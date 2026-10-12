"""HTTP views for the NanoKVM Pro Desk Screen panel."""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

import aiohttp
import paramiko
from aiohttp import web
from homeassistant.components.http import require_admin
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.http import HomeAssistantView

from .agent.client import DeskAgentClient, ScreenMetadata
from .agent.installer import (
    DEFAULT_AGENT_BIND,
    DEFAULT_AGENT_FPS,
    agent_status,
    install_agent,
    uninstall_agent,
)
from .agent.ssh import ConnectionConfig, RemoteCommandError, SSHClient
from .const import CONF_PORT, CONF_TOKEN, DEFAULT_PORT, DEFAULT_SSH_PORT, DOMAIN

AGENT_START_ATTEMPTS = 10


class DeskScreenResourceView(HomeAssistantView):
    """Proxy Desk agent screen resources through Home Assistant auth."""

    url = f"/api/{DOMAIN}/{{entry_id}}/{{resource}}"
    name = f"api:{DOMAIN}:resource"

    def __init__(self, hass: HomeAssistant, coordinators_key: str) -> None:
        """Initialize the API view."""
        self.hass = hass
        self.coordinators_key = coordinators_key

    @require_admin
    async def get(self, request: web.Request, entry_id: str, resource: str) -> web.Response:
        """Handle proxied GET requests."""
        coordinator = _coordinator(self.hass, self.coordinators_key, entry_id)
        if coordinator is None:
            return self.json_message("Entry not found", HTTPStatus.NOT_FOUND)

        try:
            if resource == "snapshot.jpg":
                metadata = coordinator.data or ScreenMetadata()
                image = await coordinator.client.async_snapshot_jpeg(metadata)
                return web.Response(
                    body=image,
                    content_type="image/jpeg",
                    headers={"Cache-Control": "no-store"},
                )
        except (TimeoutError, aiohttp.ClientError) as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)

        return self.json_message("Resource not found", HTTPStatus.NOT_FOUND)


class DeskScreenInputView(HomeAssistantView):
    """Proxy Desk agent input requests through Home Assistant auth."""

    url = f"/api/{DOMAIN}/{{entry_id}}/input/{{action}}"
    name = f"api:{DOMAIN}:input"

    def __init__(self, hass: HomeAssistant, coordinators_key: str) -> None:
        """Initialize the input view."""
        self.hass = hass
        self.coordinators_key = coordinators_key

    @require_admin
    async def post(self, request: web.Request, entry_id: str, action: str) -> web.Response:
        """Handle proxied input requests."""
        coordinator = _coordinator(self.hass, self.coordinators_key, entry_id)
        if coordinator is None:
            return self.json_message("Entry not found", HTTPStatus.NOT_FOUND)

        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON body", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            return self.json_message("JSON body must be an object", HTTPStatus.BAD_REQUEST)

        path = _input_path(action)
        if path is None:
            return self.json_message("Input action not found", HTTPStatus.NOT_FOUND)

        try:
            return self.json(await coordinator.client.async_post_json(path, payload))
        except (TimeoutError, aiohttp.ClientResponseError, aiohttp.ClientError) as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)


class DeskScreenAgentLifecycleView(HomeAssistantView):
    """Install, update, inspect, or uninstall the on-device Desk agent."""

    url = f"/api/{DOMAIN}/{{entry_id}}/agent/{{action}}"
    name = f"api:{DOMAIN}:agent"

    def __init__(self, hass: HomeAssistant, coordinators_key: str) -> None:
        """Initialize the agent lifecycle view."""
        self.hass = hass
        self.coordinators_key = coordinators_key

    @require_admin
    async def post(self, request: web.Request, entry_id: str, action: str) -> web.Response:
        """Handle agent lifecycle requests from the admin panel."""
        coordinator = _coordinator(self.hass, self.coordinators_key, entry_id)
        if coordinator is None:
            return self.json_message("Entry not found", HTTPStatus.NOT_FOUND)

        try:
            payload = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON body", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            return self.json_message("JSON body must be an object", HTTPStatus.BAD_REQUEST)

        try:
            ssh_config = _connection_config_from_payload(
                payload, str(coordinator.config_entry.data[CONF_HOST])
            )
        except ValueError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)

        try:
            if action == "status":
                status = await self.hass.async_add_executor_job(
                    _agent_status, ssh_config
                )
                return self.json(_public_agent_status(status))

            if action == "install":
                agent_port = _int_from_payload(
                    payload,
                    "agent_port",
                    int(coordinator.config_entry.data.get(CONF_PORT, DEFAULT_PORT)),
                    minimum=1,
                    maximum=65535,
                )
                bind = _str_from_payload(payload, "bind", DEFAULT_AGENT_BIND)
                fps = _float_from_payload(payload, "fps", DEFAULT_AGENT_FPS)
                reset_token = payload.get("reset_token") is True
                result = await self.hass.async_add_executor_job(
                    _install_agent,
                    ssh_config,
                    bind,
                    agent_port,
                    fps,
                    reset_token,
                )
                _update_entry_after_install(
                    self.hass,
                    coordinator,
                    host=ssh_config.host,
                    port=agent_port,
                    token=result.token,
                )
                if not await _agent_answers(
                    self.hass, ssh_config.host, agent_port, result.token
                ):
                    return self.json_message(
                        "Agent was installed but does not answer on "
                        f"{ssh_config.host}:{agent_port}",
                        HTTPStatus.BAD_GATEWAY,
                    )
                self.hass.async_create_task(coordinator.async_request_refresh())
                return self.json(
                    {
                        "ok": True,
                        "host": ssh_config.host,
                        "port": agent_port,
                        "service_manager": result.service_manager,
                        "token_updated": True,
                        "standalone_base_url": f"http://{ssh_config.host}:{agent_port}/",
                    }
                )

            if action == "uninstall":
                result = await self.hass.async_add_executor_job(
                    _uninstall_agent, ssh_config
                )
                if result.get("ok") is True:
                    _clear_entry_after_uninstall(self.hass, coordinator)
                return self.json(_public_uninstall_result(result))
        except ValueError as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        except (
            OSError,
            RuntimeError,
            RemoteCommandError,
            paramiko.SSHException,
        ) as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)

        return self.json_message("Agent action not found", HTTPStatus.NOT_FOUND)


