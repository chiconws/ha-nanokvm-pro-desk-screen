"""Camera platform for NanoKVM Pro Desk Screen."""

import logging
from typing import override

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DeskScreenConfigEntry, DeskScreenDataUpdateCoordinator
from .entity import NanoKVMProDeskScreenEntity

_LOGGER = logging.getLogger(__name__)


PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeskScreenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk screen camera."""
    coordinator = entry.runtime_data
    async_add_entities([DeskScreenCamera(coordinator)])


class DeskScreenCamera(NanoKVMProDeskScreenEntity, Camera):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """Read-only camera for the Desk front-panel screen."""

    _attr_translation_key = "screen"
    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator: DeskScreenDataUpdateCoordinator) -> None:
        """Initialize the camera."""
        NanoKVMProDeskScreenEntity.__init__(self, coordinator, "screen_camera")
        Camera.__init__(self)

    @override
    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return one still image from the installed agent."""
        try:
            return await self.coordinator.client.async_snapshot_jpeg()
        except Exception as err:  # noqa: BLE001 - a failed snapshot must not break the camera
            _LOGGER.debug("Failed to fetch Desk screen snapshot: %s", err)
            return None

    @property
    @override
    def available(self) -> bool:
        """Return whether the camera can fetch snapshots."""
        return self.coordinator.last_update_success
