from pathlib import Path

import pytest

from tapo_calibrate import frame
from tapo_calibrate.frame import Box, FrameError, brightest, clipped, grab, mean, pixels

from .conftest import solid


def test_box_from_four_numbers() -> None:
    box = Box.parse(["0.1", "0.2", "0.3", "0.4"])
    assert box == Box(0.1, 0.2, 0.3, 0.4)
    assert box.crop == "crop=iw*0.3:ih*0.4:iw*0.1:ih*0.2"


@pytest.mark.parametrize(
    "values",
    [
        ["0", "0", "1"],
        ["-0.1", "0", "0.5", "0.5"],
        ["0", "0", "0", "0.5"],
        ["0.6", "0", "0.5", "0.5"],
        ["0", "0.6", "0.5", "0.5"],
    ],
)
def test_box_must_lie_inside_the_frame(values: list[str]) -> None:
    with pytest.raises(ValueError, match="box"):
        Box.parse(values)


def test_measures_a_box(tmp_path: Path) -> None:
    image = solid(tmp_path / "grey.png", (32, 64, 96))
    px = pixels(image, Box(0.25, 0.25, 0.5, 0.5))
    assert len(px) == 32 * 18
    assert mean(px) == (32.0, 64.0, 96.0)


def test_unreadable_image(tmp_path: Path) -> None:
    with pytest.raises(FrameError, match="Could not read"):
        pixels(tmp_path / "missing.png", Box(0, 0, 1, 1))


def test_brightest_share() -> None:
    px = [(10, 10, 10)] * 98 + [(250, 240, 230), (240, 230, 220)]
    assert brightest(px, 0.02) == (245.0, 235.0, 225.0)
    assert brightest(px, 0.001) == (250.0, 240.0, 230.0)


@pytest.mark.parametrize("share", [0, 1.5])
def test_brightest_share_range(share: float) -> None:
    with pytest.raises(ValueError, match="share"):
        brightest([(1, 1, 1)], share)


def test_clipped_share() -> None:
    assert clipped([(255, 0, 0), (10, 10, 10), (0, 0, 255), (254, 254, 254)]) == 0.5


def test_grabs_a_frame_from_a_file(tmp_path: Path) -> None:
    source = solid(tmp_path / "source.png", (1, 2, 3))
    out = grab(str(source), tmp_path / "frame.png")
    assert out.exists()


def test_grab_failure_never_quotes_the_source(tmp_path: Path) -> None:
    source = "rtsp://user:secret@127.0.0.1:9/stream1"
    with pytest.raises(FrameError) as err:
        grab(source, tmp_path / "frame.jpg", tries=2, wait=0)
    assert "secret" not in str(err.value)
    assert "2 tries" in str(err.value)


def test_grab_gives_up_on_a_stream_that_hangs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(frame, "TIMEOUT", 0.001)
    source = solid(tmp_path / "source.png", (1, 2, 3))
    with pytest.raises(FrameError, match="1 tries"):
        grab(str(source), tmp_path / "frame.png", tries=1)
