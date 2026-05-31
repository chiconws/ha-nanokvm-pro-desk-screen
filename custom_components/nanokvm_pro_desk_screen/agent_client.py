"""HTTP client for the installed NanoKVM Pro Desk screen agent."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import aiohttp
from PIL import Image


@dataclass(frozen=True)
class ScreenMetadata:
    """Screen geometry reported by the Desk agent."""

    physical_width: int = 172
    physical_height: int = 320
    logical_width: int = 320
    logical_height: int = 172
    bits_per_pixel: int = 16
    rotation: str = "clockwise"
    frame_size: int = 110080
    fps: float = 12.0


class DeskAgentClient:
    """Small HTTP client for the Desk screen agent."""

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
    ) -> None:
        """Initialize the Desk agent client."""
        self.session = session
        self.host = host
        self.port = port
        self.token = token

    @property
    def base_url(self) -> str:
        """Return the Desk agent base URL."""
        return f"http://{self.host}:{self.port}"

    @property
    def headers(self) -> dict[str, str]:
        """Return authentication headers for the Desk agent."""
        return {"X-NanoKVM-Desk-Token": self.token}

    async def async_health(self) -> dict[str, Any]:
        """Fetch the Desk agent health response."""
        return await self._async_get_json("/api/health")

    async def async_probe(self) -> dict[str, Any]:
        """Fetch the Desk agent probe response."""
        return await self._async_get_json("/api/probe")

    async def async_metadata(self) -> ScreenMetadata:
        """Fetch screen metadata."""
        payload = await self._async_get_json("/api/screen/metadata")
        return ScreenMetadata(
            physical_width=int(payload.get("physical_width", 172)),
            physical_height=int(payload.get("physical_height", 320)),
            logical_width=int(payload.get("logical_width", 320)),
            logical_height=int(payload.get("logical_height", 172)),
            bits_per_pixel=int(payload.get("bits_per_pixel", 16)),
            rotation=str(payload.get("rotation", "clockwise")),
            frame_size=int(payload.get("frame_size", 110080)),
            fps=float(payload.get("fps", 12.0)),
        )

    async def async_snapshot_jpeg(self, metadata: ScreenMetadata) -> bytes:
        """Read one raw RGB565 frame and return it as JPEG."""
        timeout = aiohttp.ClientTimeout(total=10)
        async with self.session.get(
            f"{self.base_url}/api/screen/raw",
            headers=self.headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            frame = await response.content.readexactly(metadata.frame_size)

        image = rgb565_to_image(frame, metadata)
        output = BytesIO()
        image.save(output, format="JPEG", quality=85)
        return output.getvalue()

    async def async_post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Post JSON to the Desk agent."""
        timeout = aiohttp.ClientTimeout(total=10)
        async with self.session.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            data = await response.json()
        return data if isinstance(data, dict) else {}

    async def _async_get_json(self, path: str) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=10)
        async with self.session.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        return payload if isinstance(payload, dict) else {}


def rgb565_to_image(data: bytes, metadata: ScreenMetadata) -> Image.Image:
    """Convert little-endian RGB565 framebuffer data to a logical RGB image."""
    if metadata.bits_per_pixel != 16:
        raise ValueError(f"unsupported bits per pixel: {metadata.bits_per_pixel}")
    if len(data) < metadata.frame_size:
        raise ValueError(
            f"not enough framebuffer data: expected {metadata.frame_size}, got {len(data)}"
        )

    physical = Image.new("RGB", (metadata.physical_width, metadata.physical_height))
    pixels = physical.load()
    if pixels is None:
        raise RuntimeError("failed to access image pixel buffer")
    offset = 0
    for y in range(metadata.physical_height):
        for x in range(metadata.physical_width):
            value = data[offset] | (data[offset + 1] << 8)
            offset += 2
            red = ((value >> 11) & 0x1F) * 255 // 31
            green = ((value >> 5) & 0x3F) * 255 // 63
            blue = (value & 0x1F) * 255 // 31
            pixels[x, y] = (red, green, blue)

    image = rotate_physical_to_logical(physical, metadata.rotation)
    logical_size = (metadata.logical_width, metadata.logical_height)
    if image.size != logical_size:
        image = image.resize(logical_size, Image.Resampling.NEAREST)
    return image


def rotate_physical_to_logical(image: Image.Image, rotation: str) -> Image.Image:
    """Rotate the physical portrait framebuffer into browser orientation."""
    if rotation == "clockwise":
        return image.transpose(Image.Transpose.ROTATE_270)
    if rotation == "counterclockwise":
        return image.transpose(Image.Transpose.ROTATE_90)
    if rotation == "180":
        return image.transpose(Image.Transpose.ROTATE_180)
    if rotation == "none":
        return image
    raise ValueError(f"unsupported rotation: {rotation}")
