"""The tapo-calibrate command. Every result is one JSON object per line on stdout."""

import argparse
from collections.abc import Callable, Mapping, Sequence
import json
import os
from pathlib import Path
import sys
import time

from .config import Config, ConfigError
from .frame import Box, FrameError, brightest, clipped, mean, pixels
from .rig import Rig
from .settings import SettingError, adjustable, parse_changes
from .tapo import open_tapo
from .whitebalance import Step, calibrate

WHITE_BALANCE = ("wb_type", "wb_R_gain", "wb_G_gain", "wb_B_gain")
SETTLE_SECONDS = 4.0


def parser() -> argparse.ArgumentParser:
    """The command line."""
    top = argparse.ArgumentParser(prog="tapo-calibrate", description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser("show", help="print the image settings this tool changes")
    change = sub.add_parser("set", help="change image settings, e.g. saturation=40 contrast=70")
    change.add_argument("changes", nargs="+", metavar="KEY=VALUE")
    backup = sub.add_parser("backup", help="save every image setting to a JSON file")
    backup.add_argument("file", type=Path)
    restore = sub.add_parser("restore", help="put back the settings this tool changes from a backup")
    restore.add_argument("file", type=Path)
    snapshot = sub.add_parser("snapshot", help="save one frame of the live picture")
    snapshot.add_argument("out", type=Path, nargs="?", default=Path("snapshot.jpg"))
    measure = sub.add_parser("measure", help="measure the colour in a box of an image")
    measure.add_argument("image", type=Path)
    measure.add_argument("box", nargs=4, metavar=("X", "Y", "W", "H"), help="fractions of the frame, 0-1")
    measure.add_argument("--brightest", type=float, metavar="SHARE", help="also the brightest share, e.g. 0.02")
    cal = sub.add_parser("calibrate", help="find white balance gains that make a grey card neutral")
    cal.add_argument("box", nargs=4, metavar=("X", "Y", "W", "H"), help="the card, as fractions of the frame")
    cal.add_argument("--frames", type=Path, default=Path("frames"), help="where to keep each step's frame")
    cal.add_argument("--backup", type=Path, default=Path("backup.json"), help="where to save the old settings")
    cal.add_argument("--steps", type=int, default=10)
    cal.add_argument("--tolerance", type=float, default=0.02, help="how close red and blue must be to green")
    return top


def emit(value: object) -> None:
    """Print one result line."""
    print(json.dumps(value), flush=True)


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    open_rig: Callable[[Config], Rig] = open_tapo,
    settle: Callable[[], None] = lambda: time.sleep(SETTLE_SECONDS),
) -> int:
    """Run one command. Errors go to stderr with every secret hidden."""
    args = parser().parse_args(argv)
    if args.command == "measure":
        return _guarded(None, lambda: _measure(args))
    try:
        config = Config.from_env(os.environ if env is None else env)
    except ConfigError as err:
        print(err, file=sys.stderr)
        return 2
    return _guarded(config, lambda: _run(args, open_rig(config), settle))


def _guarded(config: Config | None, action: Callable[[], None]) -> int:
    try:
        action()
    except (SettingError, FrameError, ValueError, OSError) as err:
        print(config.scrub(str(err)) if config else str(err), file=sys.stderr)
        return 1
    except Exception as err:
        print(config.scrub(f"Camera error: {err}") if config else str(err), file=sys.stderr)
        return 1
    return 0


def _measure(args: argparse.Namespace) -> None:
    px = pixels(args.image, Box.parse(args.box))
    result: dict[str, object] = {"mean": mean(px), "clipped": round(clipped(px), 4)}
    if args.brightest is not None:
        result["brightest"] = brightest(px, args.brightest)
    emit(result)


def _run(args: argparse.Namespace, rig: Rig, settle: Callable[[], None]) -> None:
    match args.command:
        case "show":
            emit(adjustable(rig.read()))
        case "set":
            rig.write(parse_changes(args.changes))
            emit(adjustable(rig.read()))
        case "backup":
            args.file.write_text(json.dumps(rig.read(), indent=1))
            emit({"saved": str(args.file)})
        case "restore":
            rig.write(adjustable(json.loads(args.file.read_text())))
            emit(adjustable(rig.read()))
        case "snapshot":
            emit({"frame": str(rig.grab(args.out))})
        case _:
            _calibrate(args, rig, settle)


def _calibrate(args: argparse.Namespace, rig: Rig, settle: Callable[[], None]) -> None:
    box = Box.parse(args.box)
    before = rig.read()
    args.backup.write_text(json.dumps(before, indent=1))
    args.frames.mkdir(parents=True, exist_ok=True)

    def report(step: Step) -> None:
        emit({"gains": [step.gains.r, step.gains.g, step.gains.b], "card": step.card})

    result = calibrate(rig, box, args.frames, steps=args.steps, tolerance=args.tolerance, settle=settle, report=report)
    if not result.converged:
        rig.write({key: before[key] for key in WHITE_BALANCE if key in before})
    emit({"converged": result.converged, "gains": result.gains.change(), "backup": str(args.backup)})


def run() -> None:
    """The console script."""
    sys.exit(main())
