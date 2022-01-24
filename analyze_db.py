import argparse
import sqlite3

'''
   Analyze canlog db in several ways...
'''

parser = argparse.ArgumentParser(
    description='Analyze canlog db in several ways. So far check for missing of "Message Code"')
parser.add_argument('-dbfile', metavar='dbfile', type=str, help='Database file.')
args = parser.parse_args()

msg_codes = {}
msg_codes_stats = {}
msg_ids_stats = {}
canIds_stats = {}
cnt = 0


def codes_statistics(codes, node, code, codes_stats, id, ids_stats):
    if node in codes:
        i = 1
        if codes[node] == 255:
            codes[node] = 0
            i = 0
        if not codes[node] + i == code:
            if node not in codes_stats:
                codes_stats[node] = 1
            else:
                codes_stats[node] += 1
            if id not in ids_stats:
                ids_stats[id] = 1
            else:
                ids_stats[id] += 1
    codes[node] = code


def canid_statistics(ids, id):
    if id not in ids:
        ids[id] = 1
    ids[id] += 1


con = sqlite3.connect(args.dbfile)
cur = con.cursor()
cur.fetchall()
cur.execute('SELECT * FROM messages')
cnt = 0
for msg in cur:
    codes_statistics(msg_codes, msg[6][0], msg[6][3], msg_codes_stats, msg[1], msg_ids_stats)
    canid_statistics(canIds_stats, msg[1])
    cnt += 1

print("codes not in sync statistics of total ", cnt)
print(sorted(msg_codes_stats.items(), key=lambda kv: kv[0]))
print(sorted(msg_ids_stats.items(), key=lambda kv: kv[0]))

print("canId statistics of total ", cnt)
print(sorted(canIds_stats.items(), key=lambda kv: kv[0]))
print(sorted(canIds_stats.items(), key=lambda kv: kv[1], reverse=True))
