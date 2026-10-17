from __future__ import annotations

import json
import struct
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from custom_components.nanokvm_pro_desk_screen.agent import runtime
from custom_components.nanokvm_pro_desk_screen.agent.runtime import (
    ABS_MT_POSITION_X,
    ABS_MT_POSITION_Y,
    ABS_MT_TRACKING_ID,
    AGENT_HASH,
    BTN_TOUCH,
    EV_ABS,
    EV_KEY,
    EV_REL,
    EVENT_STRUCT,
    FRAME_SIZE,
    KEY_ENTER,
    REL_X,
    AgentConfig,
    bounded_float,
    bounded_int,
    create_server,
    list_input_devices,
    load_config,
    logical_to_physical,
    main,
    pack_event,
    resolve_input_paths,
    sanitize_log_value,
    write_key_click,
    write_knob_rotate,
    write_touch_swipe,
    write_touch_tap,
)

# The agent is a standalone HTTP server; these tests talk to it over a real local socket.
pytestmark = pytest.mark.usefixtures("socket_enabled")

TOKEN = "secret-token"


@contextmanager
def running_agent(tmp_path: Path, frame: bytes = bytes(FRAME_SIZE)) -> Iterator[str]:
    framebuffer = tmp_path / "fb0"
    framebuffer.write_bytes(frame)
    config = AgentConfig(
        bind="127.0.0.1",
        port=0,
        token=TOKEN,
        framebuffer=str(framebuffer),
        input_root=str(tmp_path / "input"),
    )
    server = create_server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def get(url: str, token: str | None = TOKEN) -> bytes:
    request = Request(url)
    if token:
        request.add_header("X-NanoKVM-Desk-Token", token)
    with urlopen(request, timeout=2) as response:
        body = response.read()
        assert response.headers["Content-Length"] == str(len(body))
        return body


def unpack_events(data: bytes) -> list[tuple[int, int, int]]:
    size = struct.calcsize(EVENT_STRUCT)
    return [
        struct.unpack(EVENT_STRUCT, data[offset : offset + size])[2:]
        for offset in range(0, len(data), size)
    ]


@pytest.mark.parametrize("path", ["/", "/api/health", "/api/screen/frame"])
def test_agent_rejects_missing_token(tmp_path: Path, path: str) -> None:
    with running_agent(tmp_path) as base_url, pytest.raises(HTTPError) as err:
        get(f"{base_url}{path}", token=None)

    assert err.value.code == 401


def test_agent_health_reports_its_source_hash(tmp_path: Path) -> None:
    with running_agent(tmp_path) as base_url:
        assert json.loads(get(f"{base_url}/api/health")) == {"ok": True, "agent_hash": AGENT_HASH}


def test_agent_serves_single_frames(tmp_path: Path) -> None:
    frame = bytes(range(256)) * (FRAME_SIZE // 256)

    with running_agent(tmp_path, frame) as base_url:
        for _ in range(5):
            assert get(f"{base_url}/api/screen/frame") == frame


def test_agent_reports_a_short_framebuffer(tmp_path: Path) -> None:
    with running_agent(tmp_path, b"\x00\x00") as base_url, pytest.raises(HTTPError) as err:
        get(f"{base_url}/api/screen/frame")

    assert err.value.code == 409


def test_load_config_reads_bind_port_and_token(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"bind": "0.0.0.0", "port": 9000, "token": "t" * 32}))

    assert load_config(str(config_path)) == AgentConfig(bind="0.0.0.0", port=9000, token="t" * 32)


def test_load_config_rejects_short_tokens(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"bind": "0.0.0.0", "port": 8765, "token": "short"}))

    with pytest.raises(ValueError, match="at least"):
        load_config(str(config_path))


def test_sanitize_log_value_redacts_sensitive_values() -> None:
    assert sanitize_log_value("token=abc") == "<redacted>"
    assert sanitize_log_value("GET /api/health?foo=bar HTTP/1.1") == "GET /api/health HTTP/1.1"


def test_resolve_input_paths_uses_device_names() -> None:
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


def test_rotary_and_key_never_fall_back_to_the_touchscreen() -> None:
    paths = resolve_input_paths(
        [{"event": "event0", "path": "/dev/input/event0", "name": "hyn_ts"}]
    )

    assert paths == {"touch": "/dev/input/event0", "rotary": None, "key": None}


def test_logical_to_physical_follows_the_clockwise_mount() -> None:
    assert logical_to_physical(0, 0) == (0, 319)
    assert logical_to_physical(319, 171) == (171, 0)


