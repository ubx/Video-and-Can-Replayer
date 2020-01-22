from datetime import datetime

import time

from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
from kivy.graphics.svg import Svg
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scatter import Scatter
from kivy.uix.videoplayer import VideoPlayer
from kivy.clock import Clock

from canreader import CanbusPos
from mapview import MapView


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
        base = 20
        max = self.width - 40
        lpos = base + ((max - base) * (position / self.ids.video_player.duration))
        with self.ids.bookmarks.canvas:
            Color(0, 1, 0)
            Line(points=(lpos, 60, lpos, 70), width=1.2, )

    def draw_all_bookmarks(self, bookmarks):
        with self.ids.bookmarks.canvas:
            Color(1, 1, 1)
            Rectangle(pos=(20, 50), size=(self.width - 40, 10))
        for bm in bookmarks:
            self.draw_bookmarks(bm)


class SymbolWidget(Scatter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Svg('mapview/icons/glider_symbol.svg')


class MapWidget(Scatter):
    pass


class VideoplayerApp(App):
    def __init__(self, file, syncpoints, bookmarks, cansender=None, position_srv=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file = file
        self.syncpoints = syncpoints
        self.bookmarks = bookmarks
        self.cansender = cansender
        self.cur_position = 0
        self.cur_duration = None
        self.position_srv = position_srv

    def build(self):
        self.mainwindow = MainWindow()

        if self.position_srv:
            self.lat = 47.0
            self.lon = 7.0
            self.th = 0.0
            self.mapview = MapView(zoom=8, lat=self.lat, lon=self.lon)
            # self.symbol = SymbolWidget()
            # self.symbol.center = Window.center
            self.map = MapWidget()
            self.map.add_widget(self.mapview)
            self.mainwindow.ids.map.add_widget(self.map)

            # self.map.add_widget(self.mainwindow.ids.symbol)

            def clock_callback(dt):
                lat2, lon2 = self.position_srv.getLocation()
                if lat2 is not None and lon2 is not None:
                    self.lat = lat2
                    self.lon = lon2
                self.mapview.center_on(self.lat, self.lon)
                ids = self.mainwindow.ids
                cent = self.mainwindow.center
                ##ids.symbol._set_center(cent)

                th = self.position_srv.getTh()
                if th:
                    ids.symbol._set_rotation(th * -1.0)

            Clock.schedule_interval(clock_callback, 0.24)

        return self.mainwindow

    def get_file(self):
        return self.file

    def on_state(self, state):
        if state == 'play':
            self.cansender.resume(self.video_position2time(self.cur_position, self.syncpoints))
        elif state == 'pause':
            self.cansender.stop()

    def on_position(self, position, videoplayer):
        if self.cur_duration is None and videoplayer.duration > 1.0:
            self.cur_duration = videoplayer.duration
            self.root.draw_all_bookmarks(self.bookmarks)
        self.cur_position = position

    def realtime(self, cur_position):
        seconds = self.video_position2time(cur_position, self.syncpoints)
        return time.strftime('%H:%M:%S', time.localtime(seconds))

    def btn_previous(self, videoplayer):
        videoplayer.state = 'pause'
        vp = self.cur_position
        prev, _ = self.inbetween(self.bookmarks, vp)
        ##print('vp', vp, 'prev', prev)
        if prev:
            videoplayer.seek(prev / videoplayer.duration)

    def btn_next(self, videoplayer):
        videoplayer.state = 'pause'
        vp = self.cur_position + 5.0  # todo -- ???
        _, next = self.inbetween(self.bookmarks, vp)
        ##print('vp', vp, 'next', next)
        if next:
            videoplayer.seek(next / videoplayer.duration)

    def btn_bookmark(self, videoplayer):
        if videoplayer.duration > 100.0:  # todo -- workorund ?
            self.root.draw_bookmarks(self.cur_position)
            self.bookmarks.append(int(self.cur_position))
            self.bookmarks.sort()

    def on_width(self):
        self.root.draw_all_bookmarks(self.bookmarks)

    def btn_syncpoint(self, videoplayer):
        videoplayer.state = 'pause'
        dialog = ModalDialog(self)
        dialog.open()

    def video_position2time(self, vpos, syncpoints):
        fsp = next(iter(syncpoints))  # take first syncpoint !
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
    position_srv = CanbusPos(channel='internal', bustype='virtual')
    position_srv.start()
    VideoplayerApp(position_srv).run()
