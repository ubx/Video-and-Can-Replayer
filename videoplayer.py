from kivy.app import App
from kivy.uix.videoplayer import VideoPlayer
from datetime import datetime


class VideoplayerApp(App):
    def __init__(self, file, syncpoints, bookmarks, cansender=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file = file
        self.syncpoints = syncpoints
        self.bookmarks = bookmarks
        self.cansender = cansender
        self.cur_position = 0

    def get_file(self):
        return self.file

    def replay(self, *args):
        print('replay, state=', args[0], 'position', args[1])
        if args[0] == 'play':
            self.cansender.resume(self.video_position2time(self.cur_position, self.syncpoints))
        elif args[0] == 'pause':
            self.cansender.stop()

    def on_position(self, pos):
        self.cur_position = pos

    def realtime(self, *args):
        return '{:6.2f}'.format(args[0] + 100)

    def btn_previous(self, *args):
        videoplayer: VideoPlayer = args[0]
        videoplayer.state = 'pause'
        vp = self.cur_position
        prev, _ = self.inbetween(self.bookmarks, vp)
        print('vp', vp, 'prev', prev)
        if prev:
            videoplayer.seek(prev / videoplayer.duration)

    def btn_next(self, *args):
        videoplayer: VideoPlayer = args[0]
        videoplayer.state = 'pause'
        vp = self.cur_position + 5.0 # todo -- ???
        _, next = self.inbetween(self.bookmarks, vp)
        print('vp', vp, 'next', next)
        if next:
            videoplayer.seek(next / videoplayer.duration)

    def video_position2time(self, vpos, syncpoints):
        fsp = next(iter(syncpoints))  # first syncpoint !
        t1 = syncpoints[fsp]
        utc_offset = datetime.fromtimestamp(t1) - datetime.utcfromtimestamp(t1)
        return (t1 - (int(fsp) - vpos)) - utc_offset.seconds

    def inbetween(self, list, val):
        val = int(round(val))
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
        return prev if prev is None else float(prev), next if next is None else float(next)


if __name__ == '__main__':
    VideoplayerApp().run()
