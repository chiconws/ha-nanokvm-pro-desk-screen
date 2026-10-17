"""Config flow for the NanoKVM Pro Desk Screen integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    import probatio as vol
else:
    try:  # Home Assistant 2026.10+ validates with probatio, a drop-in for voluptuous
        import probatio as vol
    except ImportError:  # pragma: no cover - older Home Assistant
        import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import CONF_PORT, CONF_TOKEN, DEFAULT_PORT, DOMAIN


class NanoKVMProDeskScreenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NanoKVM Pro Desk Screen."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = _normalize_host(str(user_input.get(CONF_HOST, "")))

            if not host:
                errors[CONF_HOST] = "invalid_host"

            if not errors:
                await self.async_set_unique_id(f"{host}:{DEFAULT_PORT}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"NanoKVM Pro Desk Screen ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: DEFAULT_PORT,
                        CONF_TOKEN: "",
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
        )


def _normalize_host(host: str) -> str:
    """Normalize a host entered by the user."""
    host = host.strip()
    if "://" in host:
        parsed = urlparse(host)
        if parsed.scheme != "http" or parsed.path not in {"", "/"}:
            return ""
        host = parsed.hostname or ""
    return host.strip().strip("/")
