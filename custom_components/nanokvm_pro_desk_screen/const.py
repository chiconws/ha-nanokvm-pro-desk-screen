"""Constants for the NanoKVM Pro Desk Screen integration."""

DOMAIN = "nanokvm_pro_desk_screen"
NAME = "NanoKVM Pro Desk Screen"

CONF_TOKEN = "token"
CONF_PORT = "port"

DEFAULT_PORT = 8765
DEFAULT_SSH_PORT = 22
DEFAULT_SCAN_INTERVAL_SECONDS = 15

PANEL_COMPONENT_NAME = "nanokvm-pro-desk-screen-panel"
PANEL_FRONTEND_URL_PATH = "nanokvm-pro-desk-screen"
PANEL_STATIC_URL = f"/{DOMAIN}/frontend/nanokvm-pro-desk-screen-panel.js?v=14"

PLATFORMS = [
    "binary_sensor",
    "camera",
]
