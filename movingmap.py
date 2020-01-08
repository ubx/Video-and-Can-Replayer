import sys

from kivy.app import App
from kivy.graphics.svg import Svg
from kivy.uix.scatter import Scatter
from kivy.core.window import Window

from canreader import CanlogPos, CanbusPos
from mapview import MapView


class SvgWidget(Scatter):

    def __init__(self, filename, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            svg = Svg(filename)
        self.size = svg.width, svg.height

class MapViewApp(App):
    mapview = None
    marker = None
    symbol = None

    def __init__(self, pos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos = pos

    def build(self):
        self.lat = 47.0
        self.lon = 7.0
        self.mapview = MapView(zoom=8, lat=self.lat, lon=self.lon)
        from kivy.clock import Clock
        Clock.schedule_interval(self.clock_callback, 0.5)
        return self.mapview

    def clock_callback(self, dt):
        lat2, lon2 = self.pos.getLocation()
        if lat2 is not None and lon2 is not None:
            self.lat = lat2
            self.lon = lon2
        self.mapview.center_on(self.lat, self.lon)

        if not self.symbol:
            self.symbol = SvgWidget('mapview/icons/glider_symbol.svg')
            self.mapview.add_widget(self.symbol)
        self.symbol.center = Window.center
        th = self.pos.getTh()
        if th:
            self.symbol._set_rotation(th * -1.0)
        else:
            th = 0.0
        ##print('App', self.lat, self.lon, '{:01}'.format(int(round(th, 0))))


if __name__ == '__main__':
    ## todo -- use argparse
    if len(sys.argv) == 3 and sys.argv[1] == 'file':
        pos = CanlogPos(sys.argv[2])
    else:
        pos = CanbusPos(channel='vcan0', bustype='socketcan')
    pos.start()
    MapViewApp(pos).run()
