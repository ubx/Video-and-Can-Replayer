import threading
from datetime import datetime
from time import sleep

from can import MessageSync
from player2 import LogReader2


class CallbackList(list):
    def fire(self, *args, **kwargs):
        for listener in self:
            listener(*args, **kwargs)


class CanlogReader(threading.Thread):
    def __init__(self, infile, start_time, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.infile = infile
        self.start_time = start_time
        self.reader = None
        self.running = False
        self.callback_list = CallbackList()

    # function using _stop function
    def stop(self):
        self.running = False
        if self.reader:
            self.callback_list.clear()
            self.reader.stop()
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        if not self.reader:
            self.reader = LogReader2(self.infile, self.start_time)
        in_sync = MessageSync(self.reader, timestamps=True)
        sleep(0.5)
        print('Can LogReader (Started on {})'.format(datetime.now()))
        self.running = True
        try:
            for message in in_sync:
                if not self.running:
                    break
                if message.is_error_frame:
                    continue
                self.callback_list.fire(message)
        except KeyboardInterrupt:
            pass
        finally:
            self.reader.stop()

    def addCallback(self, calback):
        self.callback_list.append(calback)


if __name__ == '__main__':
    def print_msg(msg):
        print('msg', msg)

    def print_msg_ts(msg):
        print('msg_ts', msg.timestamp)

    reader = CanlogReader('data/candump-2019-09-21_110938-gps.db', 1569062280.0)
    reader.addCallback(print_msg)
    reader.addCallback(print_msg_ts)
    reader.start()
