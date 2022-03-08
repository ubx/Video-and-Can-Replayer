import threading
from threading import Thread
from time import sleep

from can import Bus, MessageSync

from player2 import LogReader2


class CanSender(Thread):
    def __init__(self, infile, channel, interface, start_time=0.0, with_internal_bus=False, filter_out=[], *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.infile = infile
        self.start_time = start_time
        self.filter_out = filter_out
        try:
            self.config = {'single_handle': True}
            self.config['interface'] = interface
            self.bus = Bus(channel, **self.config)
        except:
            self.bus = None
            print('WARNING Can channel', channel, 'not connected')
        if with_internal_bus:
            self.bus_internal = Bus(channel='internal', bustype='virtual')
        self.runevent = threading.Event()
        self.runevent.clear()
        self.killevent = threading.Event()
        self.killevent.set()
        self.doneevent = threading.Event()
        self.reader = None

    def run(self):
        while True:
            self.killevent.wait()
            self.runevent.wait()
            self.reader = LogReader2(self.infile, self.start_time)
            self.in_sync = MessageSync(self.reader, timestamps=True)
            try:
                for message in self.in_sync:
                    if message.arbitration_id in self.filter_out:
                        print('Filter out can id {:d}'.format(message.arbitration_id))
                    else:
                        if self.bus:
                            self.bus.send(message, timeout=0.1)
                        if self.bus_internal:
                            self.bus_internal.send(message)
                        if not self.runevent.isSet():
                            break
            except:
                print("CAN send error")
            finally:
                pass

            if self.reader:
                self.stop_reader()
            self.runevent.clear()
            self.doneevent.set()
            if not self.killevent.isSet():
                break

    def stop_reader(self):
        try:
            self.reader.stop()
            sleep(0.2)
        finally:
            self.reader = None

    def resume(self, start_time):
        self.start_time = start_time
        self.runevent.set()

    def stop(self):
         if self.runevent.isSet():
            self.runevent.clear()
            self.doneevent.clear()
            self.doneevent.wait()

    def exit(self):
        self.runevent.clear()
        sleep(1)
        if self.reader:
            self.stop_reader()
        self.killevent.clear()
        if self.bus:
            self.bus.shutdown()
        if self.bus_internal:
            self.bus_internal.shutdown()


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
