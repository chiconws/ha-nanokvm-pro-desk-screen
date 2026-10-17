from __future__ import annotations

from unittest.mock import MagicMock

import paramiko
import pytest

from custom_components.nanokvm_pro_desk_screen.agent import ssh
from custom_components.nanokvm_pro_desk_screen.agent.ssh import (
    HostKeyMismatchError,
    _PinnedHostKey,
)


def test_pinned_host_key_accepts_only_the_trusted_key() -> None:
    trusted = paramiko.ECDSAKey.generate()
    other = paramiko.ECDSAKey.generate()
    policy = _PinnedHostKey(trusted.fingerprint)
    client = paramiko.SSHClient()

    policy.missing_host_key(client, "desk", trusted)
    with pytest.raises(HostKeyMismatchError) as err:
        policy.missing_host_key(client, "desk", other)

    assert err.value.fingerprint == other.fingerprint


def test_probe_host_key_reads_the_key_without_logging_in(monkeypatch: pytest.MonkeyPatch) -> None:
    key = paramiko.ECDSAKey.generate()
    transport = MagicMock()
    transport.get_remote_server_key.return_value = key
    monkeypatch.setattr(ssh.socket, "create_connection", MagicMock())
    monkeypatch.setattr(ssh.paramiko, "Transport", MagicMock(return_value=transport))

    assert ssh.probe_host_key("desk", 22, 5) == (key.get_name(), key.fingerprint)
    transport.close.assert_called_once()
    transport.auth_password.assert_not_called()


def test_ssh_client_connects_pinned_and_runs_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    paramiko_client = MagicMock()
    stdout = MagicMock()
    stdout.read.return_value = b"out"
    stdout.channel.recv_exit_status.return_value = 3
    stderr = MagicMock()
    stderr.read.return_value = b"err"
    paramiko_client.exec_command.return_value = (MagicMock(), stdout, stderr)
    monkeypatch.setattr(ssh.paramiko, "SSHClient", MagicMock(return_value=paramiko_client))
    config = ssh.ConnectionConfig(host="desk", user="root", password="pw", host_key_fingerprint="aa")

    with ssh.SSHClient(config) as client:
        assert client.run("true") == ("out", "err", 3)
        assert client.open_sftp() is paramiko_client.open_sftp.return_value

    policy = paramiko_client.set_missing_host_key_policy.call_args.args[0]
    assert policy.fingerprint == "aa"
    assert paramiko_client.connect.call_args.kwargs["look_for_keys"] is False
    paramiko_client.close.assert_called_once()
    assert "pw" not in repr(config)


def test_ssh_client_needs_a_connection() -> None:
    client = ssh.SSHClient(ssh.ConnectionConfig(host="desk", user="root"))

    with pytest.raises(RuntimeError):
        client.run("true")
    with pytest.raises(RuntimeError):
        client.open_sftp()
