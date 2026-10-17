"""HTTP views for the NanoKVM Pro Desk Screen panel."""

from __future__ import annotations

import asyncio
from functools import partial
from http import HTTPStatus
from typing import Any

import aiohttp
import paramiko
import probatio as vol
from aiohttp import web
from homeassistant.components.http import KEY_HASS, require_admin
from homeassistant.components.http.data_validator import RequestDataValidator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.http import HomeAssistantView

from .agent.client import DeskAgentClient
from .agent.installer import agent_source, install_agent, uninstall_agent
from .agent.runtime import AGENT_HASH
from .agent.ssh import (
    ConnectionConfig,
    HostKeyMismatchError,
    RemoteCommandError,
    probe_host_key,
)
from .const import (
    CONF_PORT,
    CONF_SSH_HOST_KEY,
    CONF_TOKEN,
    DATA_COORDINATORS,
    DEFAULT_PORT,
    DOMAIN,
)

AGENT_START_ATTEMPTS = 10

INPUT_PATHS = {
    "tap": "/api/input/tap",
    "swipe": "/api/input/swipe",
    "knob_rotate": "/api/input/knob/rotate",
    "knob_click": "/api/input/knob/click",
}

PORT = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))
LIFECYCLE_SCHEMA = vol.Schema(
    {
        vol.Optional("ssh_host", default=""): vol.All(str, vol.Strip),
        vol.Optional("ssh_user", default="root"): vol.All(str, vol.Strip, vol.Length(min=1)),
        vol.Optional("ssh_password", default=""): str,
        vol.Optional("ssh_port", default=22): PORT,
        vol.Optional("agent_port"): PORT,
        vol.Optional("ssh_host_key", default=""): str,
        vol.Optional("reset_token", default=False): bool,
    },
    extra=vol.REMOVE_EXTRA,
)


class DeskScreenResourceView(HomeAssistantView):
    """Serve the screen snapshot and the agent's state and source to admins."""

    url = f"/api/{DOMAIN}/{{entry_id}}/{{resource}}"
    name = f"api:{DOMAIN}:resource"

    @require_admin
    async def get(self, request: web.Request, entry_id: str, resource: str) -> web.Response:
        """Handle GET requests from the panel."""
        hass = request.app[KEY_HASS]
        entry = _entry(hass, entry_id)
        if entry is None:
            return self.json_message("Entry not found", HTTPStatus.NOT_FOUND)

        if resource == "agent":
            return self.json(await _agent_state(hass, entry))

        if resource == "agent.py":
            # The exact file an install uploads to the Desk, for anyone to read first.
            return web.Response(
                text=await hass.async_add_executor_job(agent_source),
                content_type="text/plain",
                charset="utf-8",
                headers={"Cache-Control": "no-store"},
            )

        if resource == "snapshot.jpg":
            try:
                image = await _client(hass, entry).async_snapshot_jpeg()
            except (TimeoutError, aiohttp.ClientError, ValueError) as err:
                return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)
            return web.Response(
                body=image,
                content_type="image/jpeg",
                headers={"Cache-Control": "no-store"},
            )

        return self.json_message("Resource not found", HTTPStatus.NOT_FOUND)


class DeskScreenInputView(HomeAssistantView):
    """Proxy touch and knob input to the Desk agent for admins."""

    url = f"/api/{DOMAIN}/{{entry_id}}/input/{{action}}"
    name = f"api:{DOMAIN}:input"

    @require_admin
    @RequestDataValidator(vol.Schema({}, extra=vol.ALLOW_EXTRA))
    async def post(
        self, request: web.Request, data: dict[str, Any], entry_id: str, action: str
    ) -> web.Response:
        """Handle proxied input requests."""
        hass = request.app[KEY_HASS]
        entry = _entry(hass, entry_id)
        if entry is None or action not in INPUT_PATHS:
            return self.json_message("Entry or input action not found", HTTPStatus.NOT_FOUND)

        try:
            return self.json(await _client(hass, entry).async_post_json(INPUT_PATHS[action], data))
        except (TimeoutError, aiohttp.ClientError) as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)