def _input_path(action: str) -> str | None:
    """Map HA panel input actions to Desk agent API paths."""
    return {
        "tap": "/api/input/tap",
        "swipe": "/api/input/swipe",
        "knob_rotate": "/api/input/knob/rotate",
        "knob_click": "/api/input/knob/click",
    }.get(action)


def _connection_config_from_payload(
    payload: dict[str, Any], default_host: str
) -> ConnectionConfig:
    """Build an SSH connection config from a lifecycle request payload."""
    host = _str_from_payload(payload, "ssh_host", default_host)
    user = _str_from_payload(payload, "ssh_user", "root")
    port = _int_from_payload(
        payload,
        "ssh_port",
        DEFAULT_SSH_PORT,
        minimum=1,
        maximum=65535,
    )
    timeout = _float_from_payload(payload, "timeout", 10.0)
    password_value = payload.get("ssh_password")
    password = str(password_value) if password_value not in (None, "") else None

    if not host:
        raise ValueError("SSH host is required")
    if not user:
        raise ValueError("SSH user is required")

    return ConnectionConfig(
        host=host,
        user=user,
        password=password,
        port=port,
        timeout=timeout,
    )


def _str_from_payload(payload: dict[str, Any], key: str, default: str) -> str:
    """Return a stripped string payload value."""
    value = payload.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _int_from_payload(
    payload: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Return a bounded integer payload value."""
    value = payload.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{key} must be an integer") from err
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return parsed


def _float_from_payload(payload: dict[str, Any], key: str, default: float) -> float:
    """Return a positive float payload value."""
    value = payload.get(key, default)
    try:
        parsed = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{key} must be a number") from err
    if parsed <= 0:
        raise ValueError(f"{key} must be greater than zero")
    return parsed


async def _agent_answers(hass: HomeAssistant, host: str, port: int, token: str) -> bool:
    """Wait for a freshly (re)started agent to answer with the installed token."""
    client = DeskAgentClient(
        session=async_get_clientsession(hass), host=host, port=port, token=token
    )
    for _ in range(AGENT_START_ATTEMPTS):
        try:
            await client.async_metadata()
        except (TimeoutError, aiohttp.ClientError):
            await asyncio.sleep(1)
        else:
            return True
    return False


def _agent_status(config: ConnectionConfig) -> dict[str, object]:
    """Fetch agent status through SSH."""
    with SSHClient(config) as remote:
        return agent_status(remote, host=config.host)


def _install_agent(
    config: ConnectionConfig,
    bind: str,
    port: int,
    fps: float,
    reset_token: bool,
) -> Any:
    """Install or update the on-device agent through SSH."""
    with SSHClient(config) as remote:
        return install_agent(
            remote,
            host=config.host,
            bind=bind,
            port=port,
            fps=fps,
            reset_token=reset_token,
        )


def _uninstall_agent(config: ConnectionConfig) -> dict[str, object]:
    """Uninstall the on-device agent through SSH."""
    with SSHClient(config) as remote:
        return uninstall_agent(remote)


def _public_agent_status(status: dict[str, object]) -> dict[str, object]:
    """Strip token-bearing status fields before returning to the browser."""
    public = dict(status)
    public.pop("url", None)
    public["ok"] = True
    return public


def _public_uninstall_result(result: dict[str, object]) -> dict[str, object]:
    """Return uninstall output without large noisy fields."""
    exit_status_value = result.get("exit_status", 0)
    exit_status = exit_status_value if isinstance(exit_status_value, int) else 0
    return {
        "ok": bool(result.get("ok")),
        "exit_status": exit_status,
        "stdout": str(result.get("stdout", ""))[:2000],
        "stderr": str(result.get("stderr", ""))[:2000],
    }


def _update_entry_after_install(
    hass: HomeAssistant,
    coordinator: Any,
    *,
    host: str,
    port: int,
    token: str,
) -> None:
    """Persist the installed agent endpoint; the entry update listener reloads it."""
    entry = coordinator.config_entry
    data = dict(entry.data)
    data[CONF_HOST] = host
    data[CONF_PORT] = port
    data[CONF_TOKEN] = token
    hass.config_entries.async_update_entry(entry, data=data)


def _clear_entry_after_uninstall(hass: HomeAssistant, coordinator: Any) -> None:
    """Clear the stored agent token after a successful uninstall."""
    entry = coordinator.config_entry
    data = dict(entry.data)
    data[CONF_TOKEN] = ""
    hass.config_entries.async_update_entry(entry, data=data)


def _coordinator(
    hass: HomeAssistant, coordinators_key: str, entry_id: str
) -> Any | None:
    """Return a coordinator by config entry id."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinators = domain_data.get(coordinators_key, {})
    return coordinators.get(entry_id)
