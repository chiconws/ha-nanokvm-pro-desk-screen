"""Shared pytest fixtures."""

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nanokvm_pro_desk_screen.const import CONF_PORT, CONF_TOKEN, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/ during tests."""
    yield


@pytest.fixture
async def http(hass: HomeAssistant) -> None:
    """Real http server; frontend marked loaded because hass_frontend is not installed."""
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="desk.local:8765",
        title="Desk",
        data={CONF_HOST: "desk.local", CONF_PORT: 8765, CONF_TOKEN: "secret-token"},
    )
    entry.add_to_hass(hass)
    return entry
