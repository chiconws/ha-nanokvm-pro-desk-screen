# NanoKVM Pro Desk Screen

Home Assistant custom integration for the NanoKVM Pro Desk front-panel screen.

This integration is separate from the main NanoKVM integration because the Desk
screen needs an optional root agent on the Desk device. The code lives directly
in this repository under `custom_components/nanokvm_pro_desk_screen`; there is
no separate runtime Python library.

## Scope

Implemented:

- Read-only camera entity for the Desk screen.
- Diagnostic binary sensor showing whether the Desk agent is reachable.
- Admin-only Home Assistant sidebar page that proxies screen snapshots and
  controls through Home Assistant auth.
- Admin-only sidebar agent manager for installing, updating, checking,
  resetting the token, or uninstalling the optional Desk agent over SSH.

Deferred:

- Installing the agent from a Home Assistant config flow.
- A native Lovelace dashboard card.

## Agent Requirement

The camera and sidebar page expect the optional Desk agent to be installed on
the NanoKVM Pro Desk. Read [SECURITY.md](SECURITY.md) before installing it.

The short version: the agent runs as root because it needs `/dev/fb0` and
`/dev/input/event*`, uses bearer-token auth for APIs, and should only be exposed
on a trusted LAN or VPN.

## Install Through HACS

1. Open HACS in Home Assistant.
2. Go to `Integrations` and click the menu (`⋮`) in the top-right corner.
3. Select `Custom repositories`.
4. Add this repository URL:
   - `https://github.com/chiconws/ha-nanokvm-pro-desk-screen`
5. Select category `Integration` and save.
6. Find `NanoKVM Pro Desk Screen` in HACS and click `Download`.
7. Restart Home Assistant.
8. Go to `Settings` -> `Devices & services` -> `Add integration`.
9. Add `NanoKVM Pro Desk Screen` and enter your Desk host/IP.

After setup, open the `NanoKVM Pro Desk Screen` sidebar page and use the
`Agent` button to install/update/check/uninstall the optional on-device agent.
The generated agent token is stored in the Home Assistant config entry.

## Home Assistant Entities

| Entity | Purpose |
| --- | --- |
| Camera: Screen | Read-only still image from the Desk screen |
| Binary sensor: Agent installed | Diagnostic reachability state for the Desk agent |

## Home Assistant Sidebar Page

The integration registers an admin-only sidebar page named
`NanoKVM Pro Desk Screen`. The page uses Home Assistant authenticated proxy
endpoints for snapshots and controls, so the browser does not need to load the
plain-HTTP Desk agent directly from the sidebar.

The sidebar also has an `Agent` button. It can install/update, reset the token,
check status, and uninstall the on-device agent. SSH credentials entered there
are sent to Home Assistant for that one action and are not stored. The Desk
agent token is stored in the Home Assistant config entry and is not exposed to
the sidebar browser.

The installed agent still serves its own standalone viewer at the printed
`http://<desk-ip>:8765/#token=...` URL. That standalone URL is useful outside
Home Assistant, but it is not required for the Home Assistant sidebar page. The
sidebar installer intentionally does not display that token-bearing URL.

## Agent Lifecycle

Use the sidebar `Agent` button for normal lifecycle actions:

- Install/update
- Status check
- Token reset
- Uninstall

SSH is only required for these lifecycle actions. Normal runtime (camera and
sidebar controls) does not use SSH once the agent is installed.

The agent installs under `/userapp/nanokvm-desk-agent`, runs as root, and
registers autostart with systemd when available or `/etc/init.d` otherwise.

Installed files:

| Path | Purpose | Permissions |
| --- | --- | --- |
| `/userapp/nanokvm-desk-agent/` | Agent directory | `0700` |
| `/userapp/nanokvm-desk-agent/agent.py` | stdlib-only HTTP agent | `0755` |
| `/userapp/nanokvm-desk-agent/config.json` | token and runtime config | `0600` |
| `/etc/systemd/system/nanokvm-desk-agent.service` | systemd autostart, when available | `0644` |
| `/etc/init.d/S99nanokvm-desk-agent` | init.d autostart fallback | `0755` |

## Agent HTTP Endpoints

Agent API endpoints require `Authorization: Bearer <token>` or
`X-NanoKVM-Desk-Token: <token>`.

| Endpoint | Description |
| --- | --- |
| `/` | Standalone browser viewer |
| `/api/health` | Agent health |
| `/api/probe` | Capability report |
| `/api/screen/metadata` | RGB565 screen metadata |
| `/api/screen/frame` | One raw RGB565 frame |
| `/api/screen/raw` | Raw RGB565 frame stream |
| `/api/input/tap` | Touch tap |
| `/api/input/swipe` | Touch swipe |
| `/api/input/knob/rotate` | Rotate the Desk knob left or right |
| `/api/input/knob/click` | Click or long-press the Desk knob |

## Safety Notes

- Agent install/update/uninstall uses SSH only for lifecycle management.
- Agent runtime uses HTTP from the device to Home Assistant or a trusted
  browser; it does not require SSH.
- Agent APIs require a token, but HTTP is not encrypted. Do not expose it
  directly to the internet or an untrusted network.
- Screen mirroring reads from `/dev/fb0`.
- Controls write transient events to existing `/dev/input` devices.
- The project does not write to `/dev/uinput` or NanoKVM config.
- Rotate the agent token from the sidebar `Agent` dialog if the URL is shared
  with anyone who should no longer have access.
