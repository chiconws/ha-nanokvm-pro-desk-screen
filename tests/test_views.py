"""Panel HTTP views against a loaded entry, a mocked agent and a mocked SSH installer."""

from unittest.mock import patch

import aiohttp
import paramiko
import pytest
from homeassistant.components import frontend
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nanokvm_pro_desk_screen import views
from custom_components.nanokvm_pro_desk_screen.agent.runtime import (
    AGENT_HASH,
    PHYSICAL_HEIGHT,
    PHYSICAL_WIDTH,
)
from custom_components.nanokvm_pro_desk_screen.agent.ssh import (
    HostKeyMismatchError,
    RemoteCommandError,
)
from custom_components.nanokvm_pro_desk_screen.const import (
    CONF_PORT,
    CONF_SSH_HOST_KEY,
    CONF_TOKEN,
    DOMAIN,
    PANEL_FRONTEND_URL_PATH,
)

AGENT = "http://desk.local:8765"
API = f"/api/{DOMAIN}"

pytestmark = pytest.mark.usefixtures("http")


@pytest.fixture
async def client(hass: HomeAssistant, hass_client, aioclient_mock, entry: MockConfigEntry):
    aioclient_mock.get(f"{AGENT}/api/health", json={"agent_hash": AGENT_HASH})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await hass_client()


async def test_agent_state(hass: HomeAssistant, client, aioclient_mock, entry) -> None:
    resp = await client.get(f"{API}/{entry.entry_id}/agent")
    assert resp.status == 200
    assert await resp.json() == {
        "configured": True,
        "reachable": True,
        "outdated": False,
        "bundled_hash": AGENT_HASH,
        "host": "desk.local",
        "port": 8765,
    }

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{AGENT}/api/health", exc=aiohttp.ClientError)
    state = await (await client.get(f"{API}/{entry.entry_id}/agent")).json()
    assert state["reachable"] is False


async def test_agent_source_and_unknowns(client, entry) -> None:
    resp = await client.get(f"{API}/{entry.entry_id}/agent.py")
    assert resp.status == 200 and (await resp.text()).startswith('"""Stdlib-only')
    assert (await client.get(f"{API}/{entry.entry_id}/nope")).status == 404
    assert (await client.get(f"{API}/missing/agent")).status == 404


async def test_snapshot(client, aioclient_mock, entry) -> None:
    aioclient_mock.get(f"{AGENT}/api/screen/frame", content=b"\x00" * (PHYSICAL_WIDTH * PHYSICAL_HEIGHT * 2))
    resp = await client.get(f"{API}/{entry.entry_id}/snapshot.jpg")
    assert resp.status == 200 and resp.content_type == "image/jpeg"

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{AGENT}/api/screen/frame", status=500)
    assert (await client.get(f"{API}/{entry.entry_id}/snapshot.jpg")).status == 502


async def test_input_proxy(client, aioclient_mock, entry) -> None:
    aioclient_mock.post(f"{AGENT}/api/input/tap", json={"ok": True})
    resp = await client.post(f"{API}/{entry.entry_id}/input/tap", json={"x": 1, "y": 2})
    assert resp.status == 200 and await resp.json() == {"ok": True}
    assert aioclient_mock.mock_calls[-1][2] == {"x": 1, "y": 2}

    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{AGENT}/api/input/tap", exc=aiohttp.ClientError)
    assert (await client.post(f"{API}/{entry.entry_id}/input/tap", json={})).status == 502
    assert (await client.post(f"{API}/{entry.entry_id}/input/jump", json={})).status == 404


async def test_lifecycle_asks_to_confirm_an_unknown_host_key(client, entry) -> None:
    with patch.object(views, "probe_host_key", return_value=("ssh-ed25519", "aa:bb")) as probe:
        resp = await client.post(f"{API}/{entry.entry_id}/agent/install", json={"ssh_password": "pw"})
    assert resp.status == 409
    assert await resp.json() == {
        "message": "SSH host key must be confirmed",
        "reason": "unknown",
        "key_type": "ssh-ed25519",
        "host_key": "aa:bb",
    }
    probe.assert_called_once_with("desk.local", 22, 10.0)
    assert (await client.post(f"{API}/{entry.entry_id}/agent/explode", json={})).status == 404


