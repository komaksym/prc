"""Minimal PNG variance probe for browser screenshots (stdlib only)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def luminance(path: str) -> list[float]:
    raw = Path(path).read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    width = height = 0
    ctype = 0
    body = b""
    while pos < len(raw):
        (length, kind) = struct.unpack(">I4s", raw[pos : pos + 8])
        data = raw[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", data)
            assert depth == 8 and interlace == 0 and ctype in (2, 6)
        elif kind == b"IDAT":
            body += data
        pos += 12 + length
    channels = 3 if ctype == 2 else 4
    stride = width * channels
    pixels = zlib.decompress(body)
    out: list[float] = []
    prev = bytearray(stride)
    p = 0
    for _ in range(height):
        f = pixels[p]
        p += 1
        line = bytearray(pixels[p : p + stride])
        p += stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                up = prev[i]
                upleft = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + paeth(left, up, upleft)) & 255
        for x in range(width):
            r, g, b = line[x * channels], line[x * channels + 1], line[x * channels + 2]
            out.append(0.299 * r + 0.587 * g + 0.114 * b)
        prev = line
    return out


def variance(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)
