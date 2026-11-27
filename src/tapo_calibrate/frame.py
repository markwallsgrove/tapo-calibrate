"""Frames from the camera's stream, and colour measurements on a box in a frame."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess
import time

RGB = tuple[float, float, float]
Pixel = tuple[int, int, int]
TIMEOUT = 30


class FrameError(Exception):
    """ffmpeg gave no frame or could not read an image."""


@dataclass(frozen=True)
class Box:
    """A part of the frame, as fractions (0-1) of its width and height from the top left."""

    x: float
    y: float
    w: float
    h: float

    @classmethod
    def parse(cls, values: Sequence[str]) -> "Box":
        """A box from four numbers: X Y W H."""
        if len(values) != 4:
            raise ValueError("A box is four numbers: X Y W H")
        x, y, w, h = (float(value) for value in values)
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > 1 or y + h > 1:
            raise ValueError("The box must lie inside the frame: 0 <= X, Y and X + W, Y + H <= 1")
        return cls(x, y, w, h)

    @property
    def crop(self) -> str:
        """The box as an ffmpeg crop filter."""
        return f"crop=iw*{self.w}:ih*{self.h}:iw*{self.x}:ih*{self.y}"


def grab(source: str, out: Path, tries: int = 3, wait: float = 2.0) -> Path:
    """Save one frame from a stream or file. Errors never quote the source, which may hold a login."""
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-rtsp_transport", "tcp", "-i", source, "-frames:v", "1", str(out)]
    if "://" not in source:
        cmd.remove("-rtsp_transport")
        cmd.remove("tcp")
    for attempt in range(tries):
        try:
            if subprocess.run(cmd, capture_output=True, timeout=TIMEOUT, check=False).returncode == 0:
                return out
        except subprocess.TimeoutExpired:
            pass
        if attempt + 1 < tries:
            time.sleep(wait)
    raise FrameError(f"No frame after {tries} tries. The camera allows one stream at a time: close other viewers.")


def pixels(image: Path, box: Box) -> list[Pixel]:
    """Every pixel inside the box."""
    result = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(image), "-vf", f"{box.crop},format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        raise FrameError(f"Could not read {image}")
    raw = result.stdout
    return [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw) - 2, 3)]


def mean(px: Sequence[Pixel]) -> RGB:
    """The average colour."""
    count = len(px)
    return (
        round(sum(p[0] for p in px) / count, 1),
        round(sum(p[1] for p in px) / count, 1),
        round(sum(p[2] for p in px) / count, 1),
    )


def brightest(px: Sequence[Pixel], share: float) -> RGB:
    """The average colour of the brightest share (0-1) of the pixels, such as white flecks on a stone."""
    if not 0 < share <= 1:
        raise ValueError("share must be above 0 and at most 1")
    ranked = sorted(px, key=sum, reverse=True)
    return mean(ranked[: max(1, round(len(ranked) * share))])


def clipped(px: Sequence[Pixel], level: int = 255) -> float:
    """The share of pixels with any channel at or above level."""
    return sum(1 for p in px if max(p) >= level) / len(px)
