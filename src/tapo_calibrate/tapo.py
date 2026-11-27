"""The rig for a real Tapo camera: pytapo for the settings, ffmpeg on the RTSP stream for frames."""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pytapo import Tapo

from .config import Config
from .frame import grab

# The local API logs in as admin with the Tapo cloud account's password.
ADMIN = "admin"
GET = {"image": {"name": "common"}}


def open_tapo(config: Config) -> "TapoRig":
    """The real camera."""
    return TapoRig(config)


class TapoRig:
    """A Tapo camera on the local network."""

    def __init__(self, config: Config) -> None:
        """Log in to the camera's local API."""
        self._config = config
        self._tapo = Tapo(config.host, ADMIN, config.password, config.password)

    def read(self) -> dict[str, str]:
        """Every field of image.common."""
        response = cast(dict[str, dict[str, dict[str, str]]], self._tapo.executeFunction("getLightFrequencyInfo", GET))
        return dict(response["image"]["common"])

    def write(self, change: Mapping[str, str]) -> None:
        """Change some image.common fields."""
        self._tapo.executeFunction("setLightFrequencyInfo", {"image": {"common": dict(change)}})

    def grab(self, out: Path) -> Path:
        """One frame from the high quality stream."""
        return grab(self._config.rtsp_url, out)
