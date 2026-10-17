"""NanoKVM Pro Desk Screen integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .agent.client import DeskAgentClient
from .const import (
    CONF_PORT,
    CONF_TOKEN,
    DEFAULT_PORT,
    DOMAIN,
    NAME,
    PANEL_COMPONENT_NAME,
    PANEL_FRONTEND_URL_PATH,
    PANEL_STATIC_URL,
    PLATFORMS,
)
from .coordinator import DeskScreenConfigEntry, DeskScreenDataUpdateCoordinator
from .views import (
    DeskScreenAgentLifecycleView,
    DeskScreenInputView,
    DeskScreenResourceView,
)

DATA_HTTP_REGISTERED = "http_registered"
DATA_STATIC_REGISTERED = "static_registered"


async def async_setup_entry(hass: HomeAssistant, entry: DeskScreenConfigEntry) -> bool:
    """Set up NanoKVM Pro Desk Screen from a config entry."""
    host = entry.data[CONF_HOST]
    port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
    token = str(entry.data.get(CONF_TOKEN, ""))

    client = DeskAgentClient(
        session=async_get_clientsession(hass),
        host=host,
        port=port,
        token=token,
    )
    coordinator = DeskScreenDataUpdateCoordinator(hass, entry, client)
    # Not first_refresh: before the agent is installed it cannot answer, and the
    # panel (which installs it) must still load.
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    await _async_register_panel(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: DeskScreenConfigEntry) -> None:
    """Reload after the agent host, port or token changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DeskScreenConfigEntry) -> bool:
    """Unload a NanoKVM Pro Desk Screen config entry."""
    # The panel is left alone here: a reload registers it again with the same
    # config, and taking it away in between would close the page the user is on.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: DeskScreenConfigEntry) -> None:
    """Drop the removed entry from the sidebar panel, or the panel with the last one."""
    # ponytail: a disabled entry stays listed in the panel until restart
    if hass.config_entries.async_loaded_entries(DOMAIN):
        await _async_register_panel(hass)
    else:
        frontend.async_remove_panel(hass, PANEL_FRONTEND_URL_PATH, warn_if_unknown=False)


async def _async_register_panel(
    hass: HomeAssistant, loading: DeskScreenConfigEntry | None = None
) -> None:
    """Register or update the Home Assistant sidebar panel."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(DATA_STATIC_REGISTERED):
        frontend_path = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"/{DOMAIN}/frontend",
                    str(frontend_path),
                    cache_headers=False,
                )
            ]
        )
        domain_data[DATA_STATIC_REGISTERED] = True

    if not domain_data.get(DATA_HTTP_REGISTERED):
        hass.http.register_view(DeskScreenResourceView())
        hass.http.register_view(DeskScreenInputView())
        hass.http.register_view(DeskScreenAgentLifecycleView())
        domain_data[DATA_HTTP_REGISTERED] = True

    # Only static values go in the panel config: when it changes the frontend
    # rebuilds the page. The panel reads the agent state from the agent resource.
    loaded = hass.config_entries.async_loaded_entries(DOMAIN)
    if loading is not None and loading not in loaded:  # still in setup, not LOADED yet
        loaded.append(loading)
    entries = []
    for entry in loaded:
        entries.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "snapshot_url": f"/api/{DOMAIN}/{entry.entry_id}/snapshot.jpg",
                "input_url": f"/api/{DOMAIN}/{entry.entry_id}/input",
                "agent_url": f"/api/{DOMAIN}/{entry.entry_id}/agent",
            }
        )

    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=NAME,
        sidebar_icon="mdi:monitor-dashboard",
        frontend_url_path=PANEL_FRONTEND_URL_PATH,
        config={
            "entries": entries,
            "version": str((await async_get_integration(hass, DOMAIN)).version),
            "_panel_custom": {
                "name": PANEL_COMPONENT_NAME,
                "js_url": PANEL_STATIC_URL,
                "embed_iframe": False,
                "trust_external": True,
            },
        },
        require_admin=True,
        update=True,
    )
