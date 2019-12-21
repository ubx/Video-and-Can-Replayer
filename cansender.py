import threading
from datetime import datetime

from can import MessageSync, Bus

from player2 import LogReader2


class CanSender(threading.Thread):
    def __init__(self, infile, start_time, channel, interface, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.infile = infile
        self.start_time = start_time
        self.reader = None
        self.running = False
        self.config = {'single_handle': True}
        self.config['interface'] = interface
        self.bus = Bus(channel, **self.config)
        self.message = None

# function using _stop function
    def stop(self):
        self.running = False
        self.reader.stop()
        self.bus.shutdown()
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
                self.bus.send(message)
                self.message = message
        except KeyboardInterrupt:
            pass
        finally:
            self.bus.shutdown()
            self.reader.stop()

    def getMessage(self):
        return self.message
