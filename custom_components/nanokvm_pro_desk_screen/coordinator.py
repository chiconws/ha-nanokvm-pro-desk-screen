"""Data coordinator for NanoKVM Pro Desk Screen."""

from datetime import timedelta
import logging
from typing import override

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .agent.client import DeskAgentClient
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)

type DeskScreenConfigEntry = ConfigEntry[DeskScreenDataUpdateCoordinator]


class DeskScreenDataUpdateCoordinator(DataUpdateCoordinator[str]):
    """Poll the installed NanoKVM Pro Desk screen agent."""

    config_entry: DeskScreenConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: DeskScreenConfigEntry,
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

    @override
    async def _async_update_data(self) -> str:
        """Fetch the agent's source hash; this doubles as the reachability check."""
        try:
            return await self.client.async_agent_hash()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Desk screen agent unavailable: {err}") from err
