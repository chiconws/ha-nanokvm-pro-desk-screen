"""Runtime configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field


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

