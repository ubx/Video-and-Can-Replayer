import argparse
import datetime
import os
import struct
import can
from contextlib import contextmanager
from statistics import mean, variance, stdev

from canaerospace_ids import canaerospace_ids

'''
   Adjust timestamps of a CAN dump file according to GPS time (UTC).
      sudo ip link add dev vcan0 type vcan
      sudo ip link set up vcan0
'''




def statistics(ids, id_):
    ids[id_] = ids.get(id_, 0) + 1


@contextmanager
def read_bin_file(filename):
    # Binary Log Packet structure (fixed 21 bytes)
    # typedef struct __attribute__((packed))
    # {
    #     double timestamp;   // 8 bytes
    #     uint32_t id;        // 4 bytes
    #     uint8_t len;        // 1 byte
    #     uint8_t data[8];    // 8 bytes
    # } LogPacket;
    struct_format = '<dIB8B'
    f = open(filename, 'rb')
    try:
        def generator():
            while True:
                chunk = f.read(21)
                if not chunk or len(chunk) < 21:
                    break
                timestamp, can_id, length, *data = struct.unpack(struct_format, chunk)
                yield can.Message(timestamp=timestamp, arbitration_id=can_id, dlc=length, data=data[:length])

        yield generator()
    finally:
        f.close()


def close_logfile(ts_log):
    global new_log, new_log_file_name
    if ts_log is None:
        if new_log:
            new_log.close()
        return
    try:
        new_log.close()
        new_log_file_name = "data/candump-{}.log". \
            format(datetime.datetime.fromtimestamp(int(ts_log))).replace(" ", "_").replace(":", "")
        os.rename(new_log.name, new_log_file_name)
    except IOError:
        pass


def print_gps_diff_statistics():
    global mmm, new_log_file_name, new_cnt
    if not mmm:
        print(new_log_file_name, " cnt=", new_cnt, "no GPS diffs collected")
        return
    m = mean(mmm)
    var = variance(mmm) if len(mmm) > 1 else 0.0
    sd = stdev(mmm) if len(mmm) > 1 else 0.0
    print(new_log_file_name, " cnt=", new_cnt, "mean=", m, "variance=", var, "stdev=", sd,
          "max=", max(mmm), "min=", min(mmm))


def sync_with_gps(log_file_name: str, diff):
    log_file_name_gps = log_file_name.replace(".log", "-gps.log")
    with open(log_file_name_gps, "w") as lf_gps, open(log_file_name) as lf:
        for _, line in enumerate(lf):
            ts, channel, frame = line.strip().split()
            ts = float(ts[1:-1])
            lf_gps.write("({:f}) {} {}\n".format(ts - diff, channel, frame))


