import argparse
import datetime
import os
from statistics import mean, variance, stdev

'''
   Adjust time stamps according to to GPS time (UTC):
      sudo ip link add dev vcan0 type vcan
      sudo ip link set up vcan0
'''

## todo -- user rather Log Reader then these rather complicated parsing code !!!

parser = argparse.ArgumentParser(
    description='Correct time stamps according to the logger time synch (canId 0x1FFFFFF0) and optional GPS time (UTC).'
                'Only useful for CANaerospace format!')
parser.add_argument('-input', metavar='input', type=str, help='Input logfile.')
parser.add_argument('-gps', action='store_true', help='Sync with GPS time (canIDs 1200 and 1206.')

args = parser.parse_args()

inputFile = args.input
syncwithgps = args.gps


# (1564994147.496590) can0 78A#0A0C1CE5F7990000
def getCanDate(line):
    parts = (" ".join(line.split()).split())
    ts = float(parts[0][1:18])
    canDevStr = parts[1]
    parts2 = parts[2].split("#")

    canIdStr = parts2[0]
    nodeIdStr = parts2[1][0:2]
    dataStr = parts2[1][8:40]
    return ts, canDevStr, canIdStr, dataStr, nodeIdStr


def statistics(ids, id):
    if id not in ids:
        ids[id] = 1
    ids[id] = ids[id] + 1


## "(1564994154.769054) can0 40C#0A032A3A1BC27A49"
## "(1569437515.1000000) can0 141#0A0200A942E1CBEA" --> ERROR
def check(line):
    if not line.startswith("("):
        return False
    for c in line[1:11]:
        if not c.isdigit():
            return False
    if line[11] != '.':
        return False
    for c in line[12:18]:
        if not c.isdigit():
            return False
    if line[18] != ')':
        return False
    return True


def close_logfile():
    global new_log, new_log_file_name
    try:
        new_log.close()
        new_log_file_name = "data/candump-{}.log". \
            format(datetime.datetime.fromtimestamp(int(ts_log_first))).replace(" ", "_").replace(":", "")
        os.rename(new_log.name, new_log_file_name)
    except IOError:
        pass


def print_gps_diff_statistics():
    global mmm
    m = mean(mmm)
    print(new_log_file_name, " cnt=", new_cnt, "mean=", m, "variance=", variance(mmm, m), "stdev=", stdev(mmm, m),
          "max=", max(mmm), "min=", min(mmm))


def sync_with_gps(log_file_name: str, diff):
    log_file_name_gps = log_file_name.replace(".log", "-gps.log")
    with open(log_file_name_gps, "w") as lf_gps, open(log_file_name) as lf:
        for _, line in enumerate(lf):
            ts, channel, frame = line.strip().split()
            ts = float(ts[1:-1])
            lf_gps.write("({:f}) {} {}\n".format(ts - diff, channel, frame))


with open(inputFile) as inf:
    canIds = {}
    nodeIds = {}
    dataUtcStr = None
    dataDateStr = None
    ts_log_last = None
    ts_log_first = None
    log_file_nr = 0
    new_log = None
    new_log_file_name = None
    diff = None
    ts_log_diff = None
    mmm = []
    new_cnt = 0

    for cnt, line in enumerate(inf):
        if new_log is None:
            log_file_nr = log_file_nr + 1
            new_log = open("data/newlog_{}.log".format(log_file_nr), "w+")
        if not check(line):
            print("ERROR, line={:d} {:s}".format(cnt, line))
        else:
            ts, canDevStr, canIdStr, dataStr, nodeIdStr = getCanDate(line)
            canId = int(canIdStr, 16)

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
                                               int(dataDateStr[0:2], 16), int(dataStr[0:2], 16), int(dataStr[2:4], 16),
                                               int(dataStr[4:6], 16)).timestamp()
                    mmm.append((ts + diff) - ts_gps)
                dataUtcStr = dataStr

            elif canId == 1206: # Date
                dataDateStr = dataStr

            if line is not None:
                parts = (" ".join(line.split()).split())
                new_log.write("({:f}) {} {}\n".format(ts + diff, parts[1], parts[2]))
                new_cnt = new_cnt + 1

            if not ts_log_first is None and ts_log_diff > 1.0:
                close_logfile()
                print_gps_diff_statistics()
                if syncwithgps:
                    sync_with_gps(new_log_file_name, mean(mmm))
                mmm = []
                new_log = None
                ts_log_first = None

            statistics(canIds, canId)
            statistics(nodeIds, int(nodeIdStr, 16))

    close_logfile()
    print_gps_diff_statistics()
    if syncwithgps:
        sync_with_gps(new_log_file_name, mean(mmm))

print("canId statistics")
print(sorted(canIds.items(), key=lambda kv: kv[0], reverse=True))
print(sorted(canIds.items(), key=lambda kv: kv[1], reverse=True))
print("nodeId statistics")
print(sorted(nodeIds.items(), key=lambda kv: kv[0], reverse=True))
print(sorted(nodeIds.items(), key=lambda kv: kv[1], reverse=True))
