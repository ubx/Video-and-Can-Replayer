import struct
import threading
from datetime import datetime

import can
from can import MessageSync

from player2 import LogReader2


def getDoubleL(data):
    return struct.unpack('>l', data[4:8])[0] / 1E7


def getFloat(data):
    return struct.unpack('>f', data[4:8])[0]


class CanlogPos(threading.Thread):
    def __init__(self, infile, start_time=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.infile = infile
        self.start_time = start_time
        self.reader = None
        self.running = False
        self.lat = None
        self.lon = None
        self.th = None

    # function using _stop function
    def stop(self):
        self.running = False
        self.reader.stop()
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        self.reader = LogReader2(self.infile, self.start_time)
        in_sync = MessageSync(self.reader, timestamps=True)
        print('Can LogReader (Started on {})'.format(datetime.now()))
        self.running = True
        try:
            for message in in_sync:
                if not self.running:
                    break
                if message.is_error_frame:
                    continue
                if message.arbitration_id == 1036:
                    self.lat = getDoubleL(message.data)
                elif message.arbitration_id == 1037:
                    self.lon = getDoubleL(message.data)
                elif message.arbitration_id == 321:
                    th = getFloat(message.data)
                    if th < 0.0:
                        self.th = th + 360.0
                    else:
                        self.th = th

        except KeyboardInterrupt:
            pass
        finally:
            self.reader.stop()

    def getLocation(self):
        return self.lat, self.lon

    def getTh(self):
        return self.th


class CanbusPos(threading.Thread):
    def __init__(self, channel, bustype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.bus = can.interface.Bus(channel=channel, bustype=bustype)
        self.lat = None
        self.lon = None
        self.th = None

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        for message in self.bus:
            if message.arbitration_id == 1036:
                self.lat = getDoubleL(message.data)
            elif message.arbitration_id == 1037:
                self.lon = getDoubleL(message.data)
            elif message.arbitration_id == 321:
                th = getFloat(message.data)
                if th < 0.0:
                    self.th = th + 360.0
                else:
                    self.th = th

    def getLocation(self):
        return self.lat, self.lon

    def getTh(self):
        return self.th
