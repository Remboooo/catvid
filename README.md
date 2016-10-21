ConcatDV
========

Small Python3 script to concatenate scenes recorded from miniDV tapes into a single contiguous AVI, while
recording date/time information to a separate xlsx/txt file for future reference.

See LICENSE for the license. The management summary is that there is none and you can do what you want as long as you
don't hold me responsible for the results.

Requirements:
- python3
- avconv
- mediainfo

Setting up:
- Makes sure `avconv` and `mediainfo` are on your path
- `pip3 install -r requirements.txt`
- Read the output of `python3 concatdv.py --help`


```
usage: concatdv.py [-h] [--sort {name,time,none}] [--xlsx XLSX] [--txt TXT]
                   [--out OUT] [--no-cache] [--no-periodic-cache-save]
                   [--renew-cache]
                   file [file ...]

Concatenate miniDV-sourced AVI scene files and export date/time info of the
output to XLSX/TXT

positional arguments:
  file                  AVI input files

optional arguments:
  -h, --help            show this help message and exit
  --sort {name,time,none}
                        Sort files by given criterion. name: Sort by filename.
                        time: Sort by recorded date/time (DEFAULT). none: Sort
                        as given in argument list.
  --xlsx XLSX           File to write XLSX information to
  --txt TXT             File to write plain text information to
  --out OUT             Output AVI file to write
  --no-cache            Don't use the metadata cache
  --no-periodic-cache-save
                        Stop saving the cache every 100 files (might help with
                        extreme amounts of small files)
  --renew-cache         Start with an empty metadata cache
```
