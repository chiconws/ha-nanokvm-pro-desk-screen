"""Install and manage the optional on-device NanoKVM Desk agent."""

from __future__ import annotations

import hashlib
import io
import json
import posixpath
import secrets
import shlex
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .ssh import RemoteCommandError, SSHClient

AGENT_DIR = "/userapp/nanokvm-desk-agent"
AGENT_SCRIPT = f"{AGENT_DIR}/agent.py"
AGENT_CONFIG = f"{AGENT_DIR}/config.json"
SERVICE_NAME = "nanokvm-desk-agent"
SYSTEMD_UNIT = f"/etc/systemd/system/{SERVICE_NAME}.service"
INIT_SCRIPT = f"/etc/init.d/S99{SERVICE_NAME}"
DEFAULT_AGENT_PORT = 8765
DEFAULT_AGENT_BIND = "0.0.0.0"
DEFAULT_AGENT_FPS = 12.0
DEFAULT_MAX_STREAMS = 2


@dataclass(frozen=True)
class AgentInstallResult:
    """Result returned by install/update operations."""

    url: str
    token: str
    service_manager: str
    config: dict[str, object]


def install_agent(
    remote: SSHClient,
    *,
    host: str,
    bind: str = DEFAULT_AGENT_BIND,
    port: int = DEFAULT_AGENT_PORT,
    fps: float = DEFAULT_AGENT_FPS,
    reset_token: bool = False,
) -> AgentInstallResult:
    """Install or update the on-device agent through an existing SSH connection."""

    existing = read_existing_config(remote)
    config = build_agent_config(
        bind=bind,
        port=port,
        fps=fps,
        existing=existing,
        reset_token=reset_token,
    )
    service_manager_raw = detect_service_manager(remote)
    if service_manager_raw is None:
        raise RuntimeError("No supported service manager found: expected systemd or /etc/init.d")
    service_manager: str = service_manager_raw

    run_checked(remote, f"mkdir -p {shlex.quote(AGENT_DIR)}")
    run_checked(remote, f"chmod 0700 {shlex.quote(AGENT_DIR)}")
    upload_text(remote, AGENT_SCRIPT, agent_source(), mode="0755")
    config_json = json.dumps(config, indent=2, sort_keys=True) + "\n"
    upload_text(remote, AGENT_CONFIG, config_json, mode="0600")

    remote.run(stop_commands())
    if service_manager == "systemd":
        upload_text(remote, SYSTEMD_UNIT, build_systemd_unit(), mode="0644")
        run_checked(remote, " && ".join(systemd_install_commands()))
    else:
        upload_text(remote, INIT_SCRIPT, build_init_script(), mode="0755")
        run_checked(remote, " && ".join(init_install_commands()))

    token_value = config.get("token")
    if not isinstance(token_value, str) or not token_value:
        raise RuntimeError("invalid generated agent config: token must be a non-empty string")
    port_value = config.get("port")
    if not isinstance(port_value, int):
        raise RuntimeError("invalid generated agent config: port must be an integer")

    token = token_value
    return AgentInstallResult(
        url=agent_url(host, port_value, token),
        token=token,
        service_manager=service_manager,
        config=config,
    )


def agent_status(remote: SSHClient, *, host: str) -> dict[str, object]:
    existing = read_existing_config(remote)
    installed = existing is not None
    service_manager = detect_service_manager(remote, allow_missing=True)
    active = False
    raw_status = ""

    if service_manager == "systemd":
        command = f"systemctl is-active {SERVICE_NAME} || true"
        raw_status, _stderr, _exit_status = remote.run(command)
        active = raw_status.strip() == "active"
    elif service_manager == "init":
        raw_status, _stderr, exit_status = remote.run(f"{INIT_SCRIPT} status 2>&1 || true")
        active = exit_status == 0 and "running" in raw_status.lower()

    url = None
    if existing and isinstance(existing.get("token"), str):
        existing_port_raw = existing.get("port", DEFAULT_AGENT_PORT)
        if isinstance(existing_port_raw, int):
            existing_port = existing_port_raw
        elif isinstance(existing_port_raw, str):
            try:
                existing_port = int(existing_port_raw)
            except ValueError:
                existing_port = DEFAULT_AGENT_PORT
        else:
            existing_port = DEFAULT_AGENT_PORT
        url = agent_url(host, existing_port, str(existing["token"]))

    return {
        "installed": installed,
        "active": active,
        "service_manager": service_manager,
        "install_dir": AGENT_DIR,
        "url": url,
        "status": raw_status.strip(),
    }


def uninstall_agent(remote: SSHClient) -> dict[str, object]:
    stdout, stderr, exit_status = remote.run(" ; ".join(uninstall_commands()))
    return {
        "ok": exit_status == 0,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "exit_status": exit_status,
    }


def build_agent_config(
    *,
    bind: str,
    port: int,
    fps: float,
    existing: dict[str, Any] | None = None,
    reset_token: bool = False,
    token: str | None = None,
) -> dict[str, object]:
    preserved_token = None if reset_token else (existing or {}).get("token")
    agent_token = token or (preserved_token if isinstance(preserved_token, str) else None)
    if not agent_token:
        agent_token = secrets.token_urlsafe(24)

    return {
        "bind": bind,
        "port": port,
        "token": agent_token,
        "fps": fps,
        "physical_width": 172,
        "physical_height": 320,
        "logical_width": 320,
        "logical_height": 172,
        "bits_per_pixel": 16,
        "rotation": "clockwise",
        "framebuffer": "/dev/fb0",
        "input_root": "/sys/class/input",
        "max_streams": DEFAULT_MAX_STREAMS,
    }


