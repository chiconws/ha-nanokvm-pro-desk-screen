"""Stdlib-only NanoKVM Desk agent installed on the device.

This file is copied to the NanoKVM Desk and executed directly with python3.
Keep it free of third-party and package-relative imports.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import hmac
import json
import math
import os
import struct
import sys
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

DEFAULT_CONFIG_PATH = "/userapp/nanokvm-desk-agent/config.json"
MIN_TOKEN_LENGTH = 24

# The Desk's front panel: a 172x320 RGB565 framebuffer, mounted rotated
# clockwise, so it is seen and touched as 320x172.
PHYSICAL_WIDTH = 172
PHYSICAL_HEIGHT = 320
LOGICAL_WIDTH = PHYSICAL_HEIGHT
LOGICAL_HEIGHT = PHYSICAL_WIDTH
FRAME_SIZE = PHYSICAL_WIDTH * PHYSICAL_HEIGHT * 2

# Home Assistant compares this with the hash of the runtime it ships to tell
# whether the agent installed on the Desk is outdated.
with open(__file__, "rb") as _source:
    AGENT_HASH = hashlib.sha256(_source.read()).hexdigest()[:16]

EVENT_STRUCT = "llHHi"
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03
SYN_REPORT = 0x00
REL_X = 0x00
KEY_ENTER = 28
BTN_TOUCH = 0x14A
BTN_TOOL_FINGER = 0x145
ABS_MT_SLOT = 0x2F
ABS_MT_TOUCH_MAJOR = 0x30
ABS_MT_WIDTH_MAJOR = 0x32
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
ABS_MT_TRACKING_ID = 0x39
ABS_MT_PRESSURE = 0x3A


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the on-device agent."""

    bind: str = "0.0.0.0"
    port: int = 8765
    token: str = ""
    framebuffer: str = "/dev/fb0"
    input_root: str = "/sys/class/input"


def load_config(path: str) -> AgentConfig:
    with open(path, encoding="utf-8") as config_file:
        raw = json.load(config_file)

    config = AgentConfig(bind=raw["bind"], port=raw["port"], token=raw["token"])
    if len(config.token) < MIN_TOKEN_LENGTH:
        raise ValueError(f"config token must be at least {MIN_TOKEN_LENGTH} characters")
    return config


def create_server(config: AgentConfig) -> ThreadingHTTPServer:
    class Handler(AgentRequestHandler):
        runtime_config = config

    server = ThreadingHTTPServer((config.bind, config.port), Handler)
    server.daemon_threads = True
    return server


