import argparse
import datetime
import os
import re
from statistics import mean, variance, stdev

'''
   Adjust timestamps of a CAN dump file according to GPS time (UTC).
      sudo ip link add dev vcan0 type vcan
      sudo ip link set up vcan0
'''


## todo -- user rather Log Reader then our  complicated parsing code !!!


# (1564994147.496590) can0 78A#0A0C1CE5F7990000
def getCanData(line):
    parts = (" ".join(line.split()).split())
    ts = float(parts[0][1:-1])
    canDevStr = parts[1]
    parts2 = parts[2].split("#")

    canIdStr = parts2[0]
    nodeIdStr = parts2[1][0:2]
    dataStr = parts2[1][8:40]
    return ts, canDevStr, canIdStr, dataStr, nodeIdStr


def statistics(ids, id_):
    ids[id_] = ids.get(id_, 0) + 1


def check(line: str) -> bool:
    pattern = r'^\(\d+\.\d+\)\s+(?:can|vcan)\d*\s+[0-9A-Fa-f]+#[0-9A-Fa-f]+$'
    return bool(re.match(pattern, line))


def close_logfile(ts_log):
    global new_log, new_log_file_name
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Correct time stamps according to the logger time sync (canId 0x1FFFFFF0) and optional GPS time (UTC).'
                    'Only useful for CANaerospace format!')
    parser.add_argument('-input', metavar='input', type=str, required=True, help='Input logfile.')
    parser.add_argument('-gps', action='store_true', help='Sync with GPS time (canIDs 1200 and 1206.')

    args = parser.parse_args(argv)
    inputFile = args.input
    syncwithgps = args.gps

    # Globals used by helper functions close_logfile() and print_gps_diff_statistics()
    global new_log, new_log_file_name, mmm, new_cnt
    new_log = None
    new_log_file_name = None
    mmm = []
    new_cnt = 0

    with open(inputFile) as inf:
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

        for cnt, line in enumerate(inf):
            if new_log is None:
                log_file_nr = log_file_nr + 1
                new_log = open("data/newlog_{}.log".format(log_file_nr), "w+")
            if not line.startswith("*"):
                if not check(line):
                    print("ERROR, line={:d} >>>{:s}<<<".format(cnt, line.replace("\n", "")))
                else:
                    ts, canDevStr, canIdStr, dataStr, nodeIdStr = getCanData(line)
                    diff = 0.0
                    canId = int(canIdStr, 16)
                    if ts_first is None:
                        ts_first = ts
                    if ts_prev is None:
                        ts_prev = ts
                    else:
                        if ts - ts_prev > 1.1:
                            print("ERROR, gap between ts {:f} and {:f}, {:.3f}s \n".format(ts_prev, ts, ts - ts_prev))
                        ts_prev = ts

                    if canId == 0x1FFFFFF0:  # Time sync
                        ts_log = datetime.datetime((int(line[34:36], 16) + 2000), int(line[37:38], 16),
                                                   int(line[38:40], 16), int(line[40:42], 16),
                                                   int(line[42:44], 16), int(line[44:46], 16)).timestamp()
                        diff = ts_log - ts
                        if ts_log_last is None:
                            ts_log_last = ts_log
                        ts_log_diff = ts_log - ts_log_last
                        ts_log_last = ts_log
                        if ts_log_first is None:
                            ts_log_first = ts_log
                        line = None

                    elif canId == 1200:  # UTC
                        if not dataDateStr is None:
                            ts_gps = datetime.datetime((int(dataDateStr[4:6], 16) * 100) + int(dataDateStr[6:8], 16),
                                                       int(dataDateStr[2:4], 16),
                                                       int(dataDateStr[0:2], 16), int(dataStr[0:2], 16),
                                                       int(dataStr[2:4], 16),
                                                       int(dataStr[4:6], 16)).timestamp()
                            if ts_gps_first is None:
                                ts_gps_first = ts_gps
                            mmm.append((ts + diff) - ts_gps)
                        dataUtcStr = dataStr

                    elif canId == 1206:  # Date
                        dataDateStr = dataStr

                    if line is not None:
                        parts = (" ".join(line.split()).split())
                        new_log.write("({:f}) {} {}\n".format(ts + diff, parts[1], parts[2]))
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
                    statistics(nodeIds, int(nodeIdStr, 16))

        if ts_log_first is None:
            ts_log_first = ts_gps_first

        close_logfile(ts_log_first)
        print_gps_diff_statistics()
        if syncwithgps and mmm:
            sync_with_gps(new_log_file_name, mean(mmm))

    print("canId statistics")
    print(sorted(canIds.items(), key=lambda kv: kv[0], reverse=True))
    print(sorted(canIds.items(), key=lambda kv: kv[1], reverse=True))
    print("nodeId statistics")
    print(sorted(nodeIds.items(), key=lambda kv: kv[0], reverse=True))
    print(sorted(nodeIds.items(), key=lambda kv: kv[1], reverse=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
