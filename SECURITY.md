# Security Notes

This project can install an optional HTTP agent onto a NanoKVM Pro Desk. Treat
that agent as sensitive: it can view the front-panel screen and inject touch or
knob events.

SSH is required only to install or update the agent, reset its token, or
uninstall it. After the agent is installed, the camera and the sidebar page do
not use SSH. You can disable SSH on the Desk again, but you must re-enable it
for those actions.

## What Gets Installed

The Home Assistant sidebar agent dialog copies these files over SSH:

| Path | Purpose | Permissions |
| --- | --- | --- |
| `/userapp/nanokvm-desk-agent/` | Agent directory | `0700` |
| `/userapp/nanokvm-desk-agent/agent.py` | stdlib-only Python HTTP agent | `0755` |
| `/userapp/nanokvm-desk-agent/config.json` | bind address, port and token | `0600` |
| `/etc/systemd/system/nanokvm-desk-agent.service` | systemd unit | `0644` |

`agent.py` is a copy of
[`agent/runtime.py`](custom_components/nanokvm_pro_desk_screen/agent/runtime.py),
a single file that uses only the Python standard library. The sidebar agent
dialog links to the exact copy your Home Assistant would upload, with its hash.

The Desk must have systemd. The agent dialog's Uninstall action stops the
service and removes all four paths.

## Runtime Permissions

The agent runs as root because the Desk exposes its screen and input devices
through root-owned device files.

The agent reads:

- `/dev/fb0` for RGB565 screen frames.
- `/sys/class/input` to resolve touch, rotary, and key event devices.

The agent writes:

- Transient Linux input events to existing `/dev/input/event*` devices for tap,
  swipe, knob rotate, click, and long press.

The agent does not:

- Install Python dependencies on the Desk.
- Open outbound internet connections.
- Write NanoKVM configuration.
- Write to `/dev/fb0`.
- Create or require `/dev/uinput`.
- Serve any web page; it only has the API listed in the README.

## Network Exposure

The installed agent binds to `0.0.0.0:8765`. Every request must carry the
header `X-NanoKVM-Desk-Token: <token>`.

Important limitations:

- The agent uses plain HTTP, not HTTPS.
- Anyone who can sniff the trusted LAN may be able to recover the token.
- Anyone with the token can view the screen and send touch/knob input.
- Do not expose the port directly to the internet.
- Prefer a trusted LAN, VLAN, or VPN such as Tailscale/WireGuard.

If the token may have leaked, use Reset token in the sidebar agent dialog.

## Logging

The agent does not log request headers. Request-line logging strips query
strings and redacts token-looking values before writing to stderr, which
systemd keeps in the journal.

## Home Assistant Integration

The Home Assistant integration stores the Desk agent token in the config entry
and uses it server-side when proxying snapshots and controls to the agent. The
sidebar panel talks to Home Assistant endpoints, not directly to the agent, so
the token is never passed to the browser. Those endpoints require a logged-in
Home Assistant administrator.

The sidebar agent dialog can install, update, reset the token of, or uninstall
the agent. It reads the agent state over HTTP, without SSH. The SSH password
entered in that dialog is sent to Home Assistant for the selected action only
and is not written to the config entry. When the dialog installs the agent or
resets its token, the new token is saved server-side in the config entry.

Before the first SSH login the sidebar shows the Desk's SSH host key fingerprint
and asks you to confirm it. Compare it with the Desk's own keys:

```bash
for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf $f; done
```

The confirmed fingerprint is saved in the config entry, and Home Assistant
refuses to send the SSH password to a host that presents a different key until
you confirm the new one.

The Home Assistant server contacts the Desk agent over plain HTTP. Keep that
traffic on a trusted LAN, VLAN, or VPN.

The read-only camera entity also uses the token to fetch snapshots from the
agent. Put the camera entity only on dashboards where that screen content is
appropriate.

## Built-In Guardrails

- `config.json` must contain a token of at least 24 characters.
- `config.json` is written with `0600` permissions.
- The agent directory is written with `0700` permissions.
- The systemd service uses `NoNewPrivileges=true`, `PrivateTmp=true`, and
  `UMask=0077`.
