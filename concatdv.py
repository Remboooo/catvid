import argparse
import datetime
import glob
import re
import subprocess
import platform
from enum import Enum
from os.path import basename
from os import path, makedirs
from shutil import which

import xlsxwriter
from pathlib import Path
from appdirs import *
import pickle
import errno

duration_match = re.compile(r'\d\d:\d\d:\d\d.\d\d\d')
mediainfo_exe = None
ffmpeg_exe = None


class ConcatStrategy(Enum):
    CONCAT_PROTOCOL = 0
    CONCAT_FILTER = 1


class Preset:
    def __init__(self, ffmpeg_params, complex_filters, description, concat_strategy):
        self.ffmpeg_params = ffmpeg_params
        self.description = description
        self.concat_strategy = concat_strategy
        self.complex_filters = complex_filters

    def build_ffmpeg_params(self, input_files):
        args = []
        if self.concat_strategy == ConcatStrategy.CONCAT_PROTOCOL:
            args += ["-i", "concat:{}".format('|'.join(input_files))]
        elif self.concat_strategy == ConcatStrategy.CONCAT_FILTER:
            args += [a for b in [["-i", f] for f in input_files] for a in b]
            args += [
                "-filter_complex",
                f"concat=n={len(input_files)}:v=1:a=1[catv][outa];[catv]" + ",".join(self.complex_filters) + "[outv]",
            ]
            args += ["-map", "[outv]", "-map", "[outa]"]
        args += self.ffmpeg_params
        return args


encode_presets = {
    "copy": Preset(
        ["-c", "copy"],
        [],
        "Directly copy input to output. Only suited for MPEG-2 (includes DV) files with equal codec properties due to "
        "use of the concatenation protocol.",
        ConcatStrategy.CONCAT_PROTOCOL
    ),

    "1080p": Preset(
        ["-c:v", "libx265", "-crf", "28", "-preset", "medium", "-c:a", "flac"],
        ["scale=-1:1080"],
        "Transcode to 1080p using libx265 with a CRF of 28 and FLAC audio. Suited for any input format.",
        ConcatStrategy.CONCAT_FILTER
    ),

    "4k": Preset(
        ["-c:v", "libx265", "-crf", "28", "-preset", "medium", "-c:a", "flac"],
        ["scale=-1:2160"],
        "Transcode to 4k UHD using libx265 with a CRF of 28 and FLAC audio. Suited for any input format.",
        ConcatStrategy.CONCAT_FILTER
    )
}


def find_tools():
    global mediainfo_exe, ffmpeg_exe
    mediainfo_exe = which("mediainfo")
    if mediainfo_exe is None:
        print(
            "mediainfo commandline tool not found. Use e.g. sudo apt install mediainfo (on Debian/Ubuntu) "
            "or choco install mediainfo-cli (on Windows with Chocolatey) to install it."
        )
        sys.exit(-10)
    ffmpeg_exe = which("ffmpeg") or which("avconv")
    if ffmpeg_exe is None:
        print(
            "ffmpeg or avconv commandline tool not found. Use e.g. sudo apt install ffmpeg (on Debian/Ubuntu) "
            "or choco install ffmpeg (on Windows with Chocolatey) to install it."
        )
        sys.exit(-10)


