from __future__ import annotations

import paramiko
import pytest

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
