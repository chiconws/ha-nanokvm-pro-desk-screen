"""Small Paramiko wrapper used to install and manage the Desk agent."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field

import paramiko


@dataclass(frozen=True)
class ConnectionConfig:
    """SSH connection settings.

    The password is excluded from repr so accidental debug output does not leak it.
    """

    host: str
    user: str
    password: str | None = field(default=None, repr=False)
    port: int = 22
    timeout: float = 10.0
    strict_host_key: bool = False
    host_key_fingerprint: str | None = None


@dataclass
class RemoteCommandError(Exception):
    """Raised when a remote command fails."""

    message: str
    exit_status: int
    stderr: str

    def __str__(self) -> str:
        return f"{self.message} (exit {self.exit_status}): {self.stderr}".strip()


class HostKeyMismatchError(paramiko.SSHException):
    """Raised when the server key is not the one the user trusted."""

    def __init__(self, key: paramiko.PKey) -> None:
        super().__init__("SSH host key does not match the trusted key")
        self.key_type = key.get_name()
        self.fingerprint = key.fingerprint


class _PinnedHostKey(paramiko.MissingHostKeyPolicy):
    """Accept only the host key with the trusted fingerprint."""

    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint

    def missing_host_key(
        self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey
    ) -> None:
        if key.fingerprint != self.fingerprint:
            raise HostKeyMismatchError(key)


def probe_host_key(host: str, port: int, timeout: float) -> tuple[str, str]:
    """Return the server's key type and fingerprint without authenticating."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        transport = paramiko.Transport(sock)
        try:
            transport.start_client(timeout=timeout)
            key = transport.get_remote_server_key()
            return key.get_name(), key.fingerprint
        finally:
            transport.close()


class SSHClient:
    """Context-managed SSH client."""

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> SSHClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def connect(self) -> None:
        client = paramiko.SSHClient()
        if self.config.host_key_fingerprint:
            # No known_hosts loaded, so every connection goes through the pin.
            client.set_missing_host_key_policy(
                _PinnedHostKey(self.config.host_key_fingerprint)
            )
        else:
            client.load_system_host_keys()
            if not self.config.strict_host_key:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        use_keys = self.config.password is None
        client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.user,
            password=self.config.password,
            timeout=self.config.timeout,
            banner_timeout=self.config.timeout,
            auth_timeout=self.config.timeout,
            look_for_keys=use_keys,
            allow_agent=use_keys,
        )
        self._client = client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def run(self, command: str) -> tuple[str, str, int]:
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        stdin, stdout, stderr = self._client.exec_command(command, timeout=self.config.timeout)
        stdin.close()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return out, err, stdout.channel.recv_exit_status()

    def open_sftp(self) -> paramiko.SFTPClient:
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        return self._client.open_sftp()
