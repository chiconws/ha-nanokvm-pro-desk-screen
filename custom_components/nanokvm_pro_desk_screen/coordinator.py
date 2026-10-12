"""Data coordinator for NanoKVM Pro Desk Screen."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .agent.client import DeskAgentClient, ScreenMetadata
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DeskScreenDataUpdateCoordinator(DataUpdateCoordinator[ScreenMetadata]):
    """Poll the installed NanoKVM Pro Desk screen agent."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: DeskAgentClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            config_entry=config_entry,
        )
        self.client = client

    async def _async_update_data(self) -> ScreenMetadata:
        """Fetch the screen metadata; this doubles as the agent reachability check."""
        try:
            return await self.client.async_metadata()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Desk screen agent unavailable: {err}") from err
