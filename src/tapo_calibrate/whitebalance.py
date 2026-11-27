"""Find manual white balance gains that make a grey card in the picture neutral."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .frame import RGB, Box, mean, pixels
from .rig import Rig

# A channel at or above this is too close to clipping to measure.
CLIP = 235
LOWEST_GAIN = 1
HIGHEST_GAIN = 100


@dataclass(frozen=True)
class Gains:
    """Manual white balance gains, 1-100 each."""

    r: int
    g: int
    b: int

    def change(self) -> dict[str, str]:
        """The gains as a manual white balance change for the camera."""
        return {"wb_type": "manual", "wb_R_gain": str(self.r), "wb_G_gain": str(self.g), "wb_B_gain": str(self.b)}


@dataclass(frozen=True)
class Step:
    """One try: the gains set and the card's colour they gave."""

    gains: Gains
    card: RGB


@dataclass(frozen=True)
class Result:
    """Whether the card came out neutral, and every step on the way."""

    converged: bool
    gains: Gains
    steps: list[Step]


def neutral(card: RGB, tolerance: float) -> bool:
    """Red and blue within tolerance of green, with nothing near clipping."""
    r, g, b = card
    return max(card) < CLIP and g > 0 and abs(r / g - 1) < tolerance and abs(b / g - 1) < tolerance


def next_gains(gains: Gains, card: RGB) -> Gains:
    """Scale red and blue towards green; green stays as the reference."""
    r, g, b = card

    def scaled(gain: int, channel: float) -> int:
        return max(LOWEST_GAIN, min(HIGHEST_GAIN, round(gain * g / max(channel, 1))))

    return Gains(scaled(gains.r, r), gains.g, scaled(gains.b, b))


def calibrate(
    rig: Rig,
    box: Box,
    frames: Path,
    *,
    start: Gains = Gains(50, 50, 50),
    steps: int = 10,
    tolerance: float = 0.02,
    settle: Callable[[], None],
    report: Callable[[Step], None],
) -> Result:
    """Set gains, measure the card and adjust until it is neutral or the steps run out."""
    gains = start
    done: list[Step] = []
    for number in range(steps):
        rig.write(gains.change())
        settle()
        step = Step(gains, mean(pixels(rig.grab(frames / f"calibrate_{number}.jpg"), box)))
        done.append(step)
        report(step)
        if neutral(step.card, tolerance):
            return Result(True, gains, done)
        gains = next_gains(gains, step.card)
    return Result(False, gains, done)
