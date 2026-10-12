# Security Notes

This project can install an optional HTTP agent onto a NanoKVM Pro Desk. Treat
that agent as sensitive: it can view the front-panel screen and inject touch or
knob events.

SSH is required only for install, update, status, token rotation, and uninstall.
After the agent is installed and verified, normal Home Assistant camera/sidebar
runtime does not use SSH. You can disable SSH again, but you must re-enable it
later for maintenance or uninstall.

## What Gets Installed

The Home Assistant sidebar `Agent` manager and `scripts/desk_agent.py install`
copy these files over SSH:

| Path | Purpose | Permissions |
| --- | --- | --- |
| `/userapp/nanokvm-desk-agent/` | Agent directory | `0700` |
| `/userapp/nanokvm-desk-agent/agent.py` | stdlib-only Python HTTP agent | `0755` |
| `/userapp/nanokvm-desk-agent/config.json` | token and runtime config | `0600` |
| `/etc/systemd/system/nanokvm-desk-agent.service` | systemd autostart, when available | `0644` |
| `/etc/init.d/S99nanokvm-desk-agent` | init.d autostart fallback | `0755` |

The agent is uninstalled with:

```bash
.venv/bin/python scripts/desk_agent.py uninstall --host <desk-ip> --user root --ask-password
```

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

## Network Exposure

By default the installed agent binds to `0.0.0.0:8765` so it can be opened from
a browser or embedded in Home Assistant. API requests require either:

- `Authorization: Bearer <token>`
- `X-NanoKVM-Desk-Token: <token>`

The standalone viewer keeps the token in the URL fragment:

```text
http://<desk-ip>:8765/#token=<token>
```

URL fragments are not sent in the initial HTTP request line, but the browser
does send the token in API request headers after the viewer loads.

Important limitations:

- The agent uses plain HTTP, not HTTPS.
- Anyone who can sniff the trusted LAN may be able to recover the token.
- Anyone with the token can view the screen and send touch/knob input.
- Do not expose the port directly to the internet.
- Prefer a trusted LAN, VLAN, or VPN such as Tailscale/WireGuard.

Rotate the token with:

```bash
.venv/bin/python scripts/desk_agent.py install --host <desk-ip> --user root --ask-password --reset-token
```

## Logging

The agent does not log request headers. Request-line logging strips query
strings and redacts token-looking values before writing to stderr. In init.d
mode, stdout/stderr are written to `/tmp/nanokvm-desk-agent.log`.

The command-line installer and `agent-status` print the viewer URL, including
the token. Do not paste that output into public issues, logs, screenshots, or
chat.

## Home Assistant Integration

The Home Assistant integration stores the Desk agent token in the config entry
and uses it server-side when proxying snapshots and controls to the agent. The
admin-only sidebar panel talks to Home Assistant proxy endpoints, not directly
to the agent, so the Desk agent token is not passed to the browser by the panel.
The panel receives a generated Home Assistant-side panel token that only grants
access to those proxy endpoints and is regenerated when Home Assistant restarts.

The sidebar `Agent` manager can install, update, check status, rotate the token,
or uninstall the agent. SSH credentials entered in that dialog are sent to Home
Assistant for the selected action only and are not written to the config entry.
When the sidebar installs or resets the agent token, the new Desk token is saved
server-side in the Home Assistant config entry. The sidebar does not display the
token-bearing standalone URL.

Before the first SSH login the sidebar shows the Desk's SSH host key fingerprint
and asks you to confirm it. Compare it with the Desk's own keys:

```bash
for f in /etc/ssh/ssh_host_*_key.pub; do ssh-keygen -lf $f; done
```

The confirmed fingerprint is saved in the config entry, and Home Assistant
refuses to send the SSH password to a host that presents a different key until
you confirm the new one. The command-line installer instead uses your own
`known_hosts`; pass `--strict-host-key` to reject unknown hosts.

The Home Assistant server still contacts the Desk agent over plain HTTP unless
you place a trusted reverse proxy in front of the agent. Keep that traffic on a
trusted LAN, VLAN, or VPN.

The read-only camera entity also uses the token to fetch snapshots from the
agent. Put the camera entity only on dashboards where that screen content is
appropriate.

## Built-In Guardrails

- `config.json` must contain a token of at least 24 characters.
- `config.json` is written with `0600` permissions.
- The agent directory is written with `0700` permissions.
- The raw framebuffer endpoint limits concurrent streams.
- The systemd service uses `NoNewPrivileges=true`, `PrivateTmp=true`, and
  `UMask=0077` when systemd is available.
