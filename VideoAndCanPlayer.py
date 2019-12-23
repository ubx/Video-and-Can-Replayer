#!/usr/bin/env python
import argparse

import helptext
import json
import sys
from datetime import datetime
import time
import PySimpleGUI as sg
import cv2 as cv

from PySimpleGUI import Button

##Audio: from ffpyplayer.player import MediaPlayer
from cansender import CanSender


def inbetween(list, val):
    prev, next = None, None
    if list is not None:
        if val < list[0]: next = list[0]
        if val > list[-1]: prev = list[-1]
        if len(list) > 1:
            for i in range(0, len(list) - 1):
                if val in range(list[i], list[i + 1]):
                    prev = list[i]
                    next = list[i + 1]
                    break
    return prev, next


def frame2time(cur_frame, syncpoints, fps):
    fsp = next(iter(syncpoints))  ## first syncpoint !
    t1 = syncpoints[fsp]
    return t1 - ((int(fsp) - cur_frame) / fps)


def calcfps(syncpoints):
    fpss = []
    sp0 = None
    if len(syncpoints) > 1:
        for sp in syncpoints:
            if sp0 is not None:
                fpss.append((int(sp) - int(sp0)) / (syncpoints[sp] - syncpoints[sp0]))
            sp0 = sp
    return fpss


frameT0 = None
frameC0 = 0


def frame_extradiff(cur_frame, fps, init=False):
    global frameT0, frameC0
    if init or frameT0 is None:
        frameT0 = time.time()
        frameC0 = cur_frame
        return 0.0
    diff = (time.time() - frameT0) - ((cur_frame - frameC0) / fps)
    if diff > 1.0 or diff < -1.0:
        diff = 0.0
    print('F_diff:', diff)
    return diff


messageT0 = None
messageTsT0 = None


