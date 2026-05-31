"""Camera platform for NanoKVM Pro Desk Screen."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .agent_client import ScreenMetadata
from .const import DOMAIN
from .entity import NanoKVMProDeskScreenEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk screen camera."""
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    async_add_entities([DeskScreenCamera(coordinator)])


class DeskScreenCamera(NanoKVMProDeskScreenEntity, Camera):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """Read-only camera for the Desk front-panel screen."""

    _attr_translation_key = "screen"
    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator) -> None:  # type: ignore[no-untyped-def]
        """Initialize the camera."""
        NanoKVMProDeskScreenEntity.__init__(self, coordinator, "screen_camera")
        Camera.__init__(self)

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return one still image from the installed agent."""
        metadata = (
            self.coordinator.data.metadata
            if self.coordinator.data is not None
            else ScreenMetadata()
        )
        try:
            return await self.coordinator.client.async_snapshot_jpeg(metadata)
        except Exception as err:
            _LOGGER.debug("Failed to fetch Desk screen snapshot: %s", err)
            return None

    @property
    def available(self) -> bool:
        """Return whether the camera can fetch snapshots."""
        return self.coordinator.last_update_success
