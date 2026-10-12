from __future__ import annotations

import struct

from custom_components.nanokvm_pro_desk_screen.agent_client import (
    ScreenMetadata,
    rgb565_to_image,
    rgb565_to_jpeg,
)


def test_rgb565_frame_is_decoded_and_rotated_clockwise() -> None:
    # physical 2x3 portrait frame, one distinct colour per pixel
    values = [0xF800, 0x07E0, 0x001F, 0xFFFF, 0x0000, 0x8410]
    metadata = ScreenMetadata(
        physical_width=2,
        physical_height=3,
        logical_width=3,
        logical_height=2,
        frame_size=12,
    )
    image = rgb565_to_image(struct.pack("<6H", *values), metadata)

    assert image.size == (3, 2)
    # physical (x, y) lands on logical (height - 1 - y, x)
    assert image.getpixel((2, 0)) == (255, 0, 0)
    assert image.getpixel((2, 1)) == (0, 255, 0)
    assert image.getpixel((1, 0)) == (0, 0, 255)
    assert image.getpixel((1, 1)) == (255, 255, 255)
    assert image.getpixel((0, 0)) == (0, 0, 0)
    assert image.getpixel((0, 1)) == (131, 129, 131)


def test_rgb565_to_jpeg_returns_a_jpeg() -> None:
    metadata = ScreenMetadata()

    assert rgb565_to_jpeg(bytes(metadata.frame_size), metadata)[:2] == b"\xff\xd8"
