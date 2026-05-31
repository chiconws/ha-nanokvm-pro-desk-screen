from __future__ import annotations

from custom_components.nanokvm_pro_desk_screen.agent_installer import (
    AGENT_CONFIG,
    AGENT_DIR,
    AGENT_SCRIPT,
    INIT_SCRIPT,
    SERVICE_NAME,
    SYSTEMD_UNIT,
    agent_url,
    build_agent_config,
    build_init_script,
    build_systemd_unit,
    init_install_commands,
    systemd_install_commands,
    uninstall_commands,
)


def test_build_agent_config_preserves_existing_token() -> None:
    config = build_agent_config(
        bind="0.0.0.0",
        port=8765,
        fps=12.0,
        existing={"token": "old-token"},
        token=None,
    )

    assert config["token"] == "old-token"
    assert config["port"] == 8765
    assert config["framebuffer"] == "/dev/fb0"
    assert config["input_root"] == "/sys/class/input"
    assert config["max_streams"] == 2


def test_build_agent_config_can_reset_token() -> None:
    config = build_agent_config(
        bind="127.0.0.1",
        port=9000,
        fps=8.0,
        existing={"token": "old-token"},
        reset_token=True,
        token="new-token",
    )

    assert config["token"] == "new-token"
    assert config["bind"] == "127.0.0.1"
    assert config["port"] == 9000
    assert config["fps"] == 8.0


def test_systemd_unit_runs_agent_as_root() -> None:
    unit = build_systemd_unit()

    assert f"ExecStart=/usr/bin/env python3 {AGENT_SCRIPT} --config {AGENT_CONFIG}" in unit
    assert "User=root" in unit
    assert "Restart=on-failure" in unit
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert "UMask=0077" in unit


def test_init_script_starts_agent_and_tracks_pid() -> None:
    script = build_init_script()

    assert f'APP_DIR="{AGENT_DIR}"' in script
    assert "umask 077" in script
    assert f'python3 "{AGENT_SCRIPT}" --config "$CONFIG"' in script
    assert f'PIDFILE="/var/run/{SERVICE_NAME}.pid"' in script
    assert "start|stop|restart|status" in script


def test_install_command_sets_enable_and_restart_service() -> None:
    assert systemd_install_commands() == [
        "systemctl daemon-reload",
        f"systemctl enable {SERVICE_NAME}",
        f"systemctl restart {SERVICE_NAME}",
    ]
    assert f"{INIT_SCRIPT} restart" in init_install_commands()


def test_uninstall_commands_remove_service_files_and_agent_dir() -> None:
    commands = uninstall_commands()

    assert f"systemctl stop {SERVICE_NAME} 2>/dev/null || true" in commands
    assert f"rm -f {SYSTEMD_UNIT}" in commands
    assert f"rm -f {INIT_SCRIPT}" in commands
    assert f"rm -rf {AGENT_DIR}" in commands


def test_agent_url_uses_fragment_token() -> None:
    assert agent_url("192.168.1.152", 8765, "abc") == "http://192.168.1.152:8765/#token=abc"
