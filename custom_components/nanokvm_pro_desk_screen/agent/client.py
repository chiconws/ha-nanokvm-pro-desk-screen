"""HTTP client for the installed NanoKVM Pro Desk screen agent."""

from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any

import aiohttp
from PIL import Image

from .runtime import PHYSICAL_HEIGHT, PHYSICAL_WIDTH

TIMEOUT = aiohttp.ClientTimeout(total=10)


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
        self.base_url = f"http://{host}:{port}"
        self.headers = {"X-NanoKVM-Desk-Token": token}

    async def async_agent_hash(self) -> str:
        """Return the source hash the running agent reports; doubles as a health check."""
        async with self.session.get(
            f"{self.base_url}/api/health", headers=self.headers, timeout=TIMEOUT
        ) as response:
            response.raise_for_status()
            return str((await response.json()).get("agent_hash", ""))

    async def async_snapshot_jpeg(self) -> bytes:
        """Read one raw RGB565 frame and return it as JPEG."""
        async with self.session.get(
            f"{self.base_url}/api/screen/frame", headers=self.headers, timeout=TIMEOUT
        ) as response:
            response.raise_for_status()
            frame = await response.read()

        return await asyncio.get_running_loop().run_in_executor(None, rgb565_to_jpeg, frame)

    async def async_post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Post JSON to the Desk agent."""
        async with self.session.post(
            f"{self.base_url}{path}", headers=self.headers, json=payload, timeout=TIMEOUT
        ) as response:
            response.raise_for_status()
            data = await response.json()
        return data if isinstance(data, dict) else {}


def rgb565_to_jpeg(frame: bytes) -> bytes:
    """Convert a raw framebuffer frame to JPEG. Blocking; run in an executor."""
    output = BytesIO()
    rgb565_to_image(frame).save(output, format="JPEG", quality=85)
    return output.getvalue()


def rgb565_to_image(frame: bytes) -> Image.Image:
    """Decode the portrait RGB565 framebuffer and turn it the way the screen is mounted."""
    physical = Image.frombytes("RGB", (PHYSICAL_WIDTH, PHYSICAL_HEIGHT), frame, "raw", "BGR;16")
    return physical.transpose(Image.Transpose.ROTATE_270)