@pytest.mark.parametrize("value", ["nan", float("nan"), float("inf"), "1e999"])
def test_bounded_numbers_reject_non_finite_values(value: object) -> None:
    with pytest.raises(ValueError):
        bounded_float(value, 0.01, 5.0, "press_seconds")
    with pytest.raises(ValueError):
        bounded_int(value, 1, 50, "notches")


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


def post(url: str, body: object, *, raw: bytes | None = None) -> tuple[int, dict[str, Any]]:
    data = raw if raw is not None else json.dumps(body).encode()
    request = Request(url, data=data, method="POST", headers={"X-NanoKVM-Desk-Token": TOKEN})
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read())
    except HTTPError as err:
        return err.code, json.loads(err.read())


def make_input_devices(tmp_path: Path, *names: str) -> None:
    for index, name in enumerate(names):
        device = tmp_path / "input" / f"event{index}" / "device"
        device.mkdir(parents=True)
        (device / "name").write_text(f"{name}\n")
    (tmp_path / "input" / "event9").mkdir(parents=True)  # no name file: skipped


def test_list_input_devices_reads_sysfs_names(tmp_path: Path) -> None:
    make_input_devices(tmp_path, "hyn_ts", "rotary@0")

    assert list_input_devices(str(tmp_path / "input")) == [
        {"event": "event0", "path": "/dev/input/event0", "name": "hyn_ts"},
        {"event": "event1", "path": "/dev/input/event1", "name": "rotary@0"},
    ]


def test_resolve_input_paths_falls_back_to_name_fragments() -> None:
    paths = resolve_input_paths(
        [
            {"event": "event0", "path": "/dev/input/event0", "name": "Goodix-TS"},
            {"event": "event1", "path": "/dev/input/event1", "name": "my_rotary"},
        ]
    )

    assert paths == {"touch": "/dev/input/event0", "rotary": "/dev/input/event1", "key": None}


@pytest.mark.parametrize(
    ("path", "body", "writer", "expected"),
    [
        ("tap", {"x": 0, "y": 0}, "write_touch_tap", {"action": "tap", "physical_x": 0, "physical_y": 319}),
        ("swipe", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0, "steps": "3"}, "write_touch_swipe", {"steps": 3}),
        ("knob/rotate", {"direction": "left", "notches": 2}, "write_knob_rotate", {"events": 4}),
        ("knob/click", {}, "write_key_click", {"action": "click"}),
    ],
)
def test_agent_input_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str, body: dict, writer: str, expected: dict
) -> None:
    make_input_devices(tmp_path, "hyn_ts", "rotary@0", "gpio_keys")
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(runtime, writer, lambda *args: calls.append(args))

    with running_agent(tmp_path) as base_url:
        status, reply = post(f"{base_url}/api/input/{path}", body)

    assert status == 200 and reply["ok"] is True
    assert expected.items() <= reply.items()
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("path", "body", "raw", "status"),
    [
        ("tap", {"x": 0, "y": 0}, None, 409),  # no touch device
        ("knob/rotate", {"direction": "up"}, None, 400),
        ("tap", None, b"[1]", 400),
        ("tap", None, b"x" * 20_000, 400),
        ("nope", {}, None, 404),
    ],
)
def test_agent_input_errors(tmp_path: Path, path: str, body: object, raw: bytes | None, status: int) -> None:
    make_input_devices(tmp_path, "rotary@0")

    with running_agent(tmp_path) as base_url:
        assert post(f"{base_url}/api/input/{path}", body, raw=raw)[0] == status


def test_agent_unknown_get_path(tmp_path: Path) -> None:
    with running_agent(tmp_path) as base_url, pytest.raises(HTTPError) as err:
        get(f"{base_url}/api/nope")

    assert err.value.code == 404


@pytest.mark.parametrize("value", [None, True, [1], -1, 999])
def test_bounded_numbers_reject_bad_values(value: object) -> None:
    with pytest.raises(ValueError):
        bounded_float(value, 0, 10, "x")
    with pytest.raises(ValueError):
        bounded_int(value, 0, 10, "n")


def test_write_touch_swipe_moves_between_the_points(tmp_path: Path) -> None:
    event_file = tmp_path / "event"

    write_touch_swipe(str(event_file), (0, 0), (10, 20), 3, 0.001)

    events = unpack_events(event_file.read_bytes())
    assert (EV_ABS, ABS_MT_POSITION_X, 5) in events
    assert (EV_ABS, ABS_MT_POSITION_Y, 20) in events
    assert (EV_ABS, ABS_MT_TRACKING_ID, -1) in events


def test_main_serves_until_interrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"bind": "127.0.0.1", "port": 0, "token": "t" * 32}))

    def interrupt(_self: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(runtime.ThreadingHTTPServer, "serve_forever", interrupt)

    assert main(["--config", str(config_path)]) == 0
