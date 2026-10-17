from __future__ import annotations

from types import SimpleNamespace

from custom_components.nanokvm_pro_desk_screen.binary_sensor import (
    DeskAgentInstalledBinarySensor,
)


def test_agent_sensor_is_off_not_unavailable_when_the_agent_is_down() -> None:
    coordinator = SimpleNamespace(
        last_update_success=False,
        config_entry=SimpleNamespace(entry_id="entry", title="Desk"),
    )
    sensor = DeskAgentInstalledBinarySensor(coordinator)  # type: ignore[arg-type]

    assert sensor.available is True
    assert sensor.is_on is False
