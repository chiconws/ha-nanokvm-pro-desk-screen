"""Diagnostics: entry settings with the agent token and host key redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_SSH_HOST_KEY, CONF_TOKEN
from .coordinator import DeskScreenConfigEntry

TO_REDACT = {CONF_TOKEN, CONF_SSH_HOST_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DeskScreenConfigEntry
) -> dict[str, Any]:
    """Return the entry and the last agent poll."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "agent_reachable": coordinator.last_update_success,
        "agent_hash": coordinator.data,
    }
