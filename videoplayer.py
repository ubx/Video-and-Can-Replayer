from kivy.app import App
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.videoplayer import VideoPlayer
from datetime import datetime


class ModalDialog(ModalView):
    def __init__(self, videoplayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.videoplayer: VideoPlayer = videoplayer
        self.ts = None

    def checkTime(self, sp):
        try:
            self.ts = (datetime.strptime(sp, '%Y-%m-%d %H:%M:%S') - datetime(1970, 1, 1)).total_seconds()
            return self.ts
        except:
            return None

    def set_syncpoint(self):
        print('ts', self.ts, 'cur_position', self.videoplayer.cur_position)
        self.videoplayer.bookmarks.append(int(self.ts))
        self.videoplayer.bookmarks.sort()
        self.videoplayer.syncpoints[f'{int(round(self.videoplayer.cur_position))}'] = self.ts


class MainWindow(BoxLayout):

    def draw_bookmarks(self, position):
        base = 10
        max = self.width - 20
        lpos = 10 + ((max - base) * (position / self.ids.video_player.duration))
        with self.ids.bookmarks.canvas:
            Color(0, 1, 0)
            Line(points=(lpos, 40, lpos, 60), width=1.2, )

    def draw_all_bookmarks(self, bookmarks):
        for bm in bookmarks:
            self.draw_bookmarks(bm)


class VideoplayerApp(App):
    def __init__(self, file, syncpoints, bookmarks, cansender=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file = file
        self.syncpoints = syncpoints
        self.bookmarks = bookmarks
        self.cansender = cansender
        self.cur_position = 0
        self.cur_duration = None

    def build(self):
        return MainWindow()

    def get_file(self):
        return self.file

    def on_state(self, *args):
        videoplayer: VideoPlayer = args[1]
        if self.cur_duration is None and videoplayer.duration > 100.0:
            self.cur_duration = videoplayer.duration
            self.root.draw_all_bookmarks(self.bookmarks)
        if args[0] == 'play':
            self.cansender.resume(self.video_position2time(self.cur_position, self.syncpoints))
        elif args[0] == 'pause':
            self.cansender.stop()

    def on_position(self, pos):
        self.cur_position = pos

    def realtime(self, *args):
        return '{:6.2f}'.format(args[0])

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
        vp = self.cur_position + 5.0  # todo -- ???
        _, next = self.inbetween(self.bookmarks, vp)
        print('vp', vp, 'next', next)
        if next:
            videoplayer.seek(next / videoplayer.duration)

    def btn_bookmark(self, *args):
        if args[0].duration > 100.0:  # todo -- ????
            self.root.draw_bookmarks(self.cur_position)
            self.bookmarks.append(int(self.cur_position))
            self.bookmarks.sort()

    def btn_syncpoint(self, *args):
        videoplayer: VideoPlayer = args[0]
        videoplayer.state = 'pause'
        dialog = ModalDialog(self)
        dialog.open()

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

    def on_start(self):
        pass


if __name__ == '__main__':
    VideoplayerApp().run()
