"""Binary sensors for NanoKVM Pro Desk Screen."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DeskScreenConfigEntry, DeskScreenDataUpdateCoordinator
from .entity import NanoKVMProDeskScreenEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeskScreenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk screen binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([DeskAgentInstalledBinarySensor(coordinator)])


class DeskAgentInstalledBinarySensor(  # pyright: ignore[reportIncompatibleVariableOverride]
    NanoKVMProDeskScreenEntity, BinarySensorEntity
):
    """Show whether the Desk screen agent is installed and reachable."""

    _attr_translation_key = "agent_installed"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DeskScreenDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "agent_installed")
        self._attr_is_on = coordinator.last_update_success

    @property
    def available(self) -> bool:
        """Stay available: an unreachable agent is the off state, not a missing one."""
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update cached state from coordinator data."""
        self._attr_is_on = self.coordinator.last_update_success
        super()._handle_coordinator_update()
