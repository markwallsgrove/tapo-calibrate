"""The image settings the tool changes, and checks on new values."""

from collections.abc import Mapping, Sequence

WB_TYPES = frozenset({"auto", "manual", "locked"})
LEVELS = frozenset({"saturation", "chroma", "contrast", "luma", "sharpness", "wb_R_gain", "wb_G_gain", "wb_B_gain"})
ADJUSTABLE = LEVELS | {"wb_type"}
LOWEST = 0
HIGHEST = 100


class SettingError(ValueError):
    """A change names an unknown setting or a value the camera won't take."""


def parse_changes(args: Sequence[str]) -> dict[str, str]:
    """Turn KEY=VALUE arguments into a change for the camera."""
    change: dict[str, str] = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep:
            raise SettingError(f"{arg!r} is not KEY=VALUE")
        change[key] = check(key, value)
    if not change:
        raise SettingError("Give at least one KEY=VALUE")
    return change


def check(key: str, value: str) -> str:
    """The value as the camera expects it, or SettingError."""
    if key == "wb_type":
        if value not in WB_TYPES:
            raise SettingError(f"wb_type must be one of {', '.join(sorted(WB_TYPES))}")
        return value
    if key not in LEVELS:
        raise SettingError(f"Unknown setting {key!r}; known: {', '.join(sorted(ADJUSTABLE))}")
    if not value.isdigit() or not LOWEST <= int(value) <= HIGHEST:
        raise SettingError(f"{key} must be a whole number from {LOWEST} to {HIGHEST}")
    return str(int(value))


def adjustable(common: Mapping[str, str]) -> dict[str, str]:
    """Only the settings this tool changes, in a stable order."""
    return {key: common[key] for key in sorted(ADJUSTABLE) if key in common}