def get_canaerospace_data(msg):
    ts = msg.timestamp
    canId = msg.arbitration_id
    data = msg.data
    dataFullStr = "".join("{:02X}".format(b) for b in data)
    # nodeIdStr = dataFullStr[0:2]
    # dataStr = dataFullStr[8:]
    nodeIdStr = dataFullStr[0:2] if len(dataFullStr) >= 2 else ""
    dataStr = dataFullStr[8:] if len(dataFullStr) >= 8 else ""
    return ts, canId, dataFullStr, nodeIdStr, dataStr


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Correct time stamps according to the logger time sync (canId 0x1FFFFFF0) and optional GPS time (UTC). '
                    'Supports text logs and .BIN binary logs. Only useful for CANaerospace format!')
    parser.add_argument('-input', metavar='input', type=str, required=True,
                        help='Input logfile. For supported types see can.LogReader.')
    parser.add_argument('-gps', action='store_true', help='Sync with GPS time (canIDs 1200 and 1206.')
    parser.add_argument('-canid', action='store_true', help='Translate CAN identifiers according to CANaerospace spec.')

    args = parser.parse_args(argv)
    inputFile = args.input
    syncwithgps = args.gps
    translate_canid = args.canid

    # Globals used by helper functions close_logfile() and print_gps_diff_statistics()
    global new_log, new_log_file_name, mmm, new_cnt
    new_log = None
    new_log_file_name = None
    mmm = []
    new_cnt = 0

    if inputFile.upper().endswith(".BIN"):
        reader = read_bin_file(inputFile)
    else:
        reader = can.LogReader(inputFile)

    with reader as messages:
        canIds = {}
        nodeIds = {}
        dataUtcStr = None
        dataDateStr = None
        ts_log_last = None
        ts_log_first = None
        log_file_nr = 0
        diff = None
        ts_log_diff = None
        ts_first = None
        ts_prev = None
        ts_gps_first = None

        for cnt, msg in enumerate(messages):
            if new_log is None:
                log_file_nr = log_file_nr + 1
                new_log = open("data/newlog_{}.log".format(log_file_nr), "w+")

            ts, canId, dataFullStr, nodeIdStr, dataStr = get_canaerospace_data(msg)

            diff = 0.0
            if ts_first is None:
                ts_first = ts
            if ts_prev is None:
                ts_prev = ts
            else:
                if ts - ts_prev > 1.1:
                    print("ERROR, gap between ts {:f} and {:f}, {:.3f}s \n".format(ts_prev, ts, ts - ts_prev))
                ts_prev = ts

            if canId == 0x1FFFFFF0:  # Time sync
                # CANaerospace Time sync format: YY MM DD HH MM SS (Bytes 0-5)
                # dataFullStr corresponds to the whole data payload in hex.
                try:
                    ts_log = datetime.datetime((int(dataFullStr[0:2], 16) + 2000), int(dataFullStr[2:4], 16),
                                               int(dataFullStr[4:6], 16), int(dataFullStr[6:8], 16),
                                               int(dataFullStr[8:10], 16), int(dataFullStr[10:12], 16)).timestamp()
                    diff = ts_log - ts
                    if ts_log_last is None:
                        ts_log_last = ts_log
                    ts_log_diff = ts_log - ts_log_last
                    ts_log_last = ts_log
                    if ts_log_first is None:
                        ts_log_first = ts_log
                except (ValueError, IndexError):
                    pass
                continue  # Don't write time sync to new log

            elif canId == 1200:  # UTC
                if not dataDateStr is None:
                    try:
                        ts_gps = datetime.datetime((int(dataDateStr[4:6], 16) * 100) + int(dataDateStr[6:8], 16),
                                                   int(dataDateStr[2:4], 16),
                                                   int(dataDateStr[0:2], 16), int(dataStr[0:2], 16),
                                                   int(dataStr[2:4], 16),
                                                   int(dataStr[4:6], 16)).timestamp()
                        if ts_gps_first is None:
                            ts_gps_first = ts_gps
                        mmm.append((ts + (diff if diff is not None else 0.0)) - ts_gps)
                    except (ValueError, IndexError):
                        pass
                dataUtcStr = dataStr

            elif canId == 1206:  # Date
                dataDateStr = dataStr

            # Write to new log
            data_hex = "".join("{:02X}".format(b) for b in msg.data)
            new_log.write("({:f}) can0 {:X}#{:s}\n".format(ts + (diff if diff is not None else 0.0), canId, data_hex))
            new_cnt = new_cnt + 1

            if ts_log_first is not None and (ts_log_diff is not None) and ts_log_diff > 1.0:
                close_logfile(ts_log_first)
                print_gps_diff_statistics()
                if syncwithgps and mmm:
                    sync_with_gps(new_log_file_name, mean(mmm))
                mmm = []
                new_log = None
                ts_log_first = None

            statistics(canIds, canId)
            if nodeIdStr:
                statistics(nodeIds, int(nodeIdStr, 16))

        if ts_log_first is None:
            ts_log_first = ts_gps_first

        close_logfile(ts_log_first)
        print_gps_diff_statistics()
        if syncwithgps and mmm:
            sync_with_gps(new_log_file_name, mean(mmm))

    print("canId statistics")
    if translate_canid:
        for k, v in sorted(canIds.items(), key=lambda kv: kv[0], reverse=True):
            print(f"{k} , {canaerospace_ids.get(k, 'Unknown')} : {v}")
        print("\nSorted by frequency:")
        for k, v in sorted(canIds.items(), key=lambda kv: kv[1], reverse=True):
            print(f"{k} , {canaerospace_ids.get(k, 'Unknown')} : {v}")
    else:
        print(sorted(canIds.items(), key=lambda kv: kv[0], reverse=True))
        print(sorted(canIds.items(), key=lambda kv: kv[1], reverse=True))
    print("nodeId statistics")
    print(sorted(nodeIds.items(), key=lambda kv: kv[0], reverse=True))
    print(sorted(nodeIds.items(), key=lambda kv: kv[1], reverse=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
