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
- Admin-only sidebar agent manager that shows the agent state and installs,
  updates, resets the token of, or uninstalls the optional Desk agent over SSH.

Deferred:

- Installing the agent from a Home Assistant config flow.
- A native Lovelace dashboard card.

## Agent Requirement

The camera and sidebar page expect the optional Desk agent to be installed on
the NanoKVM Pro Desk. Read [SECURITY.md](SECURITY.md) before installing it.

The short version: the agent runs as root because it needs `/dev/fb0` and
`/dev/input/event*`, protects its API with a token, and should only be exposed
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
agent button to install, update or uninstall the optional on-device agent.
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

The sidebar also has an agent button. Its dialog shows whether the agent is
installed, reachable and up to date (checked over HTTP, no SSH needed) and can
install or update it, reset its token, or uninstall it. The page tells you when
the agent on the Desk is older than the integration, for example after an
update through HACS.

Those three actions need the Desk's SSH password. It is sent to Home Assistant
for that one action and is not stored. Before the first login the dialog shows
the Desk's SSH host key fingerprint and asks you to confirm it. The Desk agent
token is stored in the Home Assistant config entry and is not exposed to the
browser.

## Agent Lifecycle

Use the sidebar agent dialog for install/update, token reset and uninstall.
SSH is only required for these actions. Normal runtime (camera and sidebar
controls) does not use SSH once the agent is installed.

The agent installs under `/userapp/nanokvm-desk-agent`, runs as root, and
starts with systemd, which the Desk must have.
The installed files and their permissions are listed in
[SECURITY.md](SECURITY.md#what-gets-installed).

## Agent HTTP Endpoints

Every endpoint requires the header `X-NanoKVM-Desk-Token: <token>`.

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | Liveness and the hash of the agent's own source |
| `GET /api/screen/frame` | One raw RGB565 frame, 172x320 |
| `POST /api/input/tap` | Touch tap |
| `POST /api/input/swipe` | Touch swipe |
| `POST /api/input/knob/rotate` | Rotate the Desk knob left or right |
| `POST /api/input/knob/click` | Click or long-press the Desk knob |

## Safety Notes

- Agent install/update/uninstall uses SSH only for lifecycle management.
- At runtime Home Assistant talks to the agent over HTTP; no SSH is involved.
- Agent APIs require a token, but HTTP is not encrypted. Do not expose it
  directly to the internet or an untrusted network.
- Screen mirroring reads from `/dev/fb0`.
- Controls write transient events to existing `/dev/input` devices.
- The project does not write to `/dev/uinput` or NanoKVM config.
- Reset the agent token from the sidebar agent dialog if it may have leaked.
