import time
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics import Color, Line
from kivy.graphics.svg import Svg
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scatter import Scatter
from kivy.uix.videoplayer import VideoPlayer
from kivy.uix.widget import Widget

from canreader import CanbusPos

Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '800')


##Config.write()

class SyncpointDialog(ModalView):
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
        self.videoplayer.syncpoints[int(round(self.videoplayer.cur_position))] = self.ts


class MainWindow(BoxLayout):

    def draw_bookmarks(self, position):
        base = 0
        max = self.width - 0
        lpos = base + ((max - base) * (position / self.ids.video_player.duration))
        with self.ids.bookmarks.canvas:
            Color(0, 1, 0)
            Line(points=(lpos, 60, lpos, 74), width=1.2, )

    def draw_all_bookmarks(self, bookmarks):
        self.ids.bookmarks.canvas.clear()
        with self.ids.bookmarks.canvas:
            Color(1, 1, 1)
        for bm in bookmarks:
            self.draw_bookmarks(bm)

from kivy.garden.mapview import MapMarker

class Glider(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            svg = Svg('mapview/icons/glider_symbol.svg')
        self.size = svg.width, svg.height


class MapWidget(Scatter):
    pass


class VideoplayerApp(App):
    heading_angle = NumericProperty(0)
    utc_str = StringProperty('--:--:--')

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
        self.icon = 'app.ico'
        self.mainwindow = MainWindow()

        if self.position_srv:
            self.lat = 47.0
            self.lon = 7.0
            self.th = 0.0

            def clock_callback(dt):
                utc = self.position_srv.getUtc()
                if utc:
                    self.utc_str = time.strftime('%H:%M:%S', time.localtime(utc))
                lat2, lon2 = self.position_srv.getLocation()
                if lat2 is not None and lon2 is not None:
                    self.lat = lat2
                    self.lon = lon2
                self.mainwindow.ids.mapview.center_on(self.lat, self.lon)
                th = self.position_srv.getTh()
                if th:
                    self.heading_angle = (th * -1.0)

            Clock.schedule_interval(clock_callback, 0.25)
        else:
            self.mainwindow.ids.mapwidget.clear_widgets()
        return self.mainwindow

    def get_file(self):
        return self.file

    def on_state(self, instance, value):
        if value == 'play':
            self.cansender.resume(self.video_position2time(self.cur_position, self.syncpoints))
        elif value == 'pause':
            self.cansender.stop()

    def on_position(self, position, videoplayer):
        if self.cur_duration is None and videoplayer.duration > 1.0:
            self.cur_duration = videoplayer.duration
            self.root.draw_all_bookmarks(self.bookmarks)
        if videoplayer.state == 'play' and abs(self.cur_position - position) > 2.0:
            self.cansender.stop()
            self.cansender.resume(self.video_position2time(self.cur_position, self.syncpoints))
        self.cur_position = position

    def realtime(self, cur_position):
        seconds = self.video_position2time(cur_position, self.syncpoints)
        return time.strftime('%H:%M:%S', time.localtime(seconds))

    def btn_previous(self, videoplayer):
        prev, _ = self.inbetween(self.bookmarks, self.cur_position - 5.0)
        if prev:
            videoplayer.seek(prev / videoplayer.duration)
        videoplayer.state = 'pause'

    def btn_next(self, videoplayer):
        _, next = self.inbetween(self.bookmarks, self.cur_position + 5.0)
        if next:
            videoplayer.seek(next / videoplayer.duration)
        videoplayer.state = 'pause'

    def btn_move(self, videoplayer, delta):
        videoplayer.seek((self.cur_position + delta) / videoplayer.duration)
        videoplayer.state = 'pause'

    def btn_bookmark(self, videoplayer):
        if videoplayer.duration > 10.0:  # todo -- workorund ?
            self.root.draw_bookmarks(self.cur_position)
            self.bookmarks.append(int(self.cur_position))
            self.bookmarks.sort()

    def on_width(self):
        self.root.draw_all_bookmarks(self.bookmarks)

    def btn_syncpoint(self, videoplayer):
        videoplayer.state = 'pause'
        dialog = SyncpointDialog(self)
        dialog.open()

    def video_position2time(self, vpos, syncpoints):
        p, n = self.inbetween(list(syncpoints.keys()), vpos)
        if p and n:
            c = (syncpoints[n] - syncpoints[p]) / (n - p)
            # todo -- optimize this,
            #   see: http://python.omics.wiki/data-structures/dictionary/multiple-keys
            #        https://stackoverflow.com/questions/39358092/range-as-dictionary-key-in-python
            p1 = p
        elif p:
            c = 1.0
            p1 = p
        else:
            c = 1.0
            p1 = next(iter(syncpoints))
        t1 = syncpoints[p1]
        ##print(p1, t1, c)
        utc_offset = datetime.fromtimestamp(t1) - datetime.utcfromtimestamp(t1)
        return (t1 - ((p1 - vpos) * c)) - utc_offset.seconds

    def inbetween(self, list, val):
        val = int(round(val))
        prev, next = None, None
        if list:
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