def get_info(file):
    result = subprocess.run(["mediainfo", "--fullscan", file], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf8')
    info = {}
    for line in output.splitlines():
        if line.startswith("Recorded date"):
            if 'datetime' not in info:
                info['datetime'] = datetime.datetime.strptime(line.split(": ", 1)[1], '%Y-%m-%d %H:%M:%S.000')
        if line.startswith("Tagged date"):
            if 'datetime' not in info:
                info['datetime'] = datetime.datetime.strptime(line.split(": ", 1)[1], '%Z %Y-%m-%d %H:%M:%S')
        if line.startswith("Duration"):
            if 'milliseconds' not in info:
                try:
                    info['milliseconds'] = int(line.split(": ", 1)[1])
                except ValueError:
                    pass
        if line.startswith("Frame count"):
            if 'frames' not in info:
                info['frames'] = int(line.split(": ", 1)[1])
    return info


def ms_to_mm_ss_ms(ms):
    minutes = ms // 60000
    seconds = (ms // 1000) % 60
    millis = ms % 1000
    return "{:02d}:{:02d}.{:03d}".format(minutes, seconds, millis)


def write_txt_report(txt_file, files, file_info):
    with open(txt_file, 'w') as txt:
        offset_ms = 0
        offset_frames = 0
        scene = 1

        for file in files:
            info = file_info[file]

            txt.write("Scene {:d}\n".format(scene))
            txt.write("  Offset (mm:ss.ms)   : {}\n".format(ms_to_mm_ss_ms(offset_ms)))
            txt.write("  Offset (ms)         : {}\n".format(offset_ms))
            txt.write("  Offset (frames)     : {}\n".format(offset_frames))
            txt.write("  Record date/time    : {}\n".format(info['datetime'].strftime('%Y-%m-%d %H:%M:%S') if 'datetime' in info else 'UNKNOWN'))
            txt.write("  Duration (mm:ss.ms) : {}\n".format(ms_to_mm_ss_ms(info['milliseconds']) if 'milliseconds' in info else 'UNKNOWN'))
            txt.write("  Duration (ms)       : {}\n".format(info['milliseconds'] if 'milliseconds' in info else 'UNKNOWN'))
            txt.write("  Duration (frames)   : {}\n".format(info['frames'] if 'frames' in info else 'UNKNOWN'))
            txt.write("  Source filename     : {}\n".format(file))
            txt.write("\n")

            if 'milliseconds' in info:
                offset_ms += info['milliseconds']
            if 'frames' in info:
                offset_frames += info['frames']
            scene += 1


def write_xlsx_report(xlsx, files, file_info):
    with xlsxwriter.Workbook(xlsx) as workbook:
        sheet = workbook.add_worksheet()
        int_fmt = workbook.add_format({'num_format': '0', 'align': 'left'})
        bold_fmt = workbook.add_format({'bold': True, 'align': 'left'})
        datetime_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'align': 'left'})

        sheet.write(0, 0, 'Offset mm:ss.ms', bold_fmt)

        sheet.write(0, 1, 'Offset ms', bold_fmt)
        sheet.write(0, 2, 'Offset frames', bold_fmt)
        sheet.write(0, 3, 'Record date/time', bold_fmt)
        sheet.write(0, 4, 'Duration mm:ss.ms', bold_fmt)
        sheet.write(0, 5, 'Duration ms', bold_fmt)
        sheet.write(0, 6, 'Duration frames', bold_fmt)
        sheet.write(0, 7, 'Source filename', bold_fmt)

        sheet.set_column(0, 2, 15)
        sheet.set_column(3, 3, 25)
        sheet.set_column(4, 6, 15)
        sheet.set_column(7, 7, 100)

        row = 1

        offset_ms = 0
        offset_frames = 0

        for file in files:
            info = file_info[file]

            sheet.write(row, 0, ms_to_mm_ss_ms(offset_ms))
            sheet.write(row, 1, offset_ms, int_fmt)
            sheet.write(row, 2, offset_frames, int_fmt)
            if 'datetime' in info:
                sheet.write_datetime(row, 3, info['datetime'], datetime_fmt)
            if 'milliseconds' in info:
                sheet.write(row, 4, ms_to_mm_ss_ms(info['milliseconds']))
                sheet.write(row, 5, info['milliseconds'], int_fmt)
            if 'frames' in info:
                sheet.write(row, 6, info['frames'], int_fmt)
            sheet.write(row, 7, file)

            if 'milliseconds' in info:
                offset_ms += info['milliseconds']
            if 'frames' in info:
                offset_frames += info['frames']

            row += 1


def do_concatenation(files, output, preset: Preset):
    args = [ffmpeg_exe] + preset.build_ffmpeg_params(files) + [output]
    print(" ".join(args))
    subprocess.run(args)


def open_cache_file(mode):
    cachedir = user_cache_dir('concatdv', 'bad-bit')
    cachefile = path.join(cachedir, 'cache.p')
    try:
        makedirs(cachedir)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e
    try:
        return open(cachefile, mode)
    except OSError as e:
        raise e


def load_cache():
    print("Loading cache file (use --no-cache to disable) ... ", end='', flush=True)
    try:
        with open_cache_file('rb') as c:
            cache = pickle.load(c)
            print('done')
            return cache
    except FileNotFoundError:
        print("does not exist, starting fresh")
        return {}
    except Exception as e:
        print("failed: {}".format(e))
        raise e


def save_cache(cache):
    print("Saving cache file (use --no-cache to disable) ... ", end='', flush=True)
    try:
        with open_cache_file('wb') as c:
            pickle.dump(cache, c)
            print('done')
    except Exception as e:
        print("failed: {}".format(e))


def replace_extension(path, new_ext):
    return os.path.splitext(path)[0] + "." + new_ext


