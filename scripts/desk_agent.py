#!/usr/bin/env python3
"""Manual install/status/uninstall helper for the NanoKVM Pro Desk agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from getpass import getpass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from custom_components.nanokvm_pro_desk_screen.agent_installer import (  # noqa: E402
    DEFAULT_AGENT_BIND,
    DEFAULT_AGENT_FPS,
    DEFAULT_AGENT_PORT,
    agent_status,
    install_agent,
    uninstall_agent,
)
from custom_components.nanokvm_pro_desk_screen.install_config import (  # noqa: E402
    ConnectionConfig,
)
from custom_components.nanokvm_pro_desk_screen.ssh import SSHClient  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Desk agent helper."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def build_parser() -> argparse.ArgumentParser:
    """Build the command parser."""
    parser = argparse.ArgumentParser(
        prog="scripts/desk_agent.py",
        description="Install, inspect, or remove the NanoKVM Pro Desk screen agent.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install or update the Desk agent.")
    add_connection_args(install_parser)
    install_parser.add_argument("--bind", default=DEFAULT_AGENT_BIND)
    install_parser.add_argument("--port", type=int, default=DEFAULT_AGENT_PORT)
    install_parser.add_argument("--fps", type=float, default=DEFAULT_AGENT_FPS)
    install_parser.add_argument("--reset-token", action="store_true")
    install_parser.set_defaults(handler=run_install)

    status_parser = subparsers.add_parser("status", help="Print Desk agent status.")
    add_connection_args(status_parser)
    status_parser.set_defaults(handler=run_status)

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove the Desk agent.")
    add_connection_args(uninstall_parser)
    uninstall_parser.set_defaults(handler=run_uninstall)

    return parser


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    """Add shared SSH connection arguments."""
    parser.add_argument("--host", default=os.getenv("NANOKVM_DESK_HOST"), help="Desk host/IP.")
    parser.add_argument(
        "--user",
        default=os.getenv("NANOKVM_DESK_USER", "root"),
        help="SSH username. Defaults to root.",
    )
    parser.add_argument("--ssh-port", type=int, default=22)
    parser.add_argument(
        "--password",
        default=os.getenv("NANOKVM_DESK_PASSWORD"),
        help="SSH password. Prefer --ask-password.",
    )
    parser.add_argument("--ask-password", action="store_true")
    parser.add_argument("--strict-host-key", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)


def run_install(args: argparse.Namespace) -> int:
    """Install or update the Desk agent."""
    config = connection_config_from_args(args)
    with SSHClient(config) as remote:
        result = install_agent(
            remote,
            host=config.host,
            bind=args.bind,
            port=args.port,
            fps=args.fps,
            reset_token=args.reset_token,
        )

    print("Installed NanoKVM Pro Desk screen agent")
    print(f"Service manager: {result.service_manager}")
    print(f"Viewer: {result.url}")
    return 0


def run_status(args: argparse.Namespace) -> int:
    """Print installed agent status."""
    config = connection_config_from_args(args)
    with SSHClient(config) as remote:
        status = agent_status(remote, host=config.host)

    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def run_uninstall(args: argparse.Namespace) -> int:
    """Uninstall the Desk agent."""
    config = connection_config_from_args(args)
    with SSHClient(config) as remote:
        result = uninstall_agent(remote)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def connection_config_from_args(args: argparse.Namespace) -> ConnectionConfig:
    """Build SSH connection config from CLI args."""
    if not args.host:
        raise SystemExit("Missing host. Pass --host or set NANOKVM_DESK_HOST.")

    password = args.password
    if args.ask_password and password is None:
        password = getpass(f"SSH password for {args.user}@{args.host}: ")

    return ConnectionConfig(
        host=args.host,
        user=args.user,
        password=password,
        port=args.ssh_port,
        timeout=args.timeout,
        strict_host_key=args.strict_host_key,
    )


if __name__ == "__main__":
    raise SystemExit(main())
