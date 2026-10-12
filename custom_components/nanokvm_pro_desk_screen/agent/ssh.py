"""Small Paramiko wrapper used to install and manage the Desk agent."""

from __future__ import annotations

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


@dataclass
class RemoteCommandError(Exception):
    """Raised when a remote command fails."""

    message: str
    exit_status: int
    stderr: str

    def __str__(self) -> str:
        return f"{self.message} (exit {self.exit_status}): {self.stderr}".strip()


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
