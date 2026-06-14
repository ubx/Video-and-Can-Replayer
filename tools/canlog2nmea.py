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


def format_pflaa(alarm_level, rel_north, rel_east, rel_vert, id_type, id_hex, track, turn_rate, gs, climb_rate,
                 ac_type, no_track=None, source=None, rssi=None):
    pflaa = "PFLAA,{},{},{},{},{},{},{},{},{},{},{}".format(
        alarm_level, rel_north, rel_east, rel_vert, id_type, id_hex, track, turn_rate, gs, climb_rate, ac_type
    )
    if no_track is not None:
        pflaa += ",{}".format(1 if no_track else 0)
        if source is not None:
            pflaa += ",{}".format(source)
            if rssi is not None:
                pflaa += ",{}".format(rssi)
    return "${}*{}".format(pflaa, nmeachecksum(pflaa))


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
    pflau_data = state['pflau']
    pflau = "PFLAU,{},{},{},{},{},{},{},{},{}".format(
        pflau_data['rx'], pflau_data['tx'], pflau_data['gps'],
        pflau_data['power'], pflau_data['alarm'], pflau_data['rel_bearing'],
        pflau_data['alarm_level'], pflau_data['rel_vert'], pflau_data['rel_dist']
    )
    print("${}*{}".format(pflau, nmeachecksum(pflau)))

    # Output $PFLAA for each known object
    for obj_id, obj in state['flarm_objects'].items():
        # Only output if we have at least position data
        if obj.get('rel_north') is not None:
            print(format_pflaa(
                obj['alarm_level'], obj['rel_north'], obj['rel_east'], obj['rel_vert'],
                obj['id_type'], obj['id_hex'],
                obj['track'] if obj['valid_track'] else "",
                "{:.1f}".format(obj['turn_rate']) if obj['valid_turn_rate'] else "",
                "{:.1f}".format(obj['gs']) if obj['valid_gs'] else "",
                "{:.1f}".format(obj['climb_rate']) if obj['valid_climb_rate'] else "",
                obj['ac_type'],
                no_track=obj.get('no_track'),
                source=obj.get('source'),
                rssi=obj.get('rssi')
            ))

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
        'switches': [0] * 8,
        'pflau': {
            'rx': 0, 'tx': 1, 'gps': 1, 'power': 1, 'alarm': 0,
            'rel_bearing': 0, 'alarm_level': 0, 'rel_vert': 0, 'rel_dist': 0
        },
        'flarm_objects': {}
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
                elif can_id == 1300:  # FLARM_STATE (PFLAU)
                    # Logic from CANaerospace.cpp and flarmPropagated.cpp
                    service_code = data_bytes[1]
                    if service_code == 0:
                        # Case 0 in flarmPropagated.cpp
                        state['pflau']['rx'] = data_bytes[5]
                        state['pflau']['tx'] = data_bytes[4] & 0x01
                        state['pflau']['gps'] = (data_bytes[4] >> 1) & 0x03
                        # objectData->AlarmLevel is set if bit 4 of data[0] is NOT set
                        if not (data_bytes[4] >> 4 & 0x01):
                            state['pflau']['alarm_level'] = 3
                    elif service_code == 1:
                        state['pflau']['alarm_level'] = data_bytes[4] & 0x07
                    elif service_code == 2:
                        # USHORT2
                        u1, u2 = struct.unpack('>HH', payload)
                        state['pflau']['rel_vert'] = u1
                        state['pflau']['rel_dist'] = u2
                    elif service_code == 3:
                        # SHORT
                        s1 = struct.unpack('>h', payload[:2])[0]
                        state['pflau']['rel_bearing'] = s1
                elif 1301 <= can_id <= 1304:  # FLARM_OBJECT (PFLAA)
                    # Logic from CANaerospace.cpp and flarmPropagated.cpp
                    # ID 1301=AL3, 1302=AL2, 1303=AL1, 1304=AL0
                    service_code = data_bytes[1]
                    messageindex = service_code & 0x0F
                    validFlags = (service_code >> 4) & 0x0F

                    obj_can_id = can_id
                    if obj_can_id not in state['flarm_objects']:
                        state['flarm_objects'][obj_can_id] = {
                            'alarm_level': 1304 - obj_can_id,
                            'rel_north': 0, 'rel_east': 0, 'rel_vert': 0,
                            'id_type': 0, 'id_hex': '000000', 'track': 0, 'turn_rate': 0.0,
                            'gs': 0.0, 'climb_rate': 0.0, 'ac_type': 0,
                            'valid_track': False, 'valid_gs': False, 'valid_turn_rate': False, 'valid_climb_rate': False
                        }
                    obj = state['flarm_objects'][obj_can_id]

                    if messageindex == 0:
                        # RelNorth, RelEast as SHORT
                        u1, u2 = struct.unpack('>hh', payload)
                        obj['rel_north'] = u1
                        obj['rel_east'] = u2
                        obj['alarm_level'] = 1304 - obj_can_id
                    elif messageindex == 1:
                        # RelVert, Track
                        u1, u2 = struct.unpack('>hh', payload)
                        obj['rel_vert'] = u1
                        obj['track'] = u2
                        obj['valid_track'] = (validFlags & 0x02) != 0  # Simplified check
                    elif messageindex == 2:
                        # GroundSpeed, Type, ClimbRate, TurnRate
                        obj['gs'] = data_bytes[4]
                        obj['ac_type'] = data_bytes[5]
                        obj['climb_rate'] = struct.unpack('>b', data_bytes[6:7])[0] / 10.0
                        obj['turn_rate'] = struct.unpack('>b', data_bytes[7:8])[0] / 10.0
                        obj['valid_gs'] = (validFlags & 0x01) != 0
                        obj['valid_climb_rate'] = (validFlags & 0x04) != 0
                        obj['valid_turn_rate'] = (validFlags & 0x08) != 0
                    elif messageindex == 3:
                        obj['id_type'] = data_bytes[4]  # IdType
                        obj['id_hex'] = '{:02X}{:02X}{:02X}'.format(data_bytes[5], data_bytes[6], data_bytes[7])
    except FileNotFoundError:
        print(f"Error: File {args.input} not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