class DeskScreenAgentLifecycleView(HomeAssistantView):
    """Install, update or uninstall the on-device Desk agent over SSH."""

    url = f"/api/{DOMAIN}/{{entry_id}}/agent/{{action}}"
    name = f"api:{DOMAIN}:agent"

    @require_admin
    @RequestDataValidator(LIFECYCLE_SCHEMA)
    async def post(
        self, request: web.Request, data: dict[str, Any], entry_id: str, action: str
    ) -> web.Response:
        """Handle agent lifecycle requests from the admin panel."""
        hass = request.app[KEY_HASS]
        entry = _entry(hass, entry_id)
        if entry is None or action not in ("install", "uninstall"):
            return self.json_message("Entry or agent action not found", HTTPStatus.NOT_FOUND)

        connection = ConnectionConfig(
            host=data["ssh_host"] or entry.data[CONF_HOST],
            user=data["ssh_user"],
            password=data["ssh_password"] or None,
            port=data["ssh_port"],
            # A key the user just confirmed in the panel replaces the stored one.
            host_key_fingerprint=data["ssh_host_key"] or entry.data.get(CONF_SSH_HOST_KEY),
        )
        trusted = {CONF_SSH_HOST_KEY: connection.host_key_fingerprint}

        try:
            if connection.host_key_fingerprint is None:
                # Never send the password to a host whose key nobody confirmed.
                key_type, fingerprint = await hass.async_add_executor_job(
                    probe_host_key, connection.host, connection.port, connection.timeout
                )
                return self._host_key_response("unknown", key_type, fingerprint)

            if action == "uninstall":
                result = await hass.async_add_executor_job(uninstall_agent, connection)
                if result["ok"]:
                    trusted[CONF_TOKEN] = ""
                _save_entry(hass, entry, **trusted)
                return self.json(
                    {
                        "ok": result["ok"],
                        "exit_status": result["exit_status"],
                        "stdout": str(result["stdout"])[:2000],
                        "stderr": str(result["stderr"])[:2000],
                    }
                )

            port = data.get("agent_port", entry.data.get(CONF_PORT, DEFAULT_PORT))
            token = await hass.async_add_executor_job(
                partial(install_agent, connection, port=port, reset_token=data["reset_token"])
            )
            # Wait before saving: saving reloads the entry, and its first
            # poll should find the restarted agent.
            answers = await _agent_answers(_client(hass, entry, connection.host, port, token))
            changed = _save_entry(
                hass, entry, host=connection.host, port=port, token=token, **trusted
            )
            coordinator = hass.data.get(DOMAIN, {}).get(DATA_COORDINATORS, {}).get(entry_id)
            if not changed and coordinator is not None:
                # No reload follows, so let the entities see the restarted agent.
                hass.async_create_task(coordinator.async_request_refresh())
            if not answers:
                return self.json_message(
                    f"Agent was installed but does not answer on {connection.host}:{port}",
                    HTTPStatus.BAD_GATEWAY,
                )
            return self.json({"ok": True, "host": connection.host, "port": port})
        except HostKeyMismatchError as err:
            return self._host_key_response("changed", err.key_type, err.fingerprint)
        except (OSError, RuntimeError, RemoteCommandError, paramiko.SSHException) as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)

    def _host_key_response(self, reason: str, key_type: str, fingerprint: str) -> web.Response:
        """Ask the panel to confirm the SSH host key before any login is attempted."""
        return self.json(
            {
                "message": "SSH host key must be confirmed",
                "reason": reason,
                "key_type": key_type,
                "host_key": fingerprint,
            },
            HTTPStatus.CONFLICT,
        )


def _entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Return this integration's config entry with that id."""
    entry = hass.config_entries.async_get_entry(entry_id)
    return entry if entry is not None and entry.domain == DOMAIN else None


def _client(
    hass: HomeAssistant,
    entry: ConfigEntry,
    host: str | None = None,
    port: int | None = None,
    token: str | None = None,
) -> DeskAgentClient:
    """Build an agent client from the entry, or for an endpoint not saved yet."""
    return DeskAgentClient(
        session=async_get_clientsession(hass),
        host=host or str(entry.data[CONF_HOST]),
        port=port or int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
        token=str(entry.data.get(CONF_TOKEN, "")) if token is None else token,
    )


async def _agent_state(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, object]:
    """Report the agent state over HTTP only, so the panel needs no SSH for it."""
    configured = bool(entry.data.get(CONF_TOKEN))
    reachable = outdated = False
    if configured:
        try:
            outdated = await _client(hass, entry).async_agent_hash() != AGENT_HASH
        except (TimeoutError, aiohttp.ClientError):
            pass
        else:
            reachable = True
    return {
        "configured": configured,
        "reachable": reachable,
        "outdated": outdated,
        "bundled_hash": AGENT_HASH,
        "host": entry.data[CONF_HOST],
        "port": entry.data.get(CONF_PORT, DEFAULT_PORT),
    }


async def _agent_answers(client: DeskAgentClient) -> bool:
    """Wait for a freshly (re)started agent to answer with the installed token."""
    for _ in range(AGENT_START_ATTEMPTS):
        try:
            await client.async_agent_hash()
        except (TimeoutError, aiohttp.ClientError):
            await asyncio.sleep(1)
        else:
            return True
    return False


def _save_entry(hass: HomeAssistant, entry: ConfigEntry, **changes: Any) -> bool:
    """Persist entry data changes; the entry update listener reloads it if any."""
    return hass.config_entries.async_update_entry(entry, data={**entry.data, **changes})
