# NanoKVM Pro Desk Screen

[![Marketplace][badge-marketplace]][link-marketplace]
[![GitHub Release][badge-release]][link-release]
[![Home Assistant][badge-ha]][link-ha]
[![GitHub Commit Activity][badge-commit-activity]][link-commits]
[![HACS Validation][badge-hacs-validation]][link-hacs-validation]
[![Hassfest][badge-hassfest]][link-hassfest]
[![Tests][badge-tests]][link-tests]
[![License][badge-license]][link-license]

See and control the front-panel screen of a Sipeed **NanoKVM Pro Desk** from Home Assistant: a camera entity, an agent status sensor and an admin sidebar page with touch and knob controls.

## Features

- Read-only camera with a still image of the Desk screen
- Diagnostic binary sensor showing whether the on-device agent answers
- Admin-only sidebar page with live snapshots, touch, swipe and knob controls
- Agent manager in the sidebar: install, update, reset the token or uninstall over SSH

## Requirements

- Home Assistant 2026.9 or newer
- A Sipeed NanoKVM Pro Desk on a trusted LAN or VPN, with SSH enabled (only for agent install/update/uninstall)
- The optional root agent on the Desk; read [SECURITY.md](SECURITY.md) first

## Installation

### Marketplace (recommended)

[![Open your Home Assistant instance and open this repository in the Marketplace.][badge-my-marketplace]][link-my-marketplace]

1. Click the button above. If Home Assistant asks, confirm adding the repository.
2. Download **NanoKVM Pro Desk Screen** in **Settings → Marketplace**.
3. Restart Home Assistant.

On Home Assistant 2026.10 or older, install [HACS](https://hacs.xyz/) first, then use:
[![Open your Home Assistant instance and open this repository in HACS.][badge-my-hacs]][link-my-hacs]
Then download **NanoKVM Pro Desk Screen** in HACS and restart Home Assistant.

### Manual

1. Download the latest [release][link-release].
2. Copy `custom_components/nanokvm_pro_desk_screen` into the `custom_components` folder of your
   Home Assistant configuration.
3. Restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up NanoKVM Pro Desk Screen.][badge-my-config]][link-my-config]

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **NanoKVM Pro Desk Screen** and follow the setup steps.

| Field | Description |
| --- | --- |
| Host | Hostname or IP of the Desk, without `http://` or a path |

After setup, open the **NanoKVM Pro Desk Screen** sidebar page and use the agent button to install the agent. Its token is generated and stored in the config entry; you never type it.

## Entities

| Entity | Platform | Description |
| --- | --- | --- |
| Screen | `camera` | Still image of the Desk screen |
| Agent installed | `binary_sensor` | Diagnostic: the agent answers with its token |

## Agent Requirement

The camera and sidebar page expect the optional Desk agent to be installed on
the NanoKVM Pro Desk. Read [SECURITY.md](SECURITY.md) before installing it.

The short version: the agent runs as root because it needs `/dev/fb0` and
`/dev/input/event*`, protects its API with a token, and should only be exposed
on a trusted LAN or VPN.

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

## Troubleshooting

- **Diagnostics:** Settings → Devices & services → NanoKVM Pro Desk Screen → ⋮ →
  **Download diagnostics** (credentials are redacted). Attach the file to bug reports.
- **Debug logging:**

```yaml
logger:
  logs:
    custom_components.nanokvm_pro_desk_screen: debug
```

## Known limitations

- The camera is a still image, not a stream; the sidebar refreshes it.
- The agent speaks plain HTTP with a token; keep it off untrusted networks.

### Safety notes

- Agent install/update/uninstall uses SSH only for lifecycle management.
- At runtime Home Assistant talks to the agent over HTTP; no SSH is involved.
- Agent APIs require a token, but HTTP is not encrypted. Do not expose it
  directly to the internet or an untrusted network.
- Screen mirroring reads from `/dev/fb0`.
- Controls write transient events to existing `/dev/input` devices.
- The project does not write to `/dev/uinput` or NanoKVM config.
- Reset the agent token from the sidebar agent dialog if it may have leaked.

## Removal

1. Go to **Settings → Devices & services → NanoKVM Pro Desk Screen**, open ⋮ and select **Delete**.
2. Remove it in **Settings → Marketplace** (or HACS), or delete
   `custom_components/nanokvm_pro_desk_screen` if you installed it manually.
3. Restart Home Assistant.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and tests, and [AGENTS.md](AGENTS.md) for the code structure.

## License

MIT, see [LICENSE](LICENSE).

[badge-marketplace]: https://img.shields.io/badge/Marketplace-Custom-41BDF5.svg
[badge-release]: https://img.shields.io/github/v/release/chiconws/ha-nanokvm-pro-desk-screen
[badge-ha]: https://img.shields.io/badge/Home%20Assistant-2026.9%2B-41BDF5?logo=home-assistant
[badge-commit-activity]: https://img.shields.io/github/commit-activity/m/chiconws/ha-nanokvm-pro-desk-screen
[badge-hacs-validation]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/hacs.yaml/badge.svg
[badge-hassfest]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/hassfest.yaml/badge.svg
[badge-tests]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/tests.yaml/badge.svg
[badge-license]: https://img.shields.io/github/license/chiconws/ha-nanokvm-pro-desk-screen
[badge-my-marketplace]: https://my.home-assistant.io/badges/marketplace_repository.svg
[badge-my-hacs]: https://my.home-assistant.io/badges/hacs_repository.svg
[badge-my-config]: https://my.home-assistant.io/badges/config_flow_start.svg

[link-marketplace]: https://www.home-assistant.io/integrations/marketplace/
[link-release]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/releases/latest
[link-ha]: https://www.home-assistant.io/
[link-commits]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/commits/main
[link-hacs-validation]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/hacs.yaml
[link-hassfest]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/hassfest.yaml
[link-tests]: https://github.com/chiconws/ha-nanokvm-pro-desk-screen/actions/workflows/tests.yaml
[link-license]: LICENSE
[link-my-marketplace]: https://my.home-assistant.io/redirect/marketplace_repository/?owner=chiconws&repository=ha-nanokvm-pro-desk-screen&category=integration
[link-my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=chiconws&repository=ha-nanokvm-pro-desk-screen&category=integration
[link-my-config]: https://my.home-assistant.io/redirect/config_flow_start/?domain=nanokvm_pro_desk_screen
