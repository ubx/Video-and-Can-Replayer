#!/usr/bin/env python
import argparse
import json

import helptext
from canreader import CanbusPos
from cansender import CanSender


def main():
    global videofilename, canlogfilename
    parser = argparse.ArgumentParser(
        "python VideoAndCanPlayer",
        description="Replay a video in sync with a can bus logfile.",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('config', metavar='config-file', type=str,
                        help=helptext.HELP_CONFIG_FILE)

    parser.add_argument('--map', default=False, action='store_true', required=False,
                        help='display a moving map')

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

    syncpoints = {int(k): v for k, v in config['video']['syncpoints'].items()}
    if len(syncpoints) == 0:
        print("No syncpoints for video")

    try:
        filter_out = config['canlog']['filter_out']
    except:
        filter_out = []

    cansender = CanSender(canlogfilename, config['canbus']['channel'], config['canbus']['interface'],
                          with_internal_bus=True, filter_out=filter_out, name='CanSender')
    cansender.start()

    if results.map:
        position_srv = CanbusPos(channel='internal', bustype='virtual')
        position_srv.start()
    else:
        position_srv = None

    from videoplayer import VideoplayerApp
    VideoplayerApp(videofilename, syncpoints, bookmarks, cansender, position_srv).run()
    cansender.exit()

    if position_srv:
        position_srv.exit()

    config['video']['bookmarks'] = bookmarks
    config['video']['syncpoints'] = syncpoints

    with open(results.config, 'w') as outfile:
        json.dump(config, outfile, indent=3, sort_keys=True)


main()
