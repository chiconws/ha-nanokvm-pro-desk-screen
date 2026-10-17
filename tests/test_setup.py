"""Setup, unload, config flow, camera and diagnostics against a mocked agent."""

from unittest.mock import patch

import pytest
from homeassistant.components.camera import async_get_image
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.nanokvm_pro_desk_screen.agent.runtime import PHYSICAL_HEIGHT, PHYSICAL_WIDTH
from custom_components.nanokvm_pro_desk_screen.const import CONF_TOKEN, DOMAIN
from custom_components.nanokvm_pro_desk_screen.diagnostics import async_get_config_entry_diagnostics

AGENT = "http://desk.local:8765"


pytestmark = pytest.mark.usefixtures("http")


async def test_setup_with_agent_and_unload(hass: HomeAssistant, aioclient_mock, entry) -> None:
    aioclient_mock.get(f"{AGENT}/api/health", json={"agent_hash": "abc"})
    aioclient_mock.get(f"{AGENT}/api/screen/frame", content=b"\x00" * (PHYSICAL_WIDTH * PHYSICAL_HEIGHT * 2))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    sensor = hass.states.get("binary_sensor.desk_agent_installed")
    assert sensor and sensor.state == "on"
    camera = hass.states.get("camera.desk_screen")
    assert camera and camera.state != "unavailable"
    image = await async_get_image(hass, "camera.desk_screen")
    assert image.content.startswith(b"\xff\xd8")  # JPEG

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"][CONF_TOKEN] == "**REDACTED**" and diag["agent_hash"] == "abc"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_without_agent_still_loads(hass: HomeAssistant, aioclient_mock, entry) -> None:
    aioclient_mock.get(f"{AGENT}/api/health", status=503)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensor = hass.states.get("binary_sensor.desk_agent_installed")
    assert sensor and sensor.state == "off"
    camera = hass.states.get("camera.desk_screen")
    assert camera and camera.state == "unavailable"


@pytest.fixture
def no_setup():
    """Flow tests stop at the entry; do not set it up."""
    with patch("custom_components.nanokvm_pro_desk_screen.async_setup_entry", return_value=True):
        yield


@pytest.mark.usefixtures("no_setup")
@pytest.mark.parametrize(
    ("host", "expected"),
    [("desk.local", "desk.local"), ("http://10.0.0.5/", "10.0.0.5"), (" 10.0.0.6 ", "10.0.0.6")],
)
async def test_user_flow(hass: HomeAssistant, host, expected) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: host})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == expected


@pytest.mark.usefixtures("no_setup")
@pytest.mark.parametrize("host", ["https://desk.local", "http://desk.local/path", "   "])
async def test_user_flow_rejects_bad_host(hass: HomeAssistant, host) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: host})
    assert result["errors"] == {CONF_HOST: "invalid_host"}


async def test_user_flow_already_configured(hass: HomeAssistant, entry) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "desk.local"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
