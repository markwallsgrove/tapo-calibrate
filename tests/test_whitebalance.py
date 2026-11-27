from pathlib import Path

from tapo_calibrate.frame import Box
from tapo_calibrate.whitebalance import CLIP, Gains, Step, calibrate, neutral, next_gains

from .conftest import FakeRig, as_rig


def test_neutral_within_tolerance() -> None:
    assert neutral((200, 201, 199), 0.02)
    assert not neutral((180, 200, 200), 0.02)
    assert not neutral((200, 200, 230), 0.02)


def test_near_clipping_is_never_neutral() -> None:
    assert not neutral((CLIP, CLIP, CLIP), 0.02)


def test_black_is_never_neutral() -> None:
    assert not neutral((0, 0, 0), 0.02)


def test_next_gains_scale_red_and_blue_to_green() -> None:
    assert next_gains(Gains(50, 50, 50), (180, 185, 240)) == Gains(51, 50, 39)


def test_next_gains_stay_in_range() -> None:
    assert next_gains(Gains(90, 50, 2), (10, 200, 250)) == Gains(100, 50, 2)
    assert next_gains(Gains(1, 50, 50), (250, 200, 0)) == Gains(1, 50, 100)


def test_calibrates_a_grey_card(tmp_path: Path) -> None:
    fake = FakeRig()
    steps: list[Step] = []
    settled: list[bool] = []
    result = calibrate(
        as_rig(fake), Box(0, 0, 1, 1), tmp_path, settle=lambda: settled.append(True), report=steps.append
    )
    assert result.converged
    assert neutral(steps[-1].card, 0.02)
    assert steps[0].gains == Gains(50, 50, 50)
    assert result.gains.b < result.gains.g < result.gains.r
    assert len(settled) == len(steps)
    assert fake.common["wb_type"] == "manual"


def test_gives_up_when_the_card_clips(tmp_path: Path) -> None:
    fake = FakeRig(scene=(250.0, 250.0, 250.0))
    result = calibrate(as_rig(fake), Box(0, 0, 1, 1), tmp_path, steps=3, settle=lambda: None, report=lambda _: None)
    assert not result.converged
    assert len(result.steps) == 3
