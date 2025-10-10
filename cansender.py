import threading
from threading import Thread
from time import sleep
import logging

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
        self.bus_internal = None
        try:
            self.config = {'single_handle': True}
            self.config['interface'] = interface
            self.bus = Bus(channel, **self.config)
        except Exception as e:
            self.bus = None
            logging.warning('CAN channel %s not connected: %s', channel, e)
        if with_internal_bus:
            try:
                self.bus_internal = Bus(channel='internal', bustype='virtual')
            except Exception as e:
                self.bus_internal = None
                logging.warning('Internal CAN bus not available: %s', e)
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
                        logging.info('Filter out CAN id %d', message.arbitration_id)
                    else:
                        if self.bus:
                            self.bus.send(message, timeout=0.1)
                        if self.bus_internal:
                            self.bus_internal.send(message)
                        if not self.runevent.is_set():
                            break
            except Exception:
                logging.exception("CAN send error")
            finally:
                pass

            if self.reader:
                self.stop_reader()
            self.runevent.clear()
            self.doneevent.set()
            if not self.killevent.is_set():
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
        if self.runevent.is_set():
            self.runevent.clear()
            self.doneevent.clear()
            self.doneevent.wait()

    def exit(self):
        # Request thread to terminate and unblock waits
        self.killevent.clear()
        self.runevent.set()
        sleep(0.1)
        if self.reader:
            self.stop_reader()
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception as e:
                logging.warning('Error during CAN bus shutdown: %s', e)
        if self.bus_internal:
            try:
                self.bus_internal.shutdown()
            except Exception as e:
                logging.warning('Error during internal CAN bus shutdown: %s', e)
        # Give the thread a moment to finish
        try:
            self.join(timeout=2.0)
        except RuntimeError:
            # join called from within the same thread; ignore
            pass


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
