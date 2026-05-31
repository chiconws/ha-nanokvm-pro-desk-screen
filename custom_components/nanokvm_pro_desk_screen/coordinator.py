"""Data coordinator for NanoKVM Pro Desk Screen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .agent_client import DeskAgentClient, ScreenMetadata
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN


@dataclass(frozen=True)
class DeskScreenData:
    """Current Desk screen agent state."""

    health: dict[str, Any]
    metadata: ScreenMetadata
    probe: dict[str, Any]


class DeskScreenDataUpdateCoordinator(DataUpdateCoordinator[DeskScreenData]):
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
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            config_entry=config_entry,
        )
        self.client = client

    async def _async_update_data(self) -> DeskScreenData:
        """Fetch current Desk screen agent state."""
        try:
            health = await self.client.async_health()
            metadata = await self.client.async_metadata()
            probe = await self.client.async_probe()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Desk screen agent unavailable: {err}") from err

        return DeskScreenData(health=health, metadata=metadata, probe=probe)