def build_systemd_unit() -> str:
    return f"""[Unit]
Description=NanoKVM Desk Agent
After=network.target

[Service]
Type=simple
WorkingDirectory={AGENT_DIR}
ExecStart=/usr/bin/env python3 {AGENT_SCRIPT} --config {AGENT_CONFIG}
Restart=on-failure
RestartSec=2
User=root
NoNewPrivileges=true
PrivateTmp=true
UMask=0077

[Install]
WantedBy=multi-user.target
"""


def build_init_script() -> str:
    return f"""#!/bin/sh
umask 077

APP_DIR="{AGENT_DIR}"
CONFIG="{AGENT_CONFIG}"
PIDFILE="/var/run/{SERVICE_NAME}.pid"
LOGFILE="/tmp/{SERVICE_NAME}.log"

is_running() {{
    [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}}

start() {{
    if is_running; then
        echo "{SERVICE_NAME} already running"
        exit 0
    fi
    cd "$APP_DIR" || exit 1
    nohup python3 "{AGENT_SCRIPT}" --config "$CONFIG" >"$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "{SERVICE_NAME} started"
}}

stop() {{
    if is_running; then
        kill "$(cat "$PIDFILE")" 2>/dev/null || true
        rm -f "$PIDFILE"
        echo "{SERVICE_NAME} stopped"
    else
        rm -f "$PIDFILE"
        echo "{SERVICE_NAME} not running"
    fi
}}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status)
        if is_running; then
            echo "{SERVICE_NAME} running"
            exit 0
        fi
        echo "{SERVICE_NAME} stopped"
        exit 3
        ;;
    *) echo "Usage: $0 {{start|stop|restart|status}}"; exit 2 ;;
esac
"""


def systemd_install_commands() -> list[str]:
    return [
        "systemctl daemon-reload",
        f"systemctl enable {SERVICE_NAME}",
        f"systemctl restart {SERVICE_NAME}",
    ]


def init_install_commands() -> list[str]:
    return [
        f"chmod +x {INIT_SCRIPT}",
        (
            f"(command -v update-rc.d >/dev/null 2>&1 && "
            f"update-rc.d {posixpath.basename(INIT_SCRIPT)} defaults || true)"
        ),
        f"([ -d /etc/rc.d ] && ln -sf {INIT_SCRIPT} /etc/rc.d/S99{SERVICE_NAME} || true)",
        f"{INIT_SCRIPT} restart",
    ]


def uninstall_commands() -> list[str]:
    return [
        f"systemctl stop {SERVICE_NAME} 2>/dev/null || true",
        f"systemctl disable {SERVICE_NAME} 2>/dev/null || true",
        f"{INIT_SCRIPT} stop 2>/dev/null || true",
        f"rm -f {SYSTEMD_UNIT}",
        f"rm -f {INIT_SCRIPT}",
        f"rm -f /etc/rc.d/S99{SERVICE_NAME}",
        f"rm -rf {AGENT_DIR}",
        "systemctl daemon-reload 2>/dev/null || true",
        # Last, so the exit status says whether anything is left behind.
        f"! [ -e {AGENT_DIR} -o -e {SYSTEMD_UNIT} -o -e {INIT_SCRIPT} ]",
    ]


def stop_commands() -> str:
    return (
        f"systemctl stop {SERVICE_NAME} 2>/dev/null || true; "
        f"{INIT_SCRIPT} stop 2>/dev/null || true"
    )


def detect_service_manager(remote: SSHClient, *, allow_missing: bool = False) -> str | None:
    stdout, _stderr, _exit_status = remote.run(
        "if command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]; then "
        "echo systemd; elif [ -d /etc/init.d ]; then echo init; fi"
    )
    manager = stdout.strip()
    if manager in {"systemd", "init"}:
        return manager
    if allow_missing:
        return None
    raise RuntimeError("No supported service manager found: expected systemd or /etc/init.d")


def read_existing_config(remote: SSHClient) -> dict[str, Any] | None:
    command = f"cat {shlex.quote(AGENT_CONFIG)} 2>/dev/null || true"
    stdout, _stderr, _exit_status = remote.run(command)
    if not stdout.strip():
        return None
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def run_checked(remote: SSHClient, command: str) -> None:
    stdout, stderr, exit_status = remote.run(command)
    if exit_status != 0:
        message = stderr.strip() or stdout.strip() or command
        raise RemoteCommandError("remote command failed", exit_status, message)


def upload_text(remote: SSHClient, path: str, content: str, *, mode: str) -> None:
    sftp = remote.open_sftp()
    try:
        sftp.putfo(io.BytesIO(content.encode("utf-8")), path)
    finally:
        sftp.close()
    run_checked(remote, f"chmod {mode} {shlex.quote(path)}")


def agent_source() -> str:
    return (Path(__file__).parent / "runtime.py").read_text(encoding="utf-8")


@cache
def agent_hash() -> str:
    """Hash of the bundled runtime, as the installed agent reports it. Reads a file."""
    return hashlib.sha256(agent_source().encode("utf-8")).hexdigest()[:16]


def agent_url(host: str, port: int, token: str) -> str:
    return f"http://{host}:{port}/#token={token}"
