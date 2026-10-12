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
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

DEFAULT_CONFIG_PATH = "/userapp/nanokvm-desk-agent/config.json"
DEFAULT_FRAMEBUFFER = "/dev/fb0"
DEFAULT_INPUT_ROOT = "/sys/class/input"
DEFAULT_MAX_STREAMS = 2
MAX_STREAMS_LIMIT = 8
MIN_TOKEN_LENGTH = 24

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
    fps: float = 12.0
    physical_width: int = 172
    physical_height: int = 320
    logical_width: int = 320
    logical_height: int = 172
    bits_per_pixel: int = 16
    rotation: str = "clockwise"
    framebuffer: str = DEFAULT_FRAMEBUFFER
    input_root: str = DEFAULT_INPUT_ROOT
    max_streams: int = DEFAULT_MAX_STREAMS

    @property
    def frame_size(self) -> int:
        return self.physical_width * self.physical_height * (self.bits_per_pixel // 8)

    def metadata(self) -> dict[str, object]:
        return {
            "physical_width": self.physical_width,
            "physical_height": self.physical_height,
            "logical_width": self.logical_width,
            "logical_height": self.logical_height,
            "bits_per_pixel": self.bits_per_pixel,
            "rotation": self.rotation,
            "frame_size": self.frame_size,
            "fps": self.fps,
            "max_streams": self.max_streams,
        }


def load_config(path: str) -> AgentConfig:
    with open(path, encoding="utf-8") as config_file:
        raw = json.load(config_file)

    if not isinstance(raw, dict):
        raise ValueError("config root must be an object")

    bind = str(raw.get("bind", "0.0.0.0"))
    port = bounded_int(raw.get("port", 8765), 1, 65535, "port")
    token = str(raw.get("token", ""))
    fps = bounded_float(raw.get("fps", 12.0), 0.1, 120.0, "fps")
    physical_width = bounded_int(raw.get("physical_width", 172), 1, 8192, "physical_width")
    physical_height = bounded_int(raw.get("physical_height", 320), 1, 8192, "physical_height")
    logical_width = bounded_int(raw.get("logical_width", 320), 1, 8192, "logical_width")
    logical_height = bounded_int(raw.get("logical_height", 172), 1, 8192, "logical_height")
    bits_per_pixel = bounded_int(raw.get("bits_per_pixel", 16), 1, 64, "bits_per_pixel")
    rotation = str(raw.get("rotation", "clockwise"))
    framebuffer = str(raw.get("framebuffer", DEFAULT_FRAMEBUFFER))
    input_root = str(raw.get("input_root", DEFAULT_INPUT_ROOT))
    max_streams = bounded_int(raw.get("max_streams", DEFAULT_MAX_STREAMS), 1, MAX_STREAMS_LIMIT, "max_streams")

    if len(token) < MIN_TOKEN_LENGTH:
        raise ValueError(f"config token must be at least {MIN_TOKEN_LENGTH} characters")
    return AgentConfig(
        bind=bind,
        port=port,
        token=token,
        fps=fps,
        physical_width=physical_width,
        physical_height=physical_height,
        logical_width=logical_width,
        logical_height=logical_height,
        bits_per_pixel=bits_per_pixel,
        rotation=rotation,
        framebuffer=framebuffer,
        input_root=input_root,
        max_streams=max_streams,
    )


class AgentHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server with agent-specific runtime limits."""

    stream_semaphore: threading.BoundedSemaphore

    def __init__(
        self,
        server_address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
    ) -> None:
        """Initialize server storage for runtime stream limit control."""
        super().__init__(server_address, handler)
        self.stream_semaphore = threading.BoundedSemaphore(1)


def create_server(config: AgentConfig) -> AgentHTTPServer:
    class Handler(AgentRequestHandler):
        runtime_config = config

    server = AgentHTTPServer((config.bind, config.port), Handler)
    server.daemon_threads = True
    server.stream_semaphore = threading.BoundedSemaphore(config.max_streams)
    return server


class AgentRequestHandler(BaseHTTPRequestHandler):
    """HTTP API and standalone viewer for the on-device agent."""

    runtime_config = AgentConfig(token="test-token")
    protocol_version = "HTTP/1.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_common_headers(content_length=0)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_text(VIEWER_HTML, "text/html; charset=utf-8", require_auth=False)
            return

        if not self.require_auth():
            return

        if path == "/api/health":
            self.send_json({"ok": True, "version": "0.1.0", "agent_hash": AGENT_HASH})
        elif path == "/api/probe":
            self.send_json(probe_state(self.runtime_config))
        elif path == "/api/screen/metadata":
            self.send_json({**self.runtime_config.metadata(), "agent_hash": AGENT_HASH})
        elif path == "/api/screen/frame":
            self.send_frame()
        elif path == "/api/screen/raw":
            self.stream_raw_screen()
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

        self.send_json(
            {"ok": False, "error": "unauthorized"},
            status=HTTPStatus.UNAUTHORIZED,
            extra_headers={"WWW-Authenticate": "Bearer"},
        )
        return False

    def send_frame(self) -> None:
        config = self.runtime_config
        try:
            with open(config.framebuffer, "rb", buffering=0) as framebuffer:
                frame = framebuffer.read(config.frame_size)
            if len(frame) != config.frame_size:
                raise OSError("short framebuffer read")
        except OSError as err:
            self.send_json(
                {"ok": False, "error": type(err).__name__, "message": str(err)},
                status=HTTPStatus.CONFLICT,
            )
            return

        self.send_response(HTTPStatus.OK)
        self.send_common_headers(
            content_type="application/octet-stream",
            content_length=len(frame),
        )
        self.end_headers()
        self.wfile.write(frame)

    def stream_raw_screen(self) -> None:
        config = self.runtime_config
        if not self.agent_server.stream_semaphore.acquire(blocking=False):
            self.send_json(
                {
                    "ok": False,
                    "error": "too_many_streams",
                    "message": "too many active screen streams",
                },
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
            return

        delay = 1 / max(config.fps, 0.1)
        stream_started = False
        try:
            with open(config.framebuffer, "rb", buffering=0) as framebuffer:
                self.send_response(HTTPStatus.OK)
                self.send_common_headers(
                    content_type="application/octet-stream",
                    extra_headers={
                        "X-Frame-Size": str(config.frame_size),
                        "X-NanoKVM-Desk-Stream": "rgb565",
                    },
                )
                self.end_headers()
                stream_started = True

                while True:
                    started = time.monotonic()
                    framebuffer.seek(0)
                    frame = framebuffer.read(config.frame_size)
                    if len(frame) != config.frame_size:
                        time.sleep(0.05)
                        continue

                    try:
                        self.wfile.write(frame)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return

                    elapsed = time.monotonic() - started
                    if elapsed < delay:
                        time.sleep(delay - elapsed)
        except OSError as err:
            if not stream_started:
                self.send_json(
                    {"ok": False, "error": type(err).__name__, "message": str(err)},
                    status=HTTPStatus.CONFLICT,
                )
        finally:
            self.agent_server.stream_semaphore.release()

    def send_text(
        self,
        text: str,
        content_type: str,
        *,
        require_auth: bool = True,
    ) -> None:
        if require_auth and not self.require_auth():
            return

        body = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_common_headers(content_type=content_type, content_length=len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_json(
        self,
        data: dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_common_headers(
            content_type="application/json",
            content_length=len(body),
            extra_headers=extra_headers,
        )
        self.end_headers()
        self.wfile.write(body)

    def send_common_headers(
        self,
        *,
        content_type: str | None = None,
        content_length: int | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, X-NanoKVM-Desk-Token, Content-Type",
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)

    def log_message(self, format: str, *args: object) -> None:
        safe_args = tuple(sanitize_log_value(arg) for arg in args)
        print(f"{self.address_string()} - {format % safe_args}", file=sys.stderr)

    @property
    def agent_server(self) -> AgentHTTPServer:
        if not isinstance(self.server, AgentHTTPServer):
            raise RuntimeError("agent server is not initialized")
        return self.server


def sanitize_log_value(value: object) -> str:
    text = str(value)
    lowered = text.lower()
    if "authorization" in lowered or "token" in lowered or "x-nanokvm-desk-token" in lowered:
        return "<redacted>"

    parts = text.split(" ")
    if len(parts) >= 3 and parts[0] in {"GET", "POST", "OPTIONS"}:
        parsed = urlparse(parts[1])
        parts[1] = parsed.path or "/"
        return " ".join(parts)

    return text


def is_authorized(headers: Any, expected_token: str) -> bool:
    authorization = headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if hmac.compare_digest(token, expected_token):
            return True

    token = headers.get("X-NanoKVM-Desk-Token", "")
    return hmac.compare_digest(token, expected_token)


def probe_state(config: AgentConfig) -> dict[str, object]:
    return {
        "ok": True,
        "framebuffer": {
            "path": config.framebuffer,
            "exists": os.path.exists(config.framebuffer),
            "readable": os.access(config.framebuffer, os.R_OK),
            "size": os.path.getsize(config.framebuffer) if os.path.exists(config.framebuffer) else None,
            "metadata": config.metadata(),
        },
        "input": {
            "devices": list_input_devices(config.input_root),
            "paths": resolve_input_paths(list_input_devices(config.input_root)),
        },
    }


def list_input_devices(input_root: str = DEFAULT_INPUT_ROOT) -> list[dict[str, str]]:
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
        "touch": resolve_device_path(devices, exact=("hyn_ts",), contains=("touch", "_ts"), suffix="ts"),
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
        if any(fragment in lowered for fragment in contains) or (suffix and lowered.endswith(suffix)):
            return device["path"]

    return None


def handle_tap(config: AgentConfig, payload: dict[str, Any]) -> dict[str, object]:
    paths = resolve_input_paths(list_input_devices(config.input_root))
    touch_path = require_path(paths["touch"], "touch input device not found")
    x = bounded_float(payload.get("x"), 0, config.logical_width - 1, "x")
    y = bounded_float(payload.get("y"), 0, config.logical_height - 1, "y")
    press_seconds = bounded_float(payload.get("press_seconds", 0.05), 0.01, 5.0, "press_seconds")
    physical_x, physical_y = logical_to_physical(config, x, y)

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
    start_x = bounded_float(payload.get("start_x"), 0, config.logical_width - 1, "start_x")
    start_y = bounded_float(payload.get("start_y"), 0, config.logical_height - 1, "start_y")
    end_x = bounded_float(payload.get("end_x"), 0, config.logical_width - 1, "end_x")
    end_y = bounded_float(payload.get("end_y"), 0, config.logical_height - 1, "end_y")
    steps = bounded_int(payload.get("steps", 8), 2, 64, "steps")
    step_seconds = bounded_float(payload.get("step_seconds", 0.02), 0.0, 1.0, "step_seconds")
    start = logical_to_physical(config, start_x, start_y)
    end = logical_to_physical(config, end_x, end_y)

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


def logical_to_physical(config: AgentConfig, x: float, y: float) -> tuple[int, int]:
    logical_x = clamp(round(x), 0, config.logical_width - 1)
    logical_y = clamp(round(y), 0, config.logical_height - 1)

    if config.rotation == "clockwise":
        physical_x = scale(logical_y, config.logical_height, config.physical_width)
        physical_y = config.physical_height - 1 - scale(
            logical_x,
            config.logical_width,
            config.physical_height,
        )
    elif config.rotation == "counterclockwise":
        physical_x = config.physical_width - 1 - scale(
            logical_y,
            config.logical_height,
            config.physical_width,
        )
        physical_y = scale(logical_x, config.logical_width, config.physical_height)
    elif config.rotation == "180":
        physical_x = config.physical_width - 1 - scale(
            logical_x,
            config.logical_width,
            config.physical_width,
        )
        physical_y = config.physical_height - 1 - scale(
            logical_y,
            config.logical_height,
            config.physical_height,
        )
    else:
        physical_x = scale(logical_x, config.logical_width, config.physical_width)
        physical_y = scale(logical_y, config.logical_height, config.physical_height)

    return (
        clamp(physical_x, 0, config.physical_width - 1),
        clamp(physical_y, 0, config.physical_height - 1),
    )


def scale(value: int, source_size: int, target_size: int) -> int:
    if source_size <= 1 or target_size <= 1:
        return 0
    return round(value * (target_size - 1) / (source_size - 1))


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


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


VIEWER_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NanoKVM Desk Agent</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; background: #111; color: #f4f4f4; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; box-sizing: border-box; }
    main { width: min(1040px, 100%); }
    header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
    h1 { font-size: 18px; margin: 0; font-weight: 650; }
    .viewer { display: grid; grid-template-columns: minmax(0, 1fr) 112px; gap: 16px; align-items: stretch; }
    .screen { background: #000; border: 1px solid #333; display: grid; place-items: center; overflow: hidden; min-width: 0; touch-action: none; }
    canvas { width: 100%; image-rendering: pixelated; display: block; }
    .controls { display: grid; grid-template-columns: 1fr; gap: 8px; align-content: center; }
    button { appearance: none; border: 1px solid #444; background: #1d1d1d; color: #f4f4f4; height: 56px; font-size: 24px; cursor: pointer; }
    button:hover:not(:disabled) { background: #292929; border-color: #666; }
    button:active:not(:disabled) { background: #333; }
    button:disabled { color: #666; cursor: not-allowed; }
    .meta { margin-top: 12px; color: #aaa; font-size: 13px; min-height: 18px; }
    @media (max-width: 700px) {
      .viewer { grid-template-columns: 1fr; }
      .controls { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>NanoKVM Desk Agent</h1>
    </header>
    <div class="viewer">
      <div class="screen">
        <canvas id="screen" width="320" height="172" aria-label="NanoKVM Desk screen"></canvas>
      </div>
      <div class="controls" aria-label="Knob controls">
        <button type="button" data-action="left" title="Rotate left" aria-label="Rotate left">↺</button>
        <button type="button" data-action="click" title="Click" aria-label="Click">⏎</button>
        <button type="button" data-action="long-click" title="Long press" aria-label="Long press">Long press</button>
        <button type="button" data-action="right" title="Rotate right" aria-label="Rotate right">↻</button>
      </div>
    </div>
    <div class="meta">
      screen: <span id="screen-status">connecting</span>
      · controls: <span id="control-status">ready</span>
      · touch: <span id="touch-status">ready</span>
    </div>
  </main>
  <script>
    const canvas = document.querySelector('#screen');
    const context = canvas.getContext('2d');
    const screenStatusEl = document.querySelector('#screen-status');
    const controlStatusEl = document.querySelector('#control-status');
    const touchStatusEl = document.querySelector('#touch-status');
    const buttons = Array.from(document.querySelectorAll('button[data-action]'));
    let metadata = null;
    let imageData = null;
    let pointerStart = null;

    function token() {
      return new URLSearchParams(window.location.hash.slice(1)).get('token') || '';
    }

    function headers() {
      return { 'X-NanoKVM-Desk-Token': token(), 'Content-Type': 'application/json' };
    }

    function setStatus(element, text) {
      element.textContent = text;
    }

    function setButtons(enabled) {
      buttons.forEach((button) => { button.disabled = !enabled; });
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: { ...headers(), ...(options.headers || {}) },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || data.error || `HTTP ${response.status}`);
      }
      return data;
    }

    function rgb565ToRgb(value) {
      return [
        Math.round(((value >> 11) & 0x1f) * 255 / 31),
        Math.round(((value >> 5) & 0x3f) * 255 / 63),
        Math.round((value & 0x1f) * 255 / 31),
      ];
    }

    function mapPhysicalToLogical(x, y) {
      if (metadata.rotation === 'clockwise') {
        return [metadata.physical_height - 1 - y, x];
      }
      if (metadata.rotation === 'counterclockwise') {
        return [y, metadata.physical_width - 1 - x];
      }
      if (metadata.rotation === '180') {
        return [metadata.physical_width - 1 - x, metadata.physical_height - 1 - y];
      }
      return [x, y];
    }

    function renderFrame(frame) {
      if (!metadata || !imageData || frame.byteLength !== metadata.frame_size) {
        return;
      }
      const source = new DataView(frame);
      const target = imageData.data;
      for (let y = 0; y < metadata.physical_height; y += 1) {
        for (let x = 0; x < metadata.physical_width; x += 1) {
          const sourceOffset = ((y * metadata.physical_width) + x) * 2;
          const value = source.getUint16(sourceOffset, true);
          const [red, green, blue] = rgb565ToRgb(value);
          const [logicalX, logicalY] = mapPhysicalToLogical(x, y);
          const targetOffset = ((logicalY * metadata.logical_width) + logicalX) * 4;
          target[targetOffset] = red;
          target[targetOffset + 1] = green;
          target[targetOffset + 2] = blue;
          target[targetOffset + 3] = 255;
        }
      }
      context.putImageData(imageData, 0, 0);
    }

    async function connectScreen() {
      if (!token()) {
        setStatus(screenStatusEl, 'missing token');
        setButtons(false);
        return;
      }
      try {
        metadata = await api('/api/screen/metadata');
        canvas.width = metadata.logical_width;
        canvas.height = metadata.logical_height;
        imageData = context.createImageData(metadata.logical_width, metadata.logical_height);
        setStatus(screenStatusEl, 'connecting');
        const response = await fetch('/api/screen/raw', { headers: headers() });
        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`);
        }
        setStatus(screenStatusEl, 'live');
        const reader = response.body.getReader();
        let carry = new Uint8Array(0);
        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            throw new Error('stream ended');
          }
          const merged = new Uint8Array(carry.length + value.length);
          merged.set(carry);
          merged.set(value, carry.length);
          let offset = 0;
          while (offset + metadata.frame_size <= merged.length) {
            renderFrame(merged.buffer.slice(offset, offset + metadata.frame_size));
            offset += metadata.frame_size;
          }
          carry = merged.slice(offset);
        }
      } catch (err) {
        setStatus(screenStatusEl, 'reconnecting');
        window.setTimeout(connectScreen, 1200);
      }
    }

    function eventPoint(event) {
      const rect = canvas.getBoundingClientRect();
      return {
        x: Math.max(0, Math.min(canvas.width - 1, (event.clientX - rect.left) * canvas.width / rect.width)),
        y: Math.max(0, Math.min(canvas.height - 1, (event.clientY - rect.top) * canvas.height / rect.height)),
      };
    }

    canvas.addEventListener('pointerdown', (event) => {
      pointerStart = eventPoint(event);
      canvas.setPointerCapture(event.pointerId);
    });

    canvas.addEventListener('pointerup', async (event) => {
      if (!pointerStart) {
        return;
      }
      const end = eventPoint(event);
      const dx = end.x - pointerStart.x;
      const dy = end.y - pointerStart.y;
      const distance = Math.hypot(dx, dy);
      setStatus(touchStatusEl, 'running');
      try {
        if (distance < 8) {
          await api('/api/input/tap', {
            method: 'POST',
            body: JSON.stringify({ x: end.x, y: end.y }),
          });
        } else {
          await api('/api/input/swipe', {
            method: 'POST',
            body: JSON.stringify({
              start_x: pointerStart.x,
              start_y: pointerStart.y,
              end_x: end.x,
              end_y: end.y,
            }),
          });
        }
        setStatus(touchStatusEl, 'ready');
      } catch (err) {
        setStatus(touchStatusEl, err.message || 'error');
      } finally {
        pointerStart = null;
      }
    });

    async function runAction(action) {
      setButtons(false);
      setStatus(controlStatusEl, 'running');
      try {
        if (action === 'click' || action === 'long-click') {
          await api('/api/input/knob/click', {
            method: 'POST',
            body: JSON.stringify({ press_seconds: action === 'long-click' ? 1.0 : 0.05 }),
          });
        } else {
          await api('/api/input/knob/rotate', {
            method: 'POST',
            body: JSON.stringify({ direction: action, notches: 1, steps_per_notch: 2 }),
          });
        }
        setStatus(controlStatusEl, 'ready');
      } catch (err) {
        setStatus(controlStatusEl, err.message || 'error');
      } finally {
        setButtons(true);
      }
    }

    buttons.forEach((button) => {
      button.addEventListener('click', () => runAction(button.dataset.action));
    });
    connectScreen();
  </script>
</body>
</html>
"""


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