def main():
    find_tools()
    parser = argparse.ArgumentParser(
        description="Concatenate camera video scene files and export date/time info of the output to XLSX/TXT/JSON")
    parser.add_argument("--sort", choices=['name', 'time', 'none'], default='time',
                        help="Sort files by given criterion. "
                             "name: Sort by filename. "
                             "time: Sort by recorded date/time (DEFAULT). "
                             "none: Sort as given in argument list.")
    parser.add_argument("--xlsx", "-x", type=str, help="File to write XLSX metadata to. Default is next to --out.")
    parser.add_argument("--no-xlsx", "-X", action='store_true', help="Disable XLSX metadata writing.")
    parser.add_argument("--txt", "-t", type=str, help="File to write plain text metadata to. Default is next to --out.")
    parser.add_argument("--no-txt", "-T", action='store_true', help="Disable plain text metadata writing.")
    parser.add_argument("--out", "-o", type=str, help="Output filename to write to")
    parser.add_argument("--no-cache", action="store_true", help="Don't use the metadata cache")
    parser.add_argument("--no-periodic-cache-save", action="store_true",
                        help="Stop saving the cache every 100 files (might help with extreme amounts of small files)")
    parser.add_argument("--renew-cache", action="store_true", help="Start with an empty metadata cache")
    parser.add_argument("--preset", "-p", type=str, nargs="?", default="copy", choices=encode_presets,
                        help="Ffmpeg preset to use; use --list-presets to get a list")
    parser.add_argument("--list-presets", "-l", action="store_true",
                        help="List the ffmpeg presets available for encoding")
    parser.add_argument("file", nargs="*", type=str, help="Input video files")
    args = parser.parse_args()
    if args.list_presets:
        print("Available presets:")
        for preset_name, preset in encode_presets.items():
            print(" - {}".format(preset_name))
            print("   {}".format(preset.description))
            print("   ffmpeg arguments: {}".format(" ".join(preset.ffmpeg_params)))
            print("   concatenation method: {}".format("concat protocol" if preset.concat_strategy else "concat filter"))
            print()
        sys.exit(0)
    if not args.no_cache and not args.renew_cache:
        cache = load_cache()
    else:
        cache = {}
    file_info = {}
    files = args.file
    if platform.system() == "Windows":
        files = [f for p in args.file for f in glob.glob(p)]
    files = [str(Path(f).resolve()) for f in files]
    meta_description = " and ".join(t for t in ['xlsx', 'txt'] if args.__dict__[t])
    output_description = "perform NO "
    print("concatdv will:")
    print(" - Analyze {} files".format(len(files)))
    print(" - Sort the files by {}".format(args.sort))
    if meta_description:
        print(" - Output metadata as {}".format(meta_description))
    if args.out:
        print(" - Concatenate and/or encode everything using preset '{}' and write output to '{}'".format(args.preset,
                                                                                                          args.out))
    file_info = cache["file_info"] if "file_info" in cache else {}
    files_analyzed = 0
    for file in files:
        print("Analyzing {} ... ".format(file), end='', flush=True)
        if file in file_info:
            print("cached")
        else:
            file_info[file] = get_info(file)
            print("done")
            files_analyzed += 1
            if not args.no_cache and not args.no_periodic_cache_save and files_analyzed % 100 == 0:
                print("Analyzed {} files, saving cache.".format(files_analyzed))
                cache["file_info"] = file_info
                save_cache(cache)
    cache["file_info"] = file_info
    if not args.no_cache:
        save_cache(cache)
    if args.sort == "name":
        files = list(sorted(files, key=basename))
    elif args.sort == "time":
        files = list(sorted(files, key=lambda f: file_info[f]["datetime"] if "datetime" in file_info[
            f] else datetime.datetime.fromtimestamp(0)))
    if not args.no_xlsx:
        xlsx = replace_extension(args.out, "xlsx") if args.out and not args.xlsx else args.xlsx
        if xlsx:
            print("Writing XLSX report {} ... ".format(xlsx), end='', flush=True)
            write_xlsx_report(xlsx, files, file_info)
            print("done")
    if not args.no_txt:
        txt = replace_extension(args.out, "txt") if args.out and not args.txt else args.txt
        if txt:
            print("Writing TXT report {} ... ".format(txt), end='', flush=True)
            write_txt_report(txt, files, file_info)
            print("done")
    if args.out:
        print("Starting concatenation process ... ")
        do_concatenation(files, args.out, encode_presets[args.preset])
    print("Done.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted by user.")
        sys.exit(-100)
