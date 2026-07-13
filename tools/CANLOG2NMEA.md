### CANLOG2NMEA.py

`canlog2nmea.py` is a utility tool designed to convert CAN dump logs (specifically in the format produced by `candump`)
into NMEA 0183 sentences. This allows flight data captured from a CAN bus (e.g., CANaerospace) to be used with standard
NMEA-compatible software and mapping tools.

#### Usage

```bash
python3 tools/canlog2nmea.py <input_can_log_file>
```

#### Supported Input Format

The script expects the input CAN log to follow the standard `(timestamp) interface ID#DATA` format. For example:

```
(1629234567.123456) can0 4B0#00000000AABBCCDD
```

#### Supported CAN IDs and Data Types

The tool interprets various CAN IDs typically found in CANaerospace environments:

* **1200**: UTC Time
* **1206**: Date
* **1036 / 1037**: Latitude / Longitude (Double precision)
* **1038 / 322**: Altitude (Float)
* **1039**: Ground Speed (Float)
* **1040**: True Track (Float)
* **1041**: Magnetic Track (Float)
* **1134**: Geoid Separation (Float)
* **1047**: HDOP (Float)
* **354**: Netto Vario (Float)
* **302**: Vertical Acceleration (Float)
* **315 / 316**: IAS / TAS (Float, converted from m/s to km/h)
* **335**: Outside Air Temperature (OAT)
* **1300**: FLARM State ($PFLAU)
* **1301-1304**: FLARM Objects ($PFLAA)

#### Generated NMEA Sentences

The tool generates the following NMEA sentences:

* **$GPGGA**: Global Positioning System Fix Data (Time, Position, Quality, Satellites, Altitude)
* **$GPRMC**: Recommended Minimum Specific GNSS Data
* **$PGRMZ**: Garmin proprietary altitude sentence (in feet)
* **$PFLAU / $PFLAA**: FLARM status and traffic information
* **$PDVDV / $PDVVT / $PDVDS / $PDSWC**: Proprietary sentences for variometer data, ground track, distance, and switch
  states.

#### Output

The script outputs the generated NMEA sentences directly to `stdout`. You can redirect the output to a file:

```bash
python3 tools/canlog2nmea.py log.can > output.nmea
```
