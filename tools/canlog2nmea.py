import sys
import struct
import datetime
import argparse


# Helper for NMEA checksum
def nmeachecksum(sentence):
    c = 0
    for char in sentence:
        c ^= ord(char)
    return '{:02X}'.format(c)


def format_lat(lat):
    if lat is None: return ","
    direction = "N" if lat >= 0 else "S"
    lat = abs(lat)
    degrees = int(lat)
    minutes = (lat - degrees) * 60
    return "{:02d}{:07.4f},{}".format(degrees, minutes, direction)


def format_lon(lon):
    if lon is None: return ","
    direction = "E" if lon >= 0 else "W"
    lon = abs(lon)
    degrees = int(lon)
    minutes = (lon - degrees) * 60
    return "{:03d}{:07.4f},{}".format(degrees, minutes, direction)


def getFloat(data):
    return struct.unpack('>f', data[4:8])[0]


def getDoubleL(data):
    return struct.unpack('>l', data[4:8])[0] / 1E7


def getInt(data):
    return struct.unpack('>i', data[4:8])[0]


def output_nmea(state):
    if not state['time']: return

    hh, mm, ss, ss_dec = state['time']
    # Ensure hundredths are within 0-99
    ss_dec = ss_dec % 100
    time_str = "{:02d}{:02d}{:02d}.{:02d}".format(hh, mm, ss, ss_dec)

    date_str = ""
    if state['date']:
        d, m, c, y = state['date']
        date_str = "{:02d}{:02d}{:02d}".format(d, m, y)

    # $GPGGA
    # $GPGGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx*hh
    # Note: format_lat/format_lon already return "val,dir"
    gga = "GPGGA,{},{},{},{:d},{:02d},{:.1f},{:.1f},M,{:.1f},M,,".format(
        time_str, format_lat(state['lat']), format_lon(state['lon']),
        state['quality'], state['satellites'], state['hdop'], state['alt'], state['geoid_sep']
    )
    print("${}*{}".format(gga, nmeachecksum(gga)))

    # $PDVDV,v1,v2,v3,v4,v5,v6,v7,v8*cs
    # Deduced order: v1:Netto, v2:STF, v3:Avg, v4:G, v5:IAS, v6:TAS, v7:Alt, v8:OAT
    pdvdv = "PDVDV,{:.1f},,{:.1f},{:.2f},{:.1f},{:.1f},{:.1f},{:.1f}".format(
        state['netto'], 0.0, state['accel_z'] / 9.81, state['ias'], state['tas'], state['alt'], state['oat'] - 273.15
    )
    print("${}*{}".format(pdvdv, nmeachecksum(pdvdv)))

    # $PDVDS,dist_to_wp,km,dist_to_go,km,arrival_alt,m*cs
    pdvds = "PDVDS,,,,,"
    print("${}*{}".format(pdvds, nmeachecksum(pdvds)))

    # $PDSWC,sw1,sw2,sw3,sw4,sw5,sw6,sw7,sw8*cs
    pdswc = "PDSWC,{}".format(",".join(map(str, state['switches'])))
    print("${}*{}".format(pdswc, nmeachecksum(pdswc)))

    # $PFLAU,rx,tx,gps,power,alarm,rel_bearing,alarm_level,rel_vert,rel_dist,id*hh
    pflau = "PFLAU,0,1,1,1,0,0,0,0,0"
    print("${}*{}".format(pflau, nmeachecksum(pflau)))

    # $PDVVT,track_true,T,track_mag,M,gs_kmh,K,gs_ms,S*hh
    gs_kmh = state['gs'] * 3.6
    pdvvt = "PDVVT,{:.1f},T,{:.1f},M,{:.1f},K,{:.1f},S".format(
        state['tt'], state['mag_track'], gs_kmh, state['gs']
    )
    print("${}*{}".format(pdvvt, nmeachecksum(pdvvt)))

    # $GPRMC
    # $GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a,m*hh
    gs_knots = state['gs'] * 1.94384  # m/s to knots
    rmc = "GPRMC,{},A,{},{},{:.1f},{:.1f},{},,,".format(
        time_str, format_lat(state['lat']), format_lon(state['lon']),
        gs_knots, state['tt'], date_str
    )
    print("${}*{}".format(rmc, nmeachecksum(rmc)))

    # $PGRMZ,alt,f,fix*hh
    alt_feet = state['alt'] * 3.28084
    pgrmz = "PGRMZ,{:.0f},f,{:d}".format(alt_feet, 3 if state['quality'] > 0 else 1)
    print("${}*{}".format(pgrmz, nmeachecksum(pgrmz)))


def main():
    parser = argparse.ArgumentParser(description='Convert CAN dump log to NMEA.')
    parser.add_argument('input', help='Input CAN log file')
    args = parser.parse_args()

    # Current state
    state = {
        'time': None,
        'date': None,
        'lat': None,
        'lon': None,
        'alt': 0.0,
        'geoid_sep': 0.0,
        'gs': 0.0,
        'tt': 0.0,
        'mag_track': 0.0,
        'quality': 1,
        'hdop': 0.0,
        'satellites': 8,
        'netto': 0.0,
        'tek_rate': 0.0,
        'accel_z': 0.0,
        'ias': 0.0,
        'tas': 0.0,
        'oat': 273.15,
        'switches': [0] * 8
    }

    try:
        with open(args.input, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3: continue

                try:
                    # Expecting format: (timestamp) interface ID#DATA
                    id_hex, data_hex = parts[2].split('#')
                    can_id = int(id_hex, 16)
                    data_bytes = bytes.fromhex(data_hex)
                except ValueError:
                    continue

                if len(data_bytes) < 8: continue
                payload = data_bytes[4:8]

                if can_id == 1200:  # UTC
                    state['time'] = struct.unpack('4B', payload)
                    output_nmea(state)
                elif can_id == 1206:  # Date
                    state['date'] = struct.unpack('4B', payload)
                elif can_id == 1036:  # Lat
                    state['lat'] = getDoubleL(data_bytes)
                elif can_id == 1037:  # Lon
                    state['lon'] = getDoubleL(data_bytes)
                elif can_id == 1038:  # Alt
                    state['alt'] = getFloat(data_bytes)
                elif can_id == 322:  # Standard Alt
                    # Use standard alt if GPS alt not yet available or as fallback
                    if state['alt'] == 0.0:
                        state['alt'] = getFloat(data_bytes)
                elif can_id == 1039:  # GS
                    state['gs'] = getFloat(data_bytes)
                elif can_id == 1040:  # True Track
                    state['tt'] = getFloat(data_bytes)
                elif can_id == 1041:  # Mag Track
                    state['mag_track'] = getFloat(data_bytes)
                elif can_id == 1134:  # Geoid sep
                    state['geoid_sep'] = getFloat(data_bytes)
                elif can_id == 1047:  # HDOP
                    state['hdop'] = getFloat(data_bytes)
                elif can_id == 354:  # Netto
                    state['netto'] = getFloat(data_bytes)
                elif can_id == 348:  # TEK Rate
                    # state['tek_rate'] = getFloat(data_bytes)
                    pass
                elif can_id == 302:  # Accel Z
                    state['accel_z'] = getFloat(data_bytes)
                elif can_id == 315:  # IAS
                    state['ias'] = getFloat(data_bytes) * 3.6  # m/s to km/h
                elif can_id == 316:  # TAS
                    state['tas'] = getFloat(data_bytes) * 3.6  # m/s to km/h
                elif can_id == 335:  # OAT
                    state['oat'] = getFloat(data_bytes)
    except FileNotFoundError:
        print(f"Error: File {args.input} not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
