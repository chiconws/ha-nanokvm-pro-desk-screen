"""Base entity for NanoKVM Pro Desk Screen."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import DeskScreenDataUpdateCoordinator


class NanoKVMProDeskScreenEntity(CoordinatorEntity[DeskScreenDataUpdateCoordinator]):
    """Base class for Desk screen entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeskScreenDataUpdateCoordinator,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Sipeed",
            model=NAME,
        )
