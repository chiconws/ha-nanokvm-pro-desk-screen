from __future__ import annotations

import json
import struct
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from custom_components.nanokvm_pro_desk_screen.agent.runtime import (
    ABS_MT_POSITION_X,
    ABS_MT_POSITION_Y,
    ABS_MT_TRACKING_ID,
    BTN_TOUCH,
    EV_ABS,
    EV_KEY,
    EV_REL,
    EVENT_STRUCT,
    KEY_ENTER,
    REL_X,
    AgentConfig,
    create_server,
    load_config,
    logical_to_physical,
    pack_event,
    resolve_input_paths,
    sanitize_log_value,
    write_key_click,
    write_knob_rotate,
    write_touch_tap,
)


@contextmanager
def running_agent(config: AgentConfig) -> Iterator[str]:
    server = create_server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        address = server.server_address
        host = str(address[0])
        port = int(address[1])
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_json(url: str, token: str | None = None, method: str = "GET") -> dict[str, object]:
    request = Request(url, method=method)
    if token:
        request.add_header("X-NanoKVM-Desk-Token", token)
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def unpack_events(data: bytes) -> list[tuple[int, int, int]]:
    size = struct.calcsize(EVENT_STRUCT)
    return [
        struct.unpack(EVENT_STRUCT, data[offset : offset + size])[2:]
        for offset in range(0, len(data), size)
    ]


def test_agent_rejects_missing_token(tmp_path: Path) -> None:
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(b"\x00\x00\x00\x00")
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token="secret-token",
        physical_width=2,
        physical_height=1,
        logical_width=2,
        logical_height=1,
        framebuffer=str(framebuffer),
    )

    with running_agent(config) as base_url, pytest.raises(HTTPError) as err:
        request_json(f"{base_url}/api/health")

    assert err.value.code == 401


def test_agent_accepts_token_and_serves_health(tmp_path: Path) -> None:
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(b"\x00\x00\x00\x00")
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token="secret-token",
        physical_width=2,
        physical_height=1,
        logical_width=2,
        logical_height=1,
        framebuffer=str(framebuffer),
    )

    with running_agent(config) as base_url:
        assert request_json(f"{base_url}/api/health", "secret-token")["ok"] is True


def test_agent_cors_preflight_is_available(tmp_path: Path) -> None:
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(b"\x00\x00\x00\x00")
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token="secret-token",
        physical_width=2,
        physical_height=1,
        logical_width=2,
        logical_height=1,
        framebuffer=str(framebuffer),
    )

    with running_agent(config) as base_url:
        request = Request(f"{base_url}/api/health", method="OPTIONS")
        with urlopen(request, timeout=2) as response:
            assert response.status == 204
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert response.headers["Referrer-Policy"] == "no-referrer"


def test_agent_streams_raw_framebuffer_bytes(tmp_path: Path) -> None:
    frame = b"\x00\xf8\xe0\x07"
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(frame)
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token="secret-token",
        fps=100,
        physical_width=2,
        physical_height=1,
        logical_width=2,
        logical_height=1,
        framebuffer=str(framebuffer),
    )

    with running_agent(config) as base_url:
        request = Request(f"{base_url}/api/screen/raw")
        request.add_header("X-NanoKVM-Desk-Token", "secret-token")
        with urlopen(request, timeout=2) as response:
            assert response.read(config.frame_size) == frame


def test_agent_limits_concurrent_raw_streams(tmp_path: Path) -> None:
    frame = b"\x00\xf8\xe0\x07"
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(frame)
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token="secret-token",
        fps=1,
        physical_width=2,
        physical_height=1,
        logical_width=2,
        logical_height=1,
        framebuffer=str(framebuffer),
        max_streams=1,
    )

    with running_agent(config) as base_url:
        first_request = Request(f"{base_url}/api/screen/raw")
        first_request.add_header("X-NanoKVM-Desk-Token", "secret-token")
        first_response = urlopen(first_request, timeout=2)
        try:
            assert first_response.read(config.frame_size) == frame

            second_request = Request(f"{base_url}/api/screen/raw")
            second_request.add_header("X-NanoKVM-Desk-Token", "secret-token")
            with pytest.raises(HTTPError) as err:
                urlopen(second_request, timeout=2)

            assert err.value.code == 429
        finally:
            first_response.close()


def test_load_config_rejects_short_tokens(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"token": "short"}), encoding="utf-8")

    with pytest.raises(ValueError, match="at least"):
        load_config(str(config_path))


def test_sanitize_log_value_redacts_sensitive_values() -> None:
    assert sanitize_log_value("token=abc") == "<redacted>"
    assert sanitize_log_value("GET /api/health?foo=bar HTTP/1.1") == "GET /api/health HTTP/1.1"


def test_resolve_input_paths_uses_names_and_fallbacks() -> None:
    paths = resolve_input_paths(
        [
            {"event": "event0", "path": "/dev/input/event0", "name": "hyn_ts"},
            {"event": "event1", "path": "/dev/input/event1", "name": "rotary@0"},
            {"event": "event2", "path": "/dev/input/event2", "name": "gpio_keys"},
        ]
    )

    assert paths == {
        "touch": "/dev/input/event0",
        "rotary": "/dev/input/event1",
        "key": "/dev/input/event2",
    }


def test_logical_to_physical_default_clockwise_mapping() -> None:
    config = AgentConfig(token="secret-token")

    assert logical_to_physical(config, 0, 0) == (0, 319)
    assert logical_to_physical(config, 319, 171) == (171, 0)


def test_pack_event_contains_type_code_and_value() -> None:
    event = struct.unpack(EVENT_STRUCT, pack_event(EV_REL, REL_X, -1))

    assert event[2:] == (EV_REL, REL_X, -1)


def test_write_key_click_generates_key_press_and_release(tmp_path: Path) -> None:
    event_file = tmp_path / "event"

    write_key_click(str(event_file), 0.01)

    events = unpack_events(event_file.read_bytes())
    assert (EV_KEY, KEY_ENTER, 1) in events
    assert (EV_KEY, KEY_ENTER, 0) in events


def test_write_knob_rotate_generates_relative_events(tmp_path: Path) -> None:
    event_file = tmp_path / "event"

    write_knob_rotate(str(event_file), -1, 2)

    events = unpack_events(event_file.read_bytes())
    assert events.count((EV_REL, REL_X, -1)) == 2


def test_write_touch_tap_generates_touch_down_and_release(tmp_path: Path) -> None:
    event_file = tmp_path / "event"

    write_touch_tap(str(event_file), 12, 34, 0.01)

    events = unpack_events(event_file.read_bytes())
    assert (EV_ABS, ABS_MT_POSITION_X, 12) in events
    assert (EV_ABS, ABS_MT_POSITION_Y, 34) in events
    assert (EV_ABS, ABS_MT_TRACKING_ID, -1) in events
    assert (EV_KEY, BTN_TOUCH, 1) in events
    assert (EV_KEY, BTN_TOUCH, 0) in events
