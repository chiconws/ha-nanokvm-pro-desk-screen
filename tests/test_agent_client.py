from __future__ import annotations

import struct

from custom_components.nanokvm_pro_desk_screen.agent.client import (
    rgb565_to_image,
    rgb565_to_jpeg,
)
from custom_components.nanokvm_pro_desk_screen.agent.runtime import (
    FRAME_SIZE,
    PHYSICAL_HEIGHT,
    PHYSICAL_WIDTH,
)


def test_rgb565_frame_is_decoded_and_rotated_clockwise() -> None:
    frame = bytearray(FRAME_SIZE)

    def put(x: int, y: int, value: int) -> None:
        struct.pack_into("<H", frame, (y * PHYSICAL_WIDTH + x) * 2, value)

    put(0, 0, 0xF800)
    put(PHYSICAL_WIDTH - 1, 0, 0x07E0)
    put(0, PHYSICAL_HEIGHT - 1, 0x001F)
    put(1, 0, 0x8410)
    image = rgb565_to_image(bytes(frame))

    assert image.size == (320, 172)
    # physical (x, y) lands on logical (319 - y, x)
    assert image.getpixel((319, 0)) == (255, 0, 0)
    assert image.getpixel((319, 171)) == (0, 255, 0)
    assert image.getpixel((0, 0)) == (0, 0, 255)
    assert image.getpixel((319, 1)) == (131, 129, 131)


def test_rgb565_to_jpeg_returns_a_jpeg() -> None:
    assert rgb565_to_jpeg(bytes(FRAME_SIZE))[:2] == b"\xff\xd8"
