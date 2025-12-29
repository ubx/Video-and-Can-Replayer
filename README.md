# Video-and-Can-Replayer
Replay a video in sync with a CAN-bus logfile. This project provides tools for synchronizing video playback with CAN-bus data, including a real-time dashboard for CANaerospace data.

![Screenshot](doc/video_and_can_replayer2.gif?raw=true "Screenshot")

### Video and CAN Player
Run with (Python 3.10+):
```bash
python VideoAndCanPlayer2.py config2.json --map
```

Or without map:
```bash
python VideoAndCanPlayer2.py config2.json
```

### CANaerospace Dashboard
A real-time Dash-based dashboard to visualize CANaerospace data (IAS, Flaps, etc.) from a CAN interface.
```bash
python Dashboard/CANaerospaceDashboard.py -channel can0
```

### Import CAN logfile into a SQL database
```bash
python logfile2sqldb.py <can-logfile> <db-file>
```

### ToDos
* Bookmarks: add text description
* Performance improve