def main():
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

    config = {}
    with open(results.config, 'r') as read_file:
        config = json.load(read_file)

    # ---===--- Get the videofilename --- #
    videofilename = None
    try:
        videofilename = config['video']['filename']
    except:
        videofilename = sg.popup_get_file('Video filename to play')
        if videofilename is None:
            return

    # ---===--- Get the canfilename --- #
    canlogfilename = None
    try:
        canlogfilename = config['canlog']['filename']
    except:
        canlogfilename = sg.popup_get_file('Can logfile name to play')
        if canlogfilename is None:
            return

    videoFile = cv.VideoCapture(videofilename)
    ##Audio: player = MediaPlayer(videofilename)

    cv.namedWindow('frame')

    # ---===--- Get some Stats --- #
    num_frames = videoFile.get(cv.CAP_PROP_FRAME_COUNT)
    fps = videoFile.get(cv.CAP_PROP_FPS)
    sg.change_look_and_feel('Dark Blue 3')

    # ---===--- define the window layout --- #
    slider = sg.Slider(range=(0, num_frames), size=(60, 10), orientation='h', key='-slider-')
    graph = sg.Graph(canvas_size=(650, 10), graph_bottom_left=(0, 0), graph_top_right=(num_frames, 10),
                     background_color='white', key='-graph')
    pause_button: Button = sg.Button('||', key='Pause', size=(5, 1), font='Helvetica 14')
    layout = [[sg.Text('Video and Can reply', size=(15, 1), font='Helvetica 20')],
              [slider],
              [graph],
              [sg.Button('Bookmark', size=(7, 1), font='Helvetica 14'),
               sg.Button('Next', size=(5, 1), font='Helvetica 14'),
               sg.Button('Prev', size=(5, 1), font='Helvetica 14'), pause_button,
               sg.Button('Sync', size=(5, 1), font='Helvetica 14')],
              [sg.Button('Exit', size=(5, 1), pad=((600, 0), 3), font='Helvetica 14')]]

    # create the window and show it without the plot
    window = sg.Window('Replay Application', layout, no_titlebar=False, location=(0, 0), finalize=True)

    pause = False
    trigger_pause = False
    cur_frame: int = 0
    bookmarks = config['video']['bookmarks']
    bookmarks.sort()
    for fr in bookmarks:
        graph.DrawLine((fr, 0), (fr, 10), width=3, color='green')

    syncpoints = config['video']['syncpoints']
    if len(syncpoints) == 0:
        print("No synpoints for video, exit")
    aspectratio = config['video']['aspectratio']
    ## fps andr fps calculated!
    fpss = calcfps(syncpoints)
    print(fps, fpss)
    if len(fpss) > 0:
        fps = fpss[0]

    ### sp = f'{25075}'  ## no int key in json !!!

    canthread = None
    while videoFile.isOpened():
        t1 = time.time()
        event, values = window.read(timeout=0)
        ##print(event, values)
        if event in ('Exit', None):
            if canthread is not None:
                canthread.stop()
            break

        if event == 'Bookmark':
            graph.DrawLine((cur_frame, 0), (cur_frame, 10), width=3, color='green')
            bookmarks.append(cur_frame)
            bookmarks.sort()

        elif event == 'Prev':
            prev, _ = inbetween(bookmarks, cur_frame)
            if prev is not None:
                videoFile.set(cv.CAP_PROP_POS_FRAMES, prev)
                values['-slider-'] = prev
                trigger_pause = True

        elif event == 'Next':
            _, next = inbetween(bookmarks, cur_frame)
            if next is not None:
                videoFile.set(cv.CAP_PROP_POS_FRAMES, next)
                values['-slider-'] = next
                trigger_pause = True

        elif event == 'Pause':
            pause = not pause
            if pause:
                pause_button.Update(text='>')
                if canthread is not None:
                    canthread.stop()
                    canthread = None
                    messageT0 = None
            else:
                pause_button.Update(text='||')
                canthread = CanSender(canlogfilename, frame2time(cur_frame, syncpoints, fps),
                                      config['canbus']['channel'],
                                      config['canbus']['interface'])
                canthread.start()

        elif event == 'Sync':
            input_text = sg.InputText(key='-IN-')
            layout2 = [[sg.Text('UTC time (ex. 2019-12-11 11:22:33)')], [input_text],
                       [sg.Ok(), sg.Cancel()]]
            window2 = sg.Window('Time synchronize window.', layout2)
            while True:
                event2, values2 = window2.read()
                if event2 == 'Ok':
                    try:
                        sp = values2['-IN-']
                        epoch_time: float = (
                                datetime.strptime(sp, '%Y-%m-%d %H:%M:%S') - datetime(1970, 1, 1)).total_seconds()
                        syncpoints[cur_frame] = epoch_time
                        break
                    except:
                        sg.Popup('Error, can not convert to timestamp:', values2['-IN-'])
                        input_text.update('')
                else:
                    break
            window2.close()

        ret, frame = videoFile.read()
        ##Audio: audio_frame, val = player.get_frame()
        if not ret:  # if out of data stop looping
            break
        # if someone moved the slider manually, the jump to that frame
        if int(values['-slider-']) != cur_frame - 1:
            cur_frame = int(values['-slider-'])
            videoFile.set(cv.CAP_PROP_POS_FRAMES, cur_frame)
            ##Audio: player.seek(cur_frame/fps,relative=False)
        slider.update(cur_frame)

        if not pause:
            cur_frame += 1
            height, width, layers = frame.shape
            new_h = int(height / aspectratio)
            new_w = int(width / aspectratio)
            frame = cv.resize(frame, (new_w, new_h))
            cv.imshow('frame', frame)

        if trigger_pause:
            pause = True
            trigger_pause = False
            pause_button.Update(text='>')

        ## todo -- simplify the 2 lines below!!
        delay = int(1000 / fps) - int((time.time() - t1) * 1000)
        wait = max(delay - int(frame_extradiff(cur_frame, fps, pause) * 1000), 1)
        cv.waitKey(wait)

        if canthread is not None:
            message = canthread.getMessage()
            if message is not None:
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(message.timestamp)))

    config['video']['bookmarks'] = bookmarks
    config['video']['syncpoints'] = syncpoints
    with open(results.config, 'w') as outfile:
        json.dump(config, outfile, indent=3, sort_keys=True)


main()
