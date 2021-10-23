# Installation on Linux
* git clone https://github.com/ubx/Video-and-Can-Replayer.git
* cd Video-and-Can-Replayer
* get all files in data directory (not on github)
* verify config2.json config file
* python -m venv <environment>
* source <environment>/bin/activate
* pip install -r requirements.txt 

# Installation on Winows

* git clone https://github.com/ubx/Video-and-Can-Replayer.git
* cd Video-and-Can-Replayer
* get all files in data directory (not on github)
* verify config2.json config file
* install Anaconda (https://www.anaconda.com/distribution)
* conda install kivy -c conda-forge
* pip install -r requirements.txt

# Run

* Setup can device:
  - `sudo ip link set can0 up type can bitrate 500000`
  - `sudo ifconfig can0 txqueuelen 1000`


* python VideoAndCanPlayer2.py config2.json --map

# Create a Windows exe (experimental)

* pip uninstall pyinstaller
* pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
* pyinstaller VideoAndCanPlayer2.spec

### Run it on Windows:

* dist\VideoAndCanPlayer2.exe config2.json
  