#!/usr/bin/env python
import sys
import argparse
import json
import logging

import helptext
from canreader import CanbusPos
from cansender import CanSender

logger = logging.getLogger("VideoAndCanPlayer2")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        "python VideoAndCanPlayer",
        description="Replay a video in sync with a CAN bus logfile.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("config", metavar="config-file", type=str, help=helptext.HELP_CONFIG_FILE)
    parser.add_argument("--map", default=False, action="store_true", required=False, help="display a moving map")
    return parser.parse_args(argv)


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as read_file:
        return json.load(read_file)


def main(argv=None) -> int:
    # basic logging setup (stderr)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Failed to load config {args.config}: {e}", file=sys.stderr)
        return 2

    # Validate required keys and extract
    try:
        video_cfg = config["video"]
        canlog_cfg = config["canlog"]
        canbus_cfg = config["canbus"]
    except KeyError as e:
        print(f"Missing required top-level config key: {e}", file=sys.stderr)
        return 2

    try:
        videofilename = video_cfg["filename"]
    except KeyError:
        print("Missing required field: video.filename", file=sys.stderr)
        return 2

    try:
        canlogfilename = canlog_cfg["filename"]
    except KeyError:
        print("Missing required field: canlog.filename", file=sys.stderr)
        return 2

    # Optional/complex fields
    bookmarks = list(video_cfg.get("bookmarks", []))
    try:
        # defensive sort: expect list of [time, label]
        bookmarks.sort(key=lambda x: x[0])
    except Exception as e:
        print(f"Invalid bookmarks format: {e}", file=sys.stderr)
        return 2

    syncpoints_raw = video_cfg.get("syncpoints", {}) or {}
    try:
        syncpoints = {int(k): v for k, v in syncpoints_raw.items()}
    except Exception as e:
        print(f"Invalid syncpoints format: {e}", file=sys.stderr)
        return 2
    if not syncpoints:
        logger.info("No syncpoints for video")

    filter_out = canlog_cfg.get("filter_out", [])

    description = config.get("description", videofilename)

    # Start services
    cansender = CanSender(
        canlogfilename,
        canbus_cfg.get("channel"),
        canbus_cfg.get("interface"),
        with_internal_bus=True,
        filter_out=filter_out,
        name="CanSender",
    )

    position_srv = None
    try:
        cansender.start()
        if args.map:
            position_srv = CanbusPos(channel="internal", bustype="virtual")
            position_srv.start()

        # Heavy import is kept late on purpose (Kivy startup cost)
        from videoplayer import VideoplayerApp

        VideoplayerApp(videofilename, syncpoints, bookmarks, description, cansender, position_srv).run()
    finally:
        # Ensure clean shutdown
        try:
            cansender.exit()
        finally:
            if position_srv:
                position_srv.exit()

    # Persist updates back to the same config file
    config["video"]["bookmarks"] = bookmarks
    # Keep keys as strings in JSON for stability
    config["video"]["syncpoints"] = {str(k): v for k, v in syncpoints.items()}
    try:
        with open(args.config, "w", encoding="utf-8") as outfile:
            json.dump(config, outfile, indent=3, sort_keys=True, ensure_ascii=False)
    except OSError as e:
        print(f"Failed to write config {args.config}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
