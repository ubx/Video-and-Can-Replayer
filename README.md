# Video-and-Can-Replayer
Replay a video in sync with a can-bus logfile.

![Screenshot](doc/video_and_can_replayer2.gif?raw=true "Screenshot")

Run with (Python 3.7):  
``````python VideoAndCanPlayer2.py config2.json --map``````

or without map:  
``````python VideoAndCanPlayer2.py config2.json``````

ToDos

* Bookmarks: add text description
* Performance improve

### Import CAN logfile into a sql db

``````python logfile2sqldb.py <can-logfile> <db-file>``````
