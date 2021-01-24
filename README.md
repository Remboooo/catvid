catvid
========

Small Python3 script to concatenate similar video files, e.g. scenes recorded from a camera into a single contiguous
video file, while recording date/time information to a separate xlsx/txt file for future reference.

See LICENSE for the license. The management summary is that there is none and you can do what you want as long as you
don't hold me responsible for the results.

Requirements
------------
- python3
- ffmpeg/avconv
- mediainfo

Setting up
----------

In all of the below documentation I will assume the Python 3 binary is `python3` and the Pip package manager script 
is `pip3`. On some systems (notably Windows) it may just be `python` and `pip`.

### 1. Installing required software
Make sure `ffmpeg` (or `avconv`) and `mediainfo` are on your path.

On Debian/Ubuntu you can use `apt install ffmpeg mediainfo`.

On Windows using Chocolatey you can use `choco install ffmpeg mediainfo-cli`.

Also make sure you have a working Python 3 installation with the pip package manager
(the latter is only required to follow the instruction below; if you're an experienced Python user, 
make your own judgement on how to get the relevant packages).

### 2. Installing Python requirements
#### Option 1: use virtualenv (preferred)
1. `pip3 install virtualenv`
2. `virtualenv -p python3 venv`
3. `venv/bin/pip install -r requirements.txt` 
   or on Windows: `venv/scripts/pip install -r requirements.txt`

#### Option 2: use system python3
`pip3 install -r requirements.txt` (replace `pip3` with `pip` on Windows)

### 3. Read the help
Once the requirements are in place, you can use `./catvid --help` (Linux) or `catvid --help` (Windows) in this folder

You may want to add the `catvid` folder to your PATH to be able to use the tool from anywhere 
(and without the `./` on Linux).

Examples
--------
### Concatenate multiple equally encoded MPEG-2 AVI files without transcoding
This is the original use for this tool; concatenating AVI files originating from miniDV tapes into one big one
while writing out a .txt and .xlsx file describing the source scenes, their date/time info and where to find them in 
the resulting video. This uses the 'copydv' preset which determines how to tell FMPEG to concatenate video files. List
all of them using the commandline parameter '-P'.

`catvid -p copydv 1.avi 2.avi -o out.avi`

Takes in multiple MPEG-2 AVI files and writes them into one big `out.avi`, and writes a description of what files
ended up where in the output to `out.txt`, `out.xlsx` and `out.cvc` which is a 'collection file' that allows later
re-processing of the same inputs using different presets or different output formats.

**NOTE:** This method keeps the metadata such as recording time, but only works for MPEG-2 AVI files.

### Concatenate multiple MP4 files
This extends the tool for use with modern cameras. It concatenates the input files using the 'concat' FFMPEG demuxer
and copies the streams to the target format without re-encoding. 

`catvid c0001.mp4 c0002.mp4 -o out.mkv`

**NOTE:** This only works for extremely similar video files, i.e. different scenes from one specific camera shot at the
same quality settings.

### Transcode multiple MP4 files

This extends the tool for use with multiple scenes shot at different settings. 
It simultaneously concatenates the input files and re-encodes them to a target format.
It can also be used to e.g. re-encode a video file to 1080p directly from multiple source files.
Currently we can choose between the presets `4k` and `1080p`, both of which use libx265 to encode with a default 
quality rate factor of 28 and a FLAC encoded audio stream.

`catvid -p 1080p c0001.mp4 c0002.mp4 -o out.mkv`

**NOTE:** the output file format must be MKV because other containers don't currently support a FLAC audio stream.

### Further notes
Many more options are available than described in the examples; use `catvid --help` to see them all.
