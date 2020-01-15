import threading
from time import sleep

from can import Bus, MessageSync

from player2 import LogReader2


class CanSender(threading.Thread):
    def __init__(self, infile, channel, interface, *args, start_time=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.infile = infile
        self.start_time = start_time
        self.config = {'single_handle': True}
        self.config['interface'] = interface
        self.bus = Bus(channel, **self.config)
        self.runevent = threading.Event()
        self.runevent.clear()
        self.killevent = threading.Event()
        self.killevent.set()
        self.reader = None

    def run(self):
        while True:
            self.killevent.wait()
            self.runevent.wait()
            self.reader = LogReader2(self.infile, self.start_time)
            self.in_sync = MessageSync(self.reader, timestamps=True)
            try:
                for message in self.in_sync:
                    self.bus.send(message)
                    if not self.runevent.isSet():
                        break
            finally:
                pass

            if self.reader:
                self.stop_reader()
            self.runevent.clear()
            if not self.killevent.isSet():
                break

    def stop_reader(self):
        try:
            self.reader.stop()
            sleep(0.2)
            self.reader.__exit__()
        finally:
            self.reader = None

    def resume(self, start_time):
        self.start_time = start_time
        self.runevent.set()

    def stop(self):
        self.runevent.clear()

    def exit(self):
        self.runevent.clear()
        if self.reader:
            self.stop_reader()
        self.killevent.clear()
        threading.Thread.join(self)


if __name__ == '__main__':
    print('INIT')
    cansender = CanSender('data/candump-2019-09-21_110938-gps.db', 1569062280.0, 'vcan0', 'socketcan')
    cansender.start()
    sleep(5)

    print('RESUME')
    cansender.resume(start_time=1569074766.0)
    sleep(10)

    print('STOP')
    cansender.stop()
    sleep(5)

    print('RESUME1')
    cansender.resume(start_time=1569048715.0)
    sleep(5)

    print('STOP1')
    cansender.stop()
    sleep(5)

    print('RESUME2')
    cansender.resume(start_time=1569062280.0)
    sleep(5)

    print('JOIN')
    cansender.join()

    print('xxxxxxxxxxxxxxxxxxxx')
