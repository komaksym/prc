"""Pixel evidence that an infographic draws a line between two boxes of text.

The OCR gate checks words. This module checks structure: for two text boxes, PRC looks for one
connected run of drawn ink that both boxes touch, and that the straight segment between them
crosses. Two lines inside one panel share no border between them, so they do not count.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

Box = tuple[int, int, int, int]
"""Left, top, width and height in image pixels."""
SCALE = 2
DARK = 0.6
SATURATED = 0.4
REACH = 4
TEXT_PAD = 2
LINE_RUN = 1.5
"""A straight connector is an unbroken run of shared ink this many text heights long."""
CROSSINGS = 2
GAP = 2
"""Pooled pixels of growth on each side, so a line that stops short of a box still joins it."""

Ink = npt.NDArray[np.bool_]
Labels = npt.NDArray[np.int32]


@dataclass(frozen=True, slots=True)
class Link:
    """Whether drawn ink joins two text boxes in separate shapes.

    `run` is the longest unbroken stretch of shared ink across the gap along the axis that joins
    the boxes, in image pixels, and `crossings` counts separate runs of shared ink along the
    center-to-center segment.
    """

    drawn: bool
    shared: bool
    run: int
    crossings: int


def decode_rgb(png: Path) -> npt.NDArray[np.float32] | None:
    """RGB pixels in 0..1, or None when ffmpeg is missing or cannot read the file."""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return None
    try:
        size = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                str(png),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        ).stdout.strip()
        width, height = (int(part) for part in size.split(",")[:2])
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True,
            timeout=60,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if len(raw) != width * height * 3:
        return None
    return np.frombuffer(raw, np.uint8).reshape(height, width, 3).astype(np.float32) / np.float32(
        255
    )


def ink_mask(rgb: npt.NDArray[np.float32], text: list[Box]) -> Ink:
    """Dark or strongly colored pixels outside text, pooled to 1/SCALE size."""
    top = rgb.max(axis=2)
    sat = (top - rgb.min(axis=2)) / np.maximum(top, 1e-6)
    ink = (rgb.mean(axis=2) < DARK) | ((sat > SATURATED) & (top > 0.2))
    for left, upper, width, height in text:
        ink[
            max(0, upper - TEXT_PAD) : upper + height + TEXT_PAD,
            max(0, left - TEXT_PAD) : left + width + TEXT_PAD,
        ] = False
    rows, cols = ink.shape[0] // SCALE, ink.shape[1] // SCALE
    pooled = ink[: rows * SCALE, : cols * SCALE].reshape(rows, SCALE, cols, SCALE).any(axis=(1, 3))
    padded = np.pad(pooled, GAP)
    grown = np.zeros_like(pooled)
    for dy in range(2 * GAP + 1):
        for dx in range(2 * GAP + 1):
            grown |= padded[dy : dy + rows, dx : dx + cols]
    return np.asarray(grown, dtype=np.bool_)


def label(ink: Ink) -> Labels:
    """8-connected ink components, numbered from 1."""
    rows, cols = ink.shape
    out = np.zeros((rows, cols), np.int32)
    count = 0
    for y, x in zip(*np.nonzero(ink), strict=True):
        if out[y, x]:
            continue
        count += 1
        out[y, x] = count
        queue = deque([(int(y), int(x))])
        while queue:
            cy, cx = queue.popleft()
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < rows and 0 <= nx < cols and ink[ny, nx] and not out[ny, nx]:
                        out[ny, nx] = count
                        queue.append((ny, nx))
    return out


def _scaled(box: Box) -> Box:
    left, top, width, height = box
    return (left // SCALE, top // SCALE, max(1, width // SCALE), max(1, height // SCALE))


def touched(labels: Labels, box: Box, line_height: int) -> set[int]:
    """Components that rays leaving the box meet first, within REACH line heights."""
    left, top, width, height = _scaled(box)
    reach = max(2, REACH * line_height // SCALE)
    rows, cols = labels.shape
    starts: list[tuple[int, int, int, int]] = []
    for part in (1, 2, 3):
        x = left + width * part // 4
        y = top + height * part // 4
        starts += [(x, top - 1, 0, -1), (x, top + height, 0, 1)]
        starts += [(left - 1, y, -1, 0), (left + width, y, 1, 0)]
    found: set[int] = set()
    for x, y, dx, dy in starts:
        for step in range(reach):
            px, py = x + dx * step, y + dy * step
            if not (0 <= px < cols and 0 <= py < rows):
                break
            if labels[py, px]:
                found.add(int(labels[py, px]))
                break
    return found


def _center(box: Box) -> tuple[float, float]:
    left, top, width, height = _scaled(box)
    return (left + width / 2, top + height / 2)


def crossings(labels: Labels, one: Box, other: Box, parts: set[int]) -> int:
    """Separate runs of the components along the segment between the two box centers."""
    (x0, y0), (x1, y1) = _center(one), _center(other)
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    rows, cols = labels.shape
    runs = 0
    was = False
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        y = round(y0 + (y1 - y0) * i / steps)
        on = 0 <= y < rows and 0 <= x < cols and int(labels[y, x]) in parts
        runs += on and not was
        was = on
    return runs


def _longest(mask: Ink) -> int:
    """Longest run of True down any column."""
    best = 0
    for column in mask.T:
        edges = np.diff(np.concatenate(([0], column.astype(np.int8), [0])))
        starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
        if starts.size:
            best = max(best, int((ends - starts).max()))
    return best


def straight_run(labels: Labels, one: Box, other: Box, parts: set[int]) -> int:
    """Longest unbroken run of the components across the gap, along the axis that joins the boxes.

    Boxes stacked with shared columns are scanned down those columns; boxes side by side with
    shared rows are scanned along those rows. Other pairs give 0. In image pixels.
    """
    a, b = _scaled(one), _scaled(other)
    if a[1] > b[1]:
        a, b = b, a
    left, right = max(a[0], b[0]), min(a[0] + a[2], b[0] + b[2])
    if right > left and b[1] > a[1] + a[3]:
        gap = np.isin(labels[a[1] + a[3] : b[1], left:right], list(parts))
        return _longest(gap) * SCALE
    a, b = (a, b) if a[0] <= b[0] else (b, a)
    top, bottom = max(a[1], b[1]), min(a[1] + a[3], b[1] + b[3])
    if bottom > top and b[0] > a[0] + a[2]:
        gap = np.isin(labels[top:bottom, a[0] + a[2] : b[0]], list(parts))
        return _longest(gap.T) * SCALE
    return 0


def link(labels: Labels, one: Box, other: Box, line_height: int) -> Link:
    shared = touched(labels, one, line_height) & touched(labels, other, line_height)
    if not shared:
        return Link(drawn=False, shared=False, run=0, crossings=0)
    run, runs = straight_run(labels, one, other, shared), crossings(labels, one, other, shared)
    drawn = run >= LINE_RUN * line_height or runs >= CROSSINGS
    return Link(drawn=drawn, shared=True, run=run, crossings=runs)
