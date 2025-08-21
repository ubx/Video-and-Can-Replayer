import datetime
import struct
import threading
import can
from can import MessageSync

from player2 import LogReader2


def getDoubleL(data):
    return struct.unpack('>l', data[4:8])[0] / 1E7


def getFloat(data):
    return struct.unpack('>f', data[4:8])[0]


def getInt(data: int):
    return struct.unpack('>i', data[4:8])[0]

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
                elif message.arbitration_id == 340:  # flap pos
                    fp = getInt(message.data)
                    print('fp = {}'.format(fp))


        except KeyboardInterrupt:
            pass
        finally:
            self.reader.stop()

    def getLocation(self):
        return self.lat, self.lon

    def getTh(self):
        return self.th


def toDeg(val):
    return val + 360.0 if val < 0.0 else val


class CanbusPos(threading.Thread):
    def __init__(self, channel, bustype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bus = can.interface.Bus(channel=channel, bustype=bustype)
        self.utc = None
        self.lat = None
        self.lon = None
        self.th = None
        self.wind_direction = None

    def run(self):
        try:
            for message in self.bus:
                if message.arbitration_id == 1200:  # UTC time
                    if self.utc_date_data:
                        ud = struct.unpack('4b', self.utc_date_data[4:])
                        ut = struct.unpack('4b', message.data[4:])
                        self.utc = datetime.datetime((ud[2] * 100) + ud[3], ud[1], ud[0], ut[0], ut[1], ut[2],
                                                     ut[3]).timestamp()
                elif message.arbitration_id == 1206:  # UTC date
                    self.utc_date_data = message.data
                elif message.arbitration_id == 1036:
                    self.lat = getDoubleL(message.data)
                elif message.arbitration_id == 1037:
                    self.lon = getDoubleL(message.data)
                elif message.arbitration_id == 321:
                    self.th = toDeg(getFloat(message.data))
                elif message.arbitration_id == 1040:
                    self.tt = getFloat(message.data)
                elif message.arbitration_id == 334:
                    self.wind_direction = toDeg(getFloat(message.data))
                    # if self.tt and self.th and self.wind_direction:
                    #     print('TT={:3.1f} TH={:3.1f} Diff={:3.1f} Wind_dir={:3.1f}'.format(self.tt, self.th,
                    #                                                                        self.tt - self.th,
                    #                                                                        self.wind_direction))
        except Exception as e:
            print(e)

    def exit(self):
        self.bus.shutdown()

    def getLocation(self):
        return self.lat, self.lon

    def getTh(self):
        return self.th

    def getUtc(self):
        return self.utc
