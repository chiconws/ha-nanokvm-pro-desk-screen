"""Tests for SSH host key pinning."""

import subprocess
import sys
from unittest.mock import MagicMock

import paramiko
import pytest

from custom_components.nanokvm_pro_desk_screen.agent import ssh
from custom_components.nanokvm_pro_desk_screen.agent.ssh import (
    HostKeyMismatchError,
    SSHError,
    _PinnedHostKey,
    translate_ssh_errors,
)


def test_integration_import_does_not_load_paramiko() -> None:
    """Loading the integration must not import Paramiko (boot install race)."""
    code = (
        "import sys, custom_components.nanokvm_pro_desk_screen;"
        "assert 'paramiko' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_translate_ssh_errors() -> None:
    """Paramiko errors become SSHError; others pass through."""

    @translate_ssh_errors
    def fail(err: Exception) -> None:
        raise err

    with pytest.raises(SSHError, match="boom"):
        fail(paramiko.AuthenticationException("boom"))
    with pytest.raises(OSError):
        fail(OSError())


def test_pinned_host_key_accepts_only_the_trusted_key() -> None:
    """Test pinned host key accepts only the trusted key."""
    trusted = paramiko.ECDSAKey.generate()
    other = paramiko.ECDSAKey.generate()
    policy = _PinnedHostKey(trusted.fingerprint)
    client = paramiko.SSHClient()

    policy.missing_host_key(client, "desk", trusted)
    with pytest.raises(HostKeyMismatchError) as err:
        policy.missing_host_key(client, "desk", other)

    assert err.value.fingerprint == other.fingerprint


def test_probe_host_key_reads_the_key_without_logging_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test probe host key reads the key without logging in."""
    key = paramiko.ECDSAKey.generate()
    transport = MagicMock()
    transport.get_remote_server_key.return_value = key
    monkeypatch.setattr(ssh.socket, "create_connection", MagicMock())
    monkeypatch.setattr(paramiko, "Transport", MagicMock(return_value=transport))

    assert ssh.probe_host_key("desk", 22, 5) == (key.get_name(), key.fingerprint)
    transport.close.assert_called_once()
    transport.auth_password.assert_not_called()


def test_ssh_client_connects_pinned_and_runs_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test ssh client connects pinned and runs commands."""
    paramiko_client = MagicMock()
    stdout = MagicMock()
    stdout.read.return_value = b"out"
    stdout.channel.recv_exit_status.return_value = 3
    stderr = MagicMock()
    stderr.read.return_value = b"err"
    paramiko_client.exec_command.return_value = (MagicMock(), stdout, stderr)
    monkeypatch.setattr(paramiko, "SSHClient", MagicMock(return_value=paramiko_client))
    config = ssh.ConnectionConfig(
        host="desk", user="root", password="pw", host_key_fingerprint="aa"
    )

    with ssh.SSHClient(config) as client:
        assert client.run("true") == ("out", "err", 3)
        assert client.open_sftp() is paramiko_client.open_sftp.return_value

    policy = paramiko_client.set_missing_host_key_policy.call_args.args[0]
    assert policy.fingerprint == "aa"
    assert paramiko_client.connect.call_args.kwargs["look_for_keys"] is False
    paramiko_client.close.assert_called_once()
    assert "pw" not in repr(config)


def test_ssh_client_needs_a_connection() -> None:
    """Test ssh client needs a connection."""
    client = ssh.SSHClient(ssh.ConnectionConfig(host="desk", user="root"))

    with pytest.raises(RuntimeError):
        client.run("true")
    with pytest.raises(RuntimeError):
        client.open_sftp()
