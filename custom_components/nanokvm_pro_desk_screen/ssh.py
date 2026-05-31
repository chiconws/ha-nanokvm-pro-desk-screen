"""Small Paramiko wrapper used by manual Desk agent install tooling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import paramiko

from .install_config import ConnectionConfig


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

    def run(self, command: str, timeout: float | None = None) -> tuple[str, str, int]:
        stdout, stderr, exit_status = self.run_bytes(command, timeout=timeout)
        return stdout.decode(errors="replace"), stderr.decode(errors="replace"), exit_status

    def run_bytes(self, command: str, timeout: float | None = None) -> tuple[bytes, bytes, int]:
        stdin, stdout, stderr = self.open_command(command, timeout=timeout or self.config.timeout)
        stdin.close()

        stdout_bytes = stdout.read()
        stderr_bytes = stderr.read()
        exit_status = stdout.channel.recv_exit_status()

        return stdout_bytes, stderr_bytes, exit_status

    def open_command(
        self,
        command: str,
        timeout: float | None = None,
    ) -> tuple[Any, Any, Any]:
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        return self._client.exec_command(
            command,
            timeout=timeout,
            get_pty=False,
        )

    def open_sftp(self) -> paramiko.SFTPClient:
        if self._client is None:
            raise RuntimeError("SSH client is not connected")

        return self._client.open_sftp()