class AgentRequestHandler(BaseHTTPRequestHandler):
    """HTTP API of the on-device agent."""

    runtime_config = AgentConfig(token="test-token")
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if not self.require_auth():
            return

        if path == "/api/health":
            self.send_json({"ok": True, "agent_hash": AGENT_HASH})
        elif path == "/api/screen/frame":
            self.send_frame()
        else:
            self.send_json({"ok": False, "error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not self.require_auth():
            return

        try:
            payload = self.read_json_body()
            if path == "/api/input/tap":
                result = handle_tap(self.runtime_config, payload)
            elif path == "/api/input/swipe":
                result = handle_swipe(self.runtime_config, payload)
            elif path == "/api/input/knob/rotate":
                result = handle_knob_rotate(self.runtime_config, payload)
            elif path == "/api/input/knob/click":
                result = handle_knob_click(self.runtime_config, payload)
            else:
                self.send_json({"ok": False, "error": "not found"}, status=HTTPStatus.NOT_FOUND)
                return
        except ValueError as err:
            self.send_json(
                {"ok": False, "error": type(err).__name__, "message": str(err)},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        except OSError as err:
            self.send_json(
                {"ok": False, "error": type(err).__name__, "message": str(err)},
                status=HTTPStatus.CONFLICT,
            )
            return

        self.send_json(result)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 16_384:
            raise ValueError("request body is too large")
        if length == 0:
            return {}

        raw = self.rfile.read(length)
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("request body must be a JSON object")
        return parsed

    def require_auth(self) -> bool:
        if is_authorized(self.headers, self.runtime_config.token):
            return True

        self.send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        return False

    def send_frame(self) -> None:
        try:
            with open(self.runtime_config.framebuffer, "rb", buffering=0) as framebuffer:
                frame = framebuffer.read(FRAME_SIZE)
            if len(frame) != FRAME_SIZE:
                raise OSError("short framebuffer read")
        except OSError as err:
            self.send_json(
                {"ok": False, "error": type(err).__name__, "message": str(err)},
                status=HTTPStatus.CONFLICT,
            )
            return

        self.send_body(HTTPStatus.OK, "application/octet-stream", frame)

    def send_json(self, data: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_body(status, "application/json", body)

    def send_body(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        safe_args = tuple(sanitize_log_value(arg) for arg in args)
        print(f"{self.address_string()} - {format % safe_args}", file=sys.stderr)


def sanitize_log_value(value: object) -> str:
    text = str(value)
    lowered = text.lower()
    if "authorization" in lowered or "token" in lowered or "x-nanokvm-desk-token" in lowered:
        return "<redacted>"

    parts = text.split(" ")
    if len(parts) >= 3 and parts[0] in {"GET", "POST"}:
        parsed = urlparse(parts[1])
        parts[1] = parsed.path or "/"
        return " ".join(parts)

    return text


def is_authorized(headers: Any, expected_token: str) -> bool:
    return hmac.compare_digest(headers.get("X-NanoKVM-Desk-Token", ""), expected_token)


def list_input_devices(input_root: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for event_path in sorted(glob.glob(os.path.join(input_root, "event*"))):
        name_path = os.path.join(event_path, "device", "name")
        try:
            with open(name_path, encoding="utf-8") as name_file:
                name = name_file.read().strip()
        except OSError:
            continue

        event = os.path.basename(event_path)
        if event and name:
            devices.append({"event": event, "path": f"/dev/input/{event}", "name": name})

    return devices


def resolve_input_paths(devices: list[dict[str, str]]) -> dict[str, str | None]:
    return {
        "touch": resolve_device_path(
            devices, exact=("hyn_ts",), contains=("touch", "_ts"), suffix="ts"
        ),
        "rotary": resolve_device_path(devices, exact=("rotary@0",), contains=("rotary",)),
        "key": resolve_device_path(devices, exact=("gpio_keys",), contains=("keys",)),
    }


def resolve_device_path(
    devices: list[dict[str, str]],
    *,
    exact: tuple[str, ...],
    contains: tuple[str, ...],
    suffix: str | None = None,
) -> str | None:
    for expected in exact:
        for device in devices:
            if device["name"] == expected:
                return device["path"]

    for device in devices:
        lowered = device["name"].lower()
        if any(fragment in lowered for fragment in contains) or (
            suffix and lowered.endswith(suffix)
        ):
            return device["path"]

    return None


def handle_tap(config: AgentConfig, payload: dict[str, Any]) -> dict[str, object]:
    paths = resolve_input_paths(list_input_devices(config.input_root))
    touch_path = require_path(paths["touch"], "touch input device not found")
    x = bounded_float(payload.get("x"), 0, LOGICAL_WIDTH - 1, "x")
    y = bounded_float(payload.get("y"), 0, LOGICAL_HEIGHT - 1, "y")
    press_seconds = bounded_float(payload.get("press_seconds", 0.05), 0.01, 5.0, "press_seconds")
    physical_x, physical_y = logical_to_physical(x, y)

    write_touch_tap(touch_path, physical_x, physical_y, press_seconds)
    return {
        "ok": True,
        "action": "tap",
        "x": x,
        "y": y,
        "physical_x": physical_x,
        "physical_y": physical_y,
    }


def handle_swipe(config: AgentConfig, payload: dict[str, Any]) -> dict[str, object]:
    paths = resolve_input_paths(list_input_devices(config.input_root))
    touch_path = require_path(paths["touch"], "touch input device not found")
    start_x = bounded_float(payload.get("start_x"), 0, LOGICAL_WIDTH - 1, "start_x")
    start_y = bounded_float(payload.get("start_y"), 0, LOGICAL_HEIGHT - 1, "start_y")
    end_x = bounded_float(payload.get("end_x"), 0, LOGICAL_WIDTH - 1, "end_x")
    end_y = bounded_float(payload.get("end_y"), 0, LOGICAL_HEIGHT - 1, "end_y")
    steps = bounded_int(payload.get("steps", 8), 2, 64, "steps")
    step_seconds = bounded_float(payload.get("step_seconds", 0.02), 0.0, 1.0, "step_seconds")
    start = logical_to_physical(start_x, start_y)
    end = logical_to_physical(end_x, end_y)

    write_touch_swipe(touch_path, start, end, steps, step_seconds)
    return {"ok": True, "action": "swipe", "steps": steps}


def handle_knob_rotate(config: AgentConfig, payload: dict[str, Any]) -> dict[str, object]:
    paths = resolve_input_paths(list_input_devices(config.input_root))
    rotary_path = require_path(paths["rotary"], "rotary input device not found")
    direction = str(payload.get("direction", "right"))
    if direction not in {"left", "right"}:
        raise ValueError("direction must be left or right")

    notches = bounded_int(payload.get("notches", 1), 1, 50, "notches")
    steps_per_notch = bounded_int(payload.get("steps_per_notch", 2), 1, 20, "steps_per_notch")
    value = -1 if direction == "left" else 1
    events = notches * steps_per_notch
    write_knob_rotate(rotary_path, value, events)
    return {"ok": True, "action": "rotate", "direction": direction, "events": events}


def handle_knob_click(config: AgentConfig, payload: dict[str, Any]) -> dict[str, object]:
    paths = resolve_input_paths(list_input_devices(config.input_root))
    key_path = require_path(paths["key"], "key input device not found")
    press_seconds = bounded_float(payload.get("press_seconds", 0.05), 0.01, 5.0, "press_seconds")
    write_key_click(key_path, press_seconds)
    return {"ok": True, "action": "click", "press_seconds": press_seconds}


def require_path(path: str | None, message: str) -> str:
    if not path:
        raise OSError(message)
    return path


def bounded_float(value: object, minimum: float, maximum: float, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        if isinstance(value, (int, float, str)):
            number = float(value)
        else:
            raise TypeError
    except (TypeError, ValueError) as err:
        raise ValueError(f"{name} must be a number") from err
    if not math.isfinite(number) or number < minimum or number > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def bounded_int(value: object, minimum: int, maximum: int, name: str) -> int:
    if value is None:
        raise ValueError(f"{name} is required")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        if isinstance(value, int):
            number = value
        elif isinstance(value, (float, str)):
            number = int(value)
        else:
            raise TypeError
    except (TypeError, ValueError, OverflowError) as err:
        raise ValueError(f"{name} must be an integer") from err
    if number < minimum or number > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def logical_to_physical(x: float, y: float) -> tuple[int, int]:
    """Map a point on the screen as seen (320x172) to the portrait touch panel."""
    return round(y), PHYSICAL_HEIGHT - 1 - round(x)


def write_touch_tap(path: str, x: int, y: int, press_seconds: float) -> None:
    with open(path, "wb", buffering=0) as device:
        emit_touch_down(device, x, y)
        time.sleep(press_seconds)
        emit_touch_up(device)


def write_touch_swipe(
    path: str,
    start: tuple[int, int],
    end: tuple[int, int],
    steps: int,
    step_seconds: float,
) -> None:
    points: list[tuple[int, int]] = []
    for index in range(steps):
        ratio = index / max(1, steps - 1)
        x = round(start[0] + ((end[0] - start[0]) * ratio))
        y = round(start[1] + ((end[1] - start[1]) * ratio))
        points.append((x, y))

    with open(path, "wb", buffering=0) as device:
        first_x, first_y = points[0]
        emit_touch_down(device, first_x, first_y)
        for x, y in points[1:]:
            write_event(device, EV_ABS, ABS_MT_POSITION_X, x)
            write_event(device, EV_ABS, ABS_MT_POSITION_Y, y)
            write_syn(device)
            if step_seconds > 0:
                time.sleep(step_seconds)
        emit_touch_up(device)


def emit_touch_down(device: Any, x: int, y: int) -> None:
    write_event(device, EV_ABS, ABS_MT_SLOT, 0)
    write_event(device, EV_ABS, ABS_MT_TRACKING_ID, 1)
    write_event(device, EV_ABS, ABS_MT_POSITION_X, x)
    write_event(device, EV_ABS, ABS_MT_POSITION_Y, y)
    write_event(device, EV_ABS, ABS_MT_TOUCH_MAJOR, 20)
    write_event(device, EV_ABS, ABS_MT_WIDTH_MAJOR, 10)
    write_event(device, EV_ABS, ABS_MT_PRESSURE, 90)
    write_event(device, EV_KEY, BTN_TOUCH, 1)
    write_event(device, EV_KEY, BTN_TOOL_FINGER, 1)
    write_syn(device)


def emit_touch_up(device: Any) -> None:
    write_event(device, EV_ABS, ABS_MT_SLOT, 0)
    write_event(device, EV_ABS, ABS_MT_TRACKING_ID, -1)
    write_event(device, EV_KEY, BTN_TOUCH, 0)
    write_event(device, EV_KEY, BTN_TOOL_FINGER, 0)
    write_syn(device)


def write_knob_rotate(path: str, value: int, events: int) -> None:
    with open(path, "wb", buffering=0) as device:
        for _ in range(events):
            write_event(device, EV_REL, REL_X, value)
            write_syn(device)


def write_key_click(path: str, press_seconds: float) -> None:
    with open(path, "wb", buffering=0) as device:
        write_event(device, EV_KEY, KEY_ENTER, 1)
        write_syn(device)
        time.sleep(press_seconds)
        write_event(device, EV_KEY, KEY_ENTER, 0)
        write_syn(device)


def write_syn(device: Any) -> None:
    write_event(device, EV_SYN, SYN_REPORT, 0)


def write_event(device: Any, event_type: int, code: int, value: int) -> None:
    device.write(pack_event(event_type, code, value))


def pack_event(event_type: int, code: int, value: int) -> bytes:
    now = time.time()
    seconds = int(now)
    microseconds = int((now - seconds) * 1_000_000)
    return struct.pack(EVENT_STRUCT, seconds, microseconds, event_type, code, value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NanoKVM Desk on-device agent.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    server = create_server(config)
    print(f"NanoKVM Desk agent listening on {config.bind}:{config.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
