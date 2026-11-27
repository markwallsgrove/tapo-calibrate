"""What the tool needs from a camera: its image settings and a frame."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class Rig(Protocol):
    """A camera whose image settings can be read and changed, and that gives frames."""

    def read(self) -> dict[str, str]:
        """Every field of the camera's image.common settings."""
        ...

    def write(self, change: Mapping[str, str]) -> None:
        """Change some image.common settings."""
        ...

    def grab(self, out: Path) -> Path:
        """Save one frame of the live picture to out."""
        ...
