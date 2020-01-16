#!/usr/bin/env python
import argparse

import helptext
import json
import sys

from cansender import CanSender
from videoplayer import VideoplayerApp


def main():
    global videofilename, canlogfilename
    parser = argparse.ArgumentParser(
        "python VideoAndCanPlayer",
        description="Replay a video in sync with a can bus logfile.")

    parser.add_argument('config', metavar='config-file', type=str,
                        help=helptext.HELP_CONFIG_FILE)

    # print help message when no arguments were given
    if len(sys.argv) < 1:
        parser.print_help(sys.stderr)
        import errno
        raise SystemExit(errno.EINVAL)
    results = parser.parse_args()

    with open(results.config, 'r') as read_file:
        config = json.load(read_file)

    # ---===--- Get the video file name --- #
    try:
        videofilename = config['video']['filename']
    except:
        if videofilename is None:
            return

    # ---===--- Get the canlog file name --- #
    try:
        canlogfilename = config['canlog']['filename']
    except:
        if canlogfilename is None:
            return

    bookmarks = config['video']['bookmarks']
    bookmarks.sort()

    ## todo -- rewrite for kivy
    # for fr in bookmarks:
    #     graph.DrawLine((fr, 0), (fr, 10), width=3, color='green')

    syncpoints = config['video']['syncpoints']
    if len(syncpoints) == 0:
        print("No synpoints for video, exit")

    cansender = CanSender(canlogfilename, config['canbus']['channel'], config['canbus']['interface'])
    cansender.start()

    VideoplayerApp(videofilename, syncpoints, bookmarks, cansender).run()

    config['video']['bookmarks'] = bookmarks
    config['video']['syncpoints'] = syncpoints
    with open(results.config, 'w') as outfile:
        json.dump(config, outfile, indent=3, sort_keys=True)
    cansender.exit()


main()
