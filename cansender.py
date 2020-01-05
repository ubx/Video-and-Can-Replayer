import threading
from datetime import datetime

from can import MessageSync, Bus

from player2 import LogReader2


class CanSender(threading.Thread):
    def __init__(self, infile, start_time, channel, interface, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.reader = LogReader2(infile, start_time)
        self.config = {'single_handle': True}
        self.config['interface'] = interface
        self.bus = Bus(channel, **self.config)
        self.running = False

    # function using _stop function
    def stop(self):
        self.running = False
        self._stop.set()
        self.reader.__exit__()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        in_sync = MessageSync(self.reader, timestamps=True)
        print('Can LogReader (Started on {})'.format(datetime.now()))
        self.running = True
        try:
            for message in in_sync:
                if not self.running:
                    break
                if message.is_error_frame:
                    continue
                self.bus.send(message)
        except KeyboardInterrupt:
            pass
        finally:
            self.reader.stop()
            self.reader.__exit__()
            self.stop()
