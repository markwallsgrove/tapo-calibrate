from collections.abc import Callable
import json
from pathlib import Path
import sys

import pytest

from tapo_calibrate.cli import main, run
from tapo_calibrate.config import ENV_PASSWORD, Config
from tapo_calibrate.rig import Rig

from .conftest import ENV, FakeRig, as_rig, solid


def opener(fake: FakeRig) -> Callable[[Config], Rig]:
    return lambda _config: as_rig(fake)


def lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_show(rig: FakeRig, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show"], env=ENV, open_rig=opener(rig)) == 0
    assert lines(capsys) == [
        {
            "contrast": "50",
            "saturation": "50",
            "wb_B_gain": "50",
            "wb_G_gain": "50",
            "wb_R_gain": "50",
            "wb_type": "auto",
        }
    ]


def test_set(rig: FakeRig, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["set", "saturation=40", "contrast=70"], env=ENV, open_rig=opener(rig)) == 0
    assert rig.writes == [{"saturation": "40", "contrast": "70"}]
    assert lines(capsys)[0]["contrast"] == "70"


def test_set_rejects_a_bad_value(rig: FakeRig, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["set", "contrast=200"], env=ENV, open_rig=opener(rig)) == 1
    assert rig.writes == []
    assert "0 to 100" in capsys.readouterr().err


def test_backup_and_restore(rig: FakeRig, tmp_path: Path) -> None:
    backup = tmp_path / "backup.json"
    assert main(["backup", str(backup)], env=ENV, open_rig=opener(rig)) == 0
    rig.common.update({"saturation": "10", "wb_type": "manual"})
    assert main(["restore", str(backup)], env=ENV, open_rig=opener(rig)) == 0
    assert rig.common["saturation"] == "50"
    assert rig.common["wb_type"] == "auto"
    assert "exp_type" not in rig.writes[-1]


def test_snapshot(rig: FakeRig, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["snapshot", str(tmp_path / "frame.png")], env=ENV, open_rig=opener(rig)) == 0
    assert Path(str(lines(capsys)[0]["frame"])).exists()


def test_measure_needs_no_camera(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    image = solid(tmp_path / "grey.png", (32, 64, 96))
    assert main(["measure", str(image), "0", "0", "1", "1", "--brightest", "0.02"], env={}) == 0
    assert lines(capsys) == [{"mean": [32.0, 64.0, 96.0], "clipped": 0.0, "brightest": [32.0, 64.0, 96.0]}]


def test_measure_without_brightest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    image = solid(tmp_path / "grey.png", (32, 64, 96))
    assert main(["measure", str(image), "0", "0", "1", "1"], env={}) == 0
    assert "brightest" not in lines(capsys)[0]


def test_measure_reports_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["measure", str(tmp_path / "missing.png"), "0", "0", "1", "1"], env={}) == 1
    assert "Could not read" in capsys.readouterr().err


def test_calibrate_keeps_gains_that_work(rig: FakeRig, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    backup = tmp_path / "backup.json"
    args = ["calibrate", "0", "0", "1", "1", "--frames", str(tmp_path / "frames"), "--backup", str(backup)]
    assert main(args, env=ENV, open_rig=opener(rig), settle=lambda: None) == 0
    out = lines(capsys)
    assert out[-1]["converged"] is True
    assert rig.common["wb_type"] == "manual"
    assert int(rig.common["wb_B_gain"]) < 50
    assert json.loads(backup.read_text())["wb_type"] == "auto"


def test_calibrate_puts_white_balance_back_when_it_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake = FakeRig(scene=(250.0, 250.0, 250.0))
    args = ["calibrate", "0", "0", "1", "1", "--steps", "2", "--frames", str(tmp_path), "--backup", str(tmp_path / "b")]
    assert main(args, env=ENV, open_rig=opener(fake), settle=lambda: None) == 0
    assert lines(capsys)[-1]["converged"] is False
    assert fake.common["wb_type"] == "auto"
    assert fake.common["wb_R_gain"] == "50"


def test_missing_settings(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show"], env={}) == 2
    assert "TAPO_HOST" in capsys.readouterr().err


class BrokenRig(FakeRig):
    def read(self) -> dict[str, str]:
        raise Exception(f"login failed for {ENV[ENV_PASSWORD]}")


def test_camera_errors_hide_the_password(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["show"], env=ENV, open_rig=opener(BrokenRig())) == 1
    err = capsys.readouterr().err
    assert "cloud-secret" not in err
    assert "Camera error: login failed for ***" in err


def test_console_script_exits_with_the_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    image = solid(tmp_path / "grey.png", (32, 64, 96))
    monkeypatch.setattr(sys, "argv", ["tapo-calibrate", "measure", str(image), "0", "0", "1", "1"])
    with pytest.raises(SystemExit) as exit_:
        run()
    assert exit_.value.code == 0
    assert lines(capsys)[0]["mean"] == [32.0, 64.0, 96.0]
