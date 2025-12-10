import time

from kivy.uix.videoplayer import VideoPlayerAnnotation

from videoPlayer2 import VideoPlayer2

from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics import Color, Line
from kivy.graphics.svg import Svg
from kivy.properties import NumericProperty, StringProperty
from kivy.resources import resource_find
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget

from canreader import CanbusPos

Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '800')


def create_annotation(start, text):
    return {'start': start, 'duration': 20, 'text': text, 'bgcolor': [0.37, 1.00, 0.0, 0.7]}


##Config.write()

class SyncpointDialog(ModalView):
    def __init__(self, videoplayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.videoplayer: VideoPlayer2 = videoplayer
        self.ts = None

    def checkTime(self, sp):
        try:
            self.ts = (datetime.strptime(sp, '%Y-%m-%d %H:%M:%S') - datetime(1970, 1, 1)).total_seconds()
            return self.ts
        except:
            return None

    def set_syncpoint(self):
        self.videoplayer.syncpoints[int(round(self.videoplayer.cur_position))] = self.ts


class BookmarkDialog(ModalView):
    def __init__(self, videoplayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.videoplayer: VideoPlayer2 = videoplayer
        self.description = None

    def set_bookmark(self):
        cur_position = int(self.videoplayer.cur_position)
        self.videoplayer.mainwindow.draw_bookmark(cur_position)
        self.videoplayer.bookmarks.append([int(cur_position), self.description])
        self.videoplayer.bookmarks.sort(key=lambda x: x[0])
        self.videoplayer.mainwindow.ids.video_player.add_annotation(
            create_annotation(start=cur_position - 10, text=self.description))


class MainWindow(BoxLayout):

    def draw_bookmark(self, position):
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
            self.draw_bookmark(bm[0])


from kivy_garden.mapview import MapMarker


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
    # Absolute path to a safe thumbnail image, resolved via Kivy resources
    thumbnail_path = StringProperty('')

    def __init__(self, file, syncpoints, bookmarks, decription, cansender=None, position_srv=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file = file
        self.syncpoints = syncpoints
        self.bookmarks = bookmarks
        self.description = decription
        self.cansender = cansender
        self.cur_position = 0
        self.cur_duration = None
        self.position_srv = position_srv
        # Resolve a valid thumbnail immediately so KV can bind to it
        # Prefer Kivy's built-in icon as it is guaranteed to exist with Kivy installations
        thumb = resource_find('data/logo/kivy-icon-128.png') or resource_find('data/logo/kivy-icon-512.png')
        if thumb:
            self.thumbnail_path = thumb

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
        # Avoid Kivy Image trying to load the MP4 when the VideoPlayer is in 'stop' state
        # by providing a valid thumbnail image (KV sets it via app.thumbnail_path).
        # As an extra safety, set directly if KV binding didn't apply for any reason.
        try:
            vp = self.mainwindow.ids.get('video_player')
            if vp is not None and self.thumbnail_path and getattr(vp, 'thumbnail', None) != self.thumbnail_path:
                vp.thumbnail = self.thumbnail_path
            # Defer setting the video source until after the widget is fully built,
            # ensuring the thumbnail is already applied and preventing Image from
            # attempting to load the MP4.
            if vp is not None:
                def _apply_source(dt):
                    try:
                        # Switch to play before assigning source so VideoPlayer doesn't
                        # try to render the stop-state preview Image from the MP4 path.
                        vp.state = 'play'
                        vp.source = self.get_file(vp)
                        # Immediately pause so the app starts in a paused state for the user.
                        Clock.schedule_once(lambda _dt: setattr(vp, 'state', 'pause'), 0)
                    except Exception:
                        pass

                Clock.schedule_once(_apply_source, 0)
        except Exception:
            pass
        return self.mainwindow

    def get_file(self, videoplayer):
        ann = {'start': 0, 'duration': 20, 'text': self.description}
        videoplayer.add_annotation(ann)
        for bm in self.bookmarks:
            videoplayer.add_annotation(create_annotation(start=bm[0] - 10, text=bm[1]))
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
        prev, _ = self.inbetween_bm(self.bookmarks, self.cur_position)
        if prev:
            videoplayer.seek((prev / videoplayer.duration) - 0.001)
        videoplayer.state = 'pause'

    def btn_next(self, videoplayer):
        _, next = self.inbetween_bm(self.bookmarks, self.cur_position)
        if next:
            videoplayer.seek((next / videoplayer.duration) + 0.001)
        videoplayer.state = 'pause'

    def btn_move(self, videoplayer, delta):
        videoplayer.seek((self.cur_position + delta) / videoplayer.duration)
        videoplayer.state = 'pause'

    def btn_bookmark(self, videoplayer):
        if videoplayer.duration > 10.0:  # todo -- workorund ?
            videoplayer.state = 'pause'
            dialog = BookmarkDialog(self)
            dialog.open()

    def btn_syncpoint(self, videoplayer):
        videoplayer.state = 'pause'
        dialog = SyncpointDialog(self)
        dialog.open()

    def on_width(self):
        self.root.draw_all_bookmarks(self.bookmarks)

    def video_position2time(self, vpos, syncpoints):
        p, n = self.inbetween_sp(list(syncpoints.keys()), vpos)
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

    ## todo -- avoid duplicated code !!
    def inbetween_sp(self, syncpoints, val):
        val = int(round(val))
        prev, next = None, None
        if syncpoints:
            if val < syncpoints[0]: next = syncpoints[0]
            if val > syncpoints[-1]: prev = syncpoints[-1]
            if len(syncpoints) > 1:
                for i in range(0, len(syncpoints) - 1):
                    if val in range(syncpoints[i], syncpoints[i + 1]):
                        prev = syncpoints[i]
                        next = syncpoints[i + 1]
                        break
        return prev if prev is None else float(prev), next if next is None else float(next)

    def inbetween_bm(self, bookmarks, val):
        val = int(round(val))
        prev, next = None, None
        if bookmarks:
            if val < bookmarks[0][0]: next = bookmarks[0][0]
            if val > bookmarks[-1][0]: prev = bookmarks[-1][0]
            if len(bookmarks) > 1:
                for i in range(0, len(bookmarks) - 1):
                    if val in range(bookmarks[i][0], bookmarks[i + 1][0]):
                        prev = bookmarks[i][0]
                        next = bookmarks[i + 1][0]
                        break
        return prev if prev is None else float(prev), next if next is None else float(next)


if __name__ == '__main__':
    position_srv = CanbusPos(channel='internal', bustype='virtual')
    position_srv.start()
    VideoplayerApp(position_srv).run()
