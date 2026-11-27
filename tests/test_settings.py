import pytest

from tapo_calibrate.settings import SettingError, adjustable, parse_changes


def test_parses_changes() -> None:
    assert parse_changes(["saturation=40", "wb_type=manual", "wb_B_gain=044"]) == {
        "saturation": "40",
        "wb_type": "manual",
        "wb_B_gain": "44",
    }


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "at least one"),
        (["saturation"], "not KEY=VALUE"),
        (["exposure=5"], "Unknown setting"),
        (["contrast=101"], "0 to 100"),
        (["contrast=-1"], "0 to 100"),
        (["contrast=high"], "0 to 100"),
        (["wb_type=daylight"], "wb_type must be one of"),
    ],
)
def test_rejects_bad_changes(args: list[str], message: str) -> None:
    with pytest.raises(SettingError, match=message):
        parse_changes(args)


def test_adjustable_keeps_only_known_settings_in_order() -> None:
    common = {"wb_type": "auto", "exp_type": "auto", "contrast": "50", "saturation": "50"}
    assert list(adjustable(common).items()) == [("contrast", "50"), ("saturation", "50"), ("wb_type", "auto")]
