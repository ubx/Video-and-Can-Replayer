import argparse
import datetime
import math
import re
import signal
import struct
import sys

LINE_RE = re.compile(r"^\((?P<timestamp>[^)]+)\)\s+\S+\s+(?P<canid>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]+)$")


def half_to_float(bits):
    sign = -1.0 if (bits & 0x8000) else 1.0
    exponent = (bits >> 10) & 0x1F
    fraction = bits & 0x03FF

    if exponent == 0:
        if fraction == 0:
            return math.copysign(0.0, sign)
        return sign * (2 ** -14) * (fraction / 1024.0)

    if exponent == 0x1F:
        if fraction == 0:
            return sign * float("inf")
        return float("nan")

    return sign * (2 ** (exponent - 15)) * (1.0 + fraction / 1024.0)


def interpret_u16(value):
    be_bytes = value.to_bytes(2, byteorder="big", signed=False)
    le_value = int.from_bytes(be_bytes, byteorder="little", signed=False)

    be_i16 = struct.unpack(">h", be_bytes)[0]
    le_i16 = struct.unpack("<h", be_bytes)[0]

    return {
        "u16_be": value,
        "u16_le": le_value,
        "i16_be": be_i16,
        "i16_le": le_i16,
        "hex_be": f"0x{value:04X}",
        "hex_le": f"0x{le_value:04X}",
        "bin": f"{value:016b}",
        "bytes_be": f"{be_bytes[0]:02X} {be_bytes[1]:02X}",
        "f16_be": half_to_float(value),
        "f16_le": half_to_float(le_value),
    }


def parse_line(line):
    match = LINE_RE.match(line.strip())
    if not match:
        return None

    payload = match.group("data")
    if len(payload) < 4:
        return None

    raw_u16 = int(payload[-4:], 16)
    return {
        "timestamp": match.group("timestamp"),
        "canid": match.group("canid").upper(),
        "data": payload.upper(),
        "u16": raw_u16,
    }


def format_row(parsed, utc_ts=False):
    interpreted = interpret_u16(parsed["u16"])
    ts_part = f"ts={parsed['timestamp']}"

    if utc_ts:
        try:
            ts_float = float(parsed["timestamp"])
            ts_utc = datetime.datetime.fromtimestamp(ts_float, tz=datetime.timezone.utc)
            ts_part += f" ts_utc={ts_utc.isoformat()}"
        except ValueError:
            pass

    return (
        f"{ts_part} id={parsed['canid']} data={parsed['data']} "
        f"u16_be={interpreted['u16_be']} u16_le={interpreted['u16_le']} "
        f"i16_be={interpreted['i16_be']} i16_le={interpreted['i16_le']} "
        f"hex_be={interpreted['hex_be']} hex_le={interpreted['hex_le']} "
        f"bin={interpreted['bin']} bytes={interpreted['bytes_be']} "
        f"f16_be={interpreted['f16_be']!r} f16_le={interpreted['f16_le']!r}"
    )


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    parser = argparse.ArgumentParser(
        description="Interpret 16-bit CANaerospace payload values in multiple numeric formats."
    )
    parser.add_argument(
        "logfile",
        nargs="?",
        default="data/flpaps-only.log",
        help="Path to candump-style log file (default: data/flpaps-only.log)",
    )
    parser.add_argument(
        "--canid",
        default="154",
        help="Only process records with this CAN ID (default: 154)",
    )
    parser.add_argument(
        "--utc-ts",
        action="store_true",
        help="Also print timestamp converted to UTC (ISO-8601)",
    )
    args = parser.parse_args()
    wanted_canid = args.canid.upper()

    parsed_count = 0
    skipped_count = 0

    try:
        with open(args.logfile, "r") as infile:
            for line in infile:
                if not line.strip():
                    continue

                parsed = parse_line(line)
                if not parsed:
                    skipped_count += 1
                    continue

                if parsed["canid"] != wanted_canid:
                    continue

                print(format_row(parsed, utc_ts=args.utc_ts))
                parsed_count += 1
    except FileNotFoundError:
        print(f"Error: file not found: {args.logfile}", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nDone. Parsed {parsed_count} lines"
        + (f", skipped {skipped_count} malformed lines." if skipped_count else ".")
    )


if __name__ == "__main__":
    main()
