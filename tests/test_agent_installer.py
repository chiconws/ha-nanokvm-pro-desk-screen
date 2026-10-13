from __future__ import annotations

import hashlib

from custom_components.nanokvm_pro_desk_screen.agent import runtime
from custom_components.nanokvm_pro_desk_screen.agent.installer import (
    agent_source,
    build_agent_config,
)


def test_build_agent_config_preserves_existing_token() -> None:
    config = build_agent_config(port=8765, existing={"token": "old-token"})

    assert config == {"bind": "0.0.0.0", "port": 8765, "token": "old-token"}


def test_build_agent_config_can_reset_token() -> None:
    config = build_agent_config(port=9000, existing={"token": "old-token"}, reset_token=True)

    assert config["token"] != "old-token"
    assert len(config["token"]) >= runtime.MIN_TOKEN_LENGTH
    assert config["port"] == 9000


def test_agent_source_is_the_stdlib_only_runtime() -> None:
    source = agent_source()

    assert source.startswith('"""Stdlib-only NanoKVM Desk agent')
    assert "\nfrom ." not in source


def test_uploaded_source_hashes_to_what_the_running_agent_reports() -> None:
    # Home Assistant flags the agent as outdated when these differ.
    uploaded = hashlib.sha256(agent_source().encode("utf-8")).hexdigest()[:16]

    assert uploaded == runtime.AGENT_HASH
