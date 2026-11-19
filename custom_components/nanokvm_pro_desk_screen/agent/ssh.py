"""Small Paramiko wrapper used to install and manage the Desk agent.

Paramiko is imported inside the functions, which run in the executor, never at
module import. At boot, another integration may still be writing Paramiko to
disk when Home Assistant imports this one, and a half-written package fails to
import (seen on HA 2026.11).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
import socket
from typing import TYPE_CHECKING, Self, cast, override

if TYPE_CHECKING:
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
    host_key_fingerprint: str | None = None


@dataclass
class RemoteCommandError(Exception):
    """Raised when a remote command fails."""

    message: str
    exit_status: int
    stderr: str

    @override
    def __str__(self) -> str:
        return f"{self.message} (exit {self.exit_status}): {self.stderr}".strip()


class SSHError(Exception):
    """Raised for SSH failures, in place of paramiko.SSHException."""


def translate_ssh_errors[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Re-raise paramiko.SSHException from func as SSHError."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        import paramiko  # noqa: PLC0415

        try:
            return func(*args, **kwargs)
        except paramiko.SSHException as err:
            raise SSHError(str(err)) from err

    return wrapper


class HostKeyMismatchError(SSHError):
    """Raised when the server key is not the one the user trusted."""

    def __init__(self, key: paramiko.PKey) -> None:
        """Record the presented key type and fingerprint."""
        super().__init__("SSH host key does not match the trusted key")
        self.key_type = key.get_name()
        self.fingerprint = key.fingerprint


class _PinnedHostKey:
    """Accept only the host key with the trusted fingerprint.

    Duck-typed paramiko.MissingHostKeyPolicy, so Paramiko is not imported here.
    """

    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint

    def missing_host_key(
        self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey
    ) -> None:
        if key.fingerprint != self.fingerprint:
            raise HostKeyMismatchError(key)


@translate_ssh_errors
def probe_host_key(host: str, port: int, timeout: float) -> tuple[str, str]:
    """Return the server's key type and fingerprint without authenticating."""
    import paramiko  # noqa: PLC0415

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
        """Store the connection settings; connect lazily."""
        self.config = config
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> Self:
        """Connect and return the client."""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close the connection."""
        self.close()

    def connect(self) -> None:
        """Open the SSH connection, accepting only the pinned host key."""
        import paramiko  # noqa: PLC0415

        client = paramiko.SSHClient()
        # No known_hosts are loaded, so every connection goes through the pin;
        # without a trusted fingerprint nothing matches and the login is refused.
        client.set_missing_host_key_policy(
            cast(
                "paramiko.MissingHostKeyPolicy",
                _PinnedHostKey(self.config.host_key_fingerprint or ""),
            )
        )
        client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.user,
            password=self.config.password,
            timeout=self.config.timeout,
            banner_timeout=self.config.timeout,
            auth_timeout=self.config.timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        self._client = client

    def close(self) -> None:
        """Close the SSH connection if open."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def run(self, command: str) -> tuple[str, str, int]:
        """Run a command and return stdout, stderr and the exit status."""
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=self.config.timeout
        )
        stdin.close()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return out, err, stdout.channel.recv_exit_status()

    def open_sftp(self) -> paramiko.SFTPClient:
        """Open an SFTP session on the connection."""
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        return self._client.open_sftp()
