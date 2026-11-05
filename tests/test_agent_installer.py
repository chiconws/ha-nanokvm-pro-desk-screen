"""Tests for installing and removing the Desk agent over SSH."""

import hashlib
import json
from typing import Self
from unittest.mock import MagicMock

import pytest

from custom_components.nanokvm_pro_desk_screen.agent import installer, runtime
from custom_components.nanokvm_pro_desk_screen.agent.installer import (
    agent_source,
    build_agent_config,
)
from custom_components.nanokvm_pro_desk_screen.agent.ssh import (
    ConnectionConfig,
    RemoteCommandError,
)


def test_build_agent_config_preserves_existing_token() -> None:
    """Test build agent config preserves existing token."""
    config = build_agent_config(port=8765, existing={"token": "old-token"})

    assert config == {"bind": "0.0.0.0", "port": 8765, "token": "old-token"}


def test_build_agent_config_can_reset_token() -> None:
    """Test build agent config can reset token."""
    config = build_agent_config(
        port=9000, existing={"token": "old-token"}, reset_token=True
    )

    assert config["token"] != "old-token"
    assert len(config["token"]) >= runtime.MIN_TOKEN_LENGTH
    assert config["port"] == 9000


def test_agent_source_is_the_stdlib_only_runtime() -> None:
    """Test agent source is the stdlib only runtime."""
    source = agent_source()

    assert source.startswith('"""Stdlib-only NanoKVM Desk agent')
    assert "\nfrom ." not in source


def test_uploaded_source_hashes_to_what_the_running_agent_reports() -> None:
    # Home Assistant flags the agent as outdated when these differ.
    """Test uploaded source hashes to what the running agent reports."""
    uploaded = hashlib.sha256(agent_source().encode("utf-8")).hexdigest()[:16]

    assert uploaded == runtime.AGENT_HASH


class FakeRemote:
    """Stands in for SSHClient: answers commands in order and records uploads."""

    def __init__(self, *replies: tuple[str, str, int]) -> None:
        """Queue the replies returned by run()."""
        self.replies = list(replies)
        self.commands: list[str] = []
        self.uploads: dict[str, bytes] = {}

    def __call__(self, _connection: ConnectionConfig) -> FakeRemote:
        """Act as the SSHClient factory."""
        return self

    def __enter__(self) -> Self:
        """Return itself as the connected client."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Do nothing on close."""

    def run(self, command: str) -> tuple[str, str, int]:
        """Record the command and return the next queued reply."""
        self.commands.append(command)
        return self.replies.pop(0) if self.replies else ("", "", 0)

    def open_sftp(self) -> MagicMock:
        """Return an SFTP mock that records uploads."""
        sftp = MagicMock()
        sftp.putfo.side_effect = lambda data, path: self.uploads.__setitem__(
            path, data.read()
        )
        return sftp


CONNECTION = ConnectionConfig(
    host="desk", user="root", password="pw", host_key_fingerprint="aa"
)


def test_install_keeps_the_installed_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test install keeps the installed token."""
    remote = FakeRemote(("", "", 0), ('{"token": "kept"}', "", 0))
    monkeypatch.setattr(installer, "SSHClient", remote)

    assert installer.install_agent(CONNECTION, port=8765) == "kept"
    config = json.loads(remote.uploads[installer.AGENT_CONFIG])
    assert config == {"bind": "0.0.0.0", "port": 8765, "token": "kept"}
    assert remote.uploads[installer.AGENT_SCRIPT].decode() == agent_source()
    assert remote.commands[-1].endswith(f"systemctl restart {installer.SERVICE_NAME}")


def test_install_needs_systemd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test install needs systemd."""
    monkeypatch.setattr(installer, "SSHClient", FakeRemote(("", "", 1)))

    with pytest.raises(RuntimeError, match="systemd"):
        installer.install_agent(CONNECTION, port=8765)


def test_install_reports_a_failed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    # systemd ok, unreadable config, then mkdir fails
    """Test install reports a failed command."""
    remote = FakeRemote(("", "", 0), ("not json", "", 0), ("", "denied", 2))
    monkeypatch.setattr(installer, "SSHClient", remote)

    with pytest.raises(RemoteCommandError) as err:
        installer.install_agent(CONNECTION, port=8765)
    assert str(err.value) == "remote command failed (exit 2): denied"


@pytest.mark.parametrize("stdout", ["[]", ""])
def test_read_existing_config_ignores_non_objects(stdout: str) -> None:
    """Test read existing config ignores non objects."""
    assert installer.read_existing_config(FakeRemote((stdout, "", 0))) is None  # type: ignore[arg-type]  # duck-typed remote


@pytest.mark.parametrize(("exit_status", "ok"), [(0, True), (1, False)])
def test_uninstall(monkeypatch: pytest.MonkeyPatch, exit_status: int, ok: bool) -> None:
    """Test uninstall."""
    monkeypatch.setattr(
        installer, "SSHClient", FakeRemote((" out\n", " err\n", exit_status))
    )

    assert installer.uninstall_agent(CONNECTION) == {
        "ok": ok,
        "stdout": "out",
        "stderr": "err",
        "exit_status": exit_status,
    }
