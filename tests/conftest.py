from collections.abc import Mapping
from pathlib import Path
import subprocess

import pytest

from tapo_calibrate.config import ENV_HOST, ENV_PASSWORD, ENV_RTSP_PASSWORD, ENV_RTSP_USER
from tapo_calibrate.rig import Rig

# A grey card under a blue-heavy light, as the camera sees it with every gain at 50.
SCENE = (180.0, 185.0, 240.0)
ENV = {ENV_HOST: "192.0.2.10", ENV_PASSWORD: "cloud-secret", ENV_RTSP_USER: "cam-user", ENV_RTSP_PASSWORD: "p@ss:word"}


def solid(out: Path, rgb: tuple[int, int, int], size: str = "64x36") -> Path:
    """An image of one colour, made by ffmpeg."""
    colour = "0x{:02x}{:02x}{:02x}".format(*rgb)
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={colour}:s={size}",
            "-frames:v",
            "1",
            str(out),
        ],
        check=True,
    )
    return out


class FakeRig:
    """A camera whose picture of the grey card follows its white balance gains."""

    def __init__(self, scene: tuple[float, float, float] = SCENE) -> None:
        self.scene = scene
        self.common = {
            "wb_type": "auto",
            "wb_R_gain": "50",
            "wb_G_gain": "50",
            "wb_B_gain": "50",
            "saturation": "50",
            "contrast": "50",
            "exp_type": "auto",
        }
        self.writes: list[dict[str, str]] = []

    def read(self) -> dict[str, str]:
        return dict(self.common)

    def write(self, change: Mapping[str, str]) -> None:
        self.writes.append(dict(change))
        self.common.update(change)

    def grab(self, out: Path) -> Path:
        gains = (int(self.common["wb_R_gain"]), int(self.common["wb_G_gain"]), int(self.common["wb_B_gain"]))
        r, g, b = (min(255, round(level * gain / 50)) for level, gain in zip(self.scene, gains, strict=True))
        return solid(out.with_suffix(".png"), (r, g, b))


@pytest.fixture
def rig() -> FakeRig:
    return FakeRig()


def as_rig(fake: FakeRig) -> Rig:
    """The fake, checked by the type checker against the Rig protocol."""
    return fake