async def test_install_saves_the_new_token_and_host_key(hass: HomeAssistant, client, entry) -> None:
    body = {"ssh_password": "pw", "ssh_host_key": "aa:bb"}
    with patch.object(views, "install_agent", return_value="new-token") as install:
        resp = await client.post(f"{API}/{entry.entry_id}/agent/install", json=body)
        await hass.async_block_till_done()
        assert resp.status == 200
        assert await resp.json() == {"ok": True, "host": "desk.local", "port": 8765}
        assert entry.data[CONF_TOKEN] == "new-token" and entry.data[CONF_SSH_HOST_KEY] == "aa:bb"
        connection = install.call_args.args[0]
        assert connection.password == "pw" and install.call_args.kwargs == {"port": 8765, "reset_token": False}

        # Same result again: nothing to save, so the entities are refreshed instead of reloaded.
        resp = await client.post(f"{API}/{entry.entry_id}/agent/install", json=body)
        await hass.async_block_till_done()
        assert resp.status == 200


async def test_install_reports_an_agent_that_never_answers(hass: HomeAssistant, client, entry) -> None:
    body = {"ssh_host_key": "aa:bb", "agent_port": 9000}
    with (
        patch.object(views, "install_agent", return_value="new-token"),
        patch.object(views, "AGENT_START_ATTEMPTS", 0),
    ):
        resp = await client.post(f"{API}/{entry.entry_id}/agent/install", json=body)
        await hass.async_block_till_done()
    assert resp.status == 502
    assert entry.data[CONF_PORT] == 9000


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (HostKeyMismatchError(paramiko.ECDSAKey.generate()), 409),
        (RemoteCommandError("remote command failed", 1, "boom"), 502),
        (OSError("no route"), 502),
    ],
)
async def test_install_errors(client, entry, error, status) -> None:
    with patch.object(views, "install_agent", side_effect=error):
        resp = await client.post(f"{API}/{entry.entry_id}/agent/install", json={"ssh_host_key": "aa:bb"})
    assert resp.status == status
    if status == 409:
        assert (await resp.json())["reason"] == "changed"


@pytest.mark.parametrize(("ok", "token"), [(True, ""), (False, "secret-token")])
async def test_uninstall(hass: HomeAssistant, client, entry, ok, token) -> None:
    result = {"ok": ok, "exit_status": 0 if ok else 1, "stdout": "", "stderr": "left"}
    with patch.object(views, "uninstall_agent", return_value=result):
        resp = await client.post(f"{API}/{entry.entry_id}/agent/uninstall", json={"ssh_host_key": "aa:bb"})
        await hass.async_block_till_done()
    assert resp.status == 200 and (await resp.json())["ok"] is ok
    assert entry.data[CONF_TOKEN] == token


async def test_removing_entries_updates_then_drops_the_panel(hass: HomeAssistant, client, aioclient_mock, entry) -> None:
    aioclient_mock.get("http://desk2.local:8765/api/health", json={"agent_hash": AGENT_HASH})
    second = MockConfigEntry(domain=DOMAIN, unique_id="desk2.local:8765", data={CONF_HOST: "desk2.local"})
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_remove(second.entry_id)
    panel = hass.data[frontend.DATA_PANELS][PANEL_FRONTEND_URL_PATH]
    assert panel.config is not None
    assert [e["entry_id"] for e in panel.config["entries"]] == [entry.entry_id]

    await hass.config_entries.async_remove(entry.entry_id)
    assert PANEL_FRONTEND_URL_PATH not in hass.data[frontend.DATA_PANELS]
