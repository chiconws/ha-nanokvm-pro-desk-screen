"""Install and manage the on-device NanoKVM Desk agent over SSH."""

from __future__ import annotations

import io
import json
import secrets
from pathlib import Path
from typing import Any

from .ssh import ConnectionConfig, RemoteCommandError, SSHClient

AGENT_DIR = "/userapp/nanokvm-desk-agent"
AGENT_SCRIPT = f"{AGENT_DIR}/agent.py"
AGENT_CONFIG = f"{AGENT_DIR}/config.json"
SERVICE_NAME = "nanokvm-desk-agent"
SYSTEMD_UNIT = f"/etc/systemd/system/{SERVICE_NAME}.service"

SYSTEMD_UNIT_TEXT = f"""[Unit]
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

UNINSTALL_COMMANDS = [
    f"systemctl stop {SERVICE_NAME} 2>/dev/null || true",
    f"systemctl disable {SERVICE_NAME} 2>/dev/null || true",
    f"rm -f {SYSTEMD_UNIT}",
    f"rm -rf {AGENT_DIR}",
    "systemctl daemon-reload 2>/dev/null || true",
    # Last, so the exit status says whether anything is left behind.
    f"! [ -e {AGENT_DIR} -o -e {SYSTEMD_UNIT} ]",
]


def install_agent(connection: ConnectionConfig, *, port: int, reset_token: bool = False) -> str:
    """Install or update the agent on the Desk and return its token."""
    with SSHClient(connection) as remote:
        _stdout, _stderr, exit_status = remote.run(
            "command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]"
        )
        if exit_status != 0:
            raise RuntimeError("systemd was not found on the Desk")

        config = build_agent_config(
            port=port, existing=read_existing_config(remote), reset_token=reset_token
        )
        run_checked(remote, f"mkdir -p {AGENT_DIR} && chmod 0700 {AGENT_DIR}")
        upload_text(remote, AGENT_SCRIPT, agent_source(), mode="0755")
        config_json = json.dumps(config, indent=2, sort_keys=True) + "\n"
        upload_text(remote, AGENT_CONFIG, config_json, mode="0600")
        upload_text(remote, SYSTEMD_UNIT, SYSTEMD_UNIT_TEXT, mode="0644")
        run_checked(
            remote,
            f"systemctl daemon-reload && systemctl enable {SERVICE_NAME} "
            f"&& systemctl restart {SERVICE_NAME}",
        )
    return config["token"]


def uninstall_agent(connection: ConnectionConfig) -> dict[str, object]:
    """Remove the agent from the Desk; ok is False when files were left behind."""
    with SSHClient(connection) as remote:
        stdout, stderr, exit_status = remote.run(" ; ".join(UNINSTALL_COMMANDS))
    return {
        "ok": exit_status == 0,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "exit_status": exit_status,
    }


def build_agent_config(
    *, port: int, existing: dict[str, Any] | None = None, reset_token: bool = False
) -> dict[str, Any]:
    """Build config.json, keeping the installed token unless a reset is asked for."""
    token = None if reset_token else (existing or {}).get("token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(24)
    return {"bind": "0.0.0.0", "port": port, "token": token}


def read_existing_config(remote: SSHClient) -> dict[str, Any] | None:
    stdout, _stderr, _exit_status = remote.run(f"cat {AGENT_CONFIG} 2>/dev/null || true")
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
    run_checked(remote, f"chmod {mode} {path}")


def agent_source() -> str:
    """The runtime file as uploaded to the Desk. Reads a file."""
    return (Path(__file__).parent / "runtime.py").read_text(encoding="utf-8")
