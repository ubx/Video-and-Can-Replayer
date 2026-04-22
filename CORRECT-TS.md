# correct-ts.py

`correct-ts.py` is a command-line utility that rewrites CAN dump logs with corrected timestamps. It is designed for
CANaerospace-style frames and uses embedded time information from the log stream to align message times with real-world
clock time.

## What it does

- Reads an input CAN dump file passed with `-input`.
- Validates line format (expects `(<timestamp>) <canX|vcanX> <can_id>#<data>`).
- Tracks and counts CAN IDs and node IDs for summary statistics.
- Uses logger time-sync frames (`0x1FFFFFF0`) to compute a timestamp offset (`diff`) and apply it to normal messages.
- Detects larger logger-time jumps and splits output into separate corrected log files.
- Optionally (`-gps`) computes GPS-based offset checks from UTC (`1200`) + Date (`1206`) frames and creates additional
  `-gps.log` files.

## Time-correction logic

1. Every regular frame starts with its original dump timestamp.
2. When a logger sync frame (`0x1FFFFFF0`) appears, the script extracts date/time bytes from payload and converts them
   to a UNIX timestamp.
3. The correction offset is calculated as:
    - `diff = logger_timestamp - frame_timestamp`
4. Each writable frame is emitted with corrected time:
    - `corrected_ts = original_ts + diff`

## Output files

- Intermediate files are written as `data/newlog_<n>.log`.
- On segment close, they are renamed to `data/candump-<datetime>.log`.
- With `-gps`, a second pass can generate `data/candump-<datetime>-gps.log` using the mean GPS difference.

## GPS synchronization mode (`-gps`)

- `1206` provides date information.
- `1200` provides UTC time.
- When both are available, the script computes the difference between corrected logger time and GPS time, stores
  samples, and prints statistics (mean, variance, stdev, max, min).
- If GPS samples exist for a segment, the mean difference is applied to create the `-gps.log` variant.

## Notes and limitations

- Intended for CANaerospace payload layout and specific time/date frame formats.
- Invalid input lines are reported but processing continues.
- Timestamp gaps larger than about `1.1s` are reported as errors.
- Logger sync frames themselves are not written to output logs.