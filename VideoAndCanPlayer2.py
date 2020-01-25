#!/usr/bin/env python
import argparse
import threading

import helptext
import json
import sys

from canreader import CanbusPos
from cansender import CanSender
from videoplayer import VideoplayerApp


def list_threads(txt):
    main_thread = threading.current_thread()
    for t in threading.enumerate():
        if t is main_thread:
            continue
        print(txt,t.getName(), t.isDaemon())
        ##t.join()

def main():
    global videofilename, canlogfilename
    parser = argparse.ArgumentParser(
        "python VideoAndCanPlayer",
        description="Replay a video in sync with a can bus logfile.")

    parser.add_argument('config', metavar='config-file', type=str,
                        help=helptext.HELP_CONFIG_FILE)

    parser.add_argument('--map', default=False, action='store_true', required=False,
                        help='display a moving map')

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

    syncpoints = config['video']['syncpoints']
    if len(syncpoints) == 0:
        print("No synpoints for video, exit")

    cansender = CanSender(canlogfilename, config['canbus']['channel'], config['canbus']['interface'],
                          with_internal_bus=True, name='CanSender')
    cansender.start()

    if results.map:
        position_srv = CanbusPos(channel='internal', bustype='virtual')
        position_srv.start()
    else:
        position_srv = None

    VideoplayerApp(videofilename, syncpoints, bookmarks, cansender, position_srv).run()
    cansender.exit()

    config['video']['bookmarks'] = bookmarks
    config['video']['syncpoints'] = syncpoints

    with open(results.config, 'w') as outfile:
        json.dump(config, outfile, indent=3, sort_keys=True)

main()
list_threads('after main')

