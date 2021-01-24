import argparse
import glob
import json
import logging
import platform

from pathlib import Path
from appdirs import *

from metacache import MetaCache
from mediatools import encode_presets, MediaTools, MediaToolsNotInstalledException, FileList
from report import write_txt_report, write_xlsx_report, write_srt
from util import confirm_overwrite

log = logging.getLogger(__name__)


class UserInputException(Exception):
    pass


def replace_extension(path, new_ext):
    return os.path.splitext(path)[0] + "." + new_ext


def absolute_from_maybe_relative(path, relative_to_file):
    if os.path.isabs(path):
        return path
    else:
        return os.path.join(os.path.dirname(relative_to_file), path)


def relative_to_or_absolute(path, relative_to_file):
    try:
        return os.path.relpath(path, os.path.dirname(relative_to_file))
    except ValueError:
        return os.path.abspath(path)


def main():
    tools = MediaTools()
    cache = MetaCache()

    parser = argparse.ArgumentParser(
        description="Concatenate similar (e.g. camera scene) video files "
                    "and export date/time info of the output to XLSX/TXT")

    parser.add_argument("--verbose", "-v", action="store_true", help="Activate verbose mode (debug logging)")
    parser.add_argument("--sort", choices=['name', 'time', 'path', 'none'], default='time',
                        help="Sort files by given criterion. "
                             "name: Sort by filename. "
                             "path: Sort by file path. "
                             "time: Sort by recorded date/time (DEFAULT). "
                             "none: Sort as given in argument list.")

    parser.add_argument("--xlsx", "-x", type=str, help="File to write XLSX metadata to. Default is next to --out.")
    parser.add_argument("--no-xlsx", "-X", action='store_true', help="Disable XLSX metadata writing.")

    parser.add_argument("--txt", "-t", type=str, help="File to write plain text metadata to. Default is next to --out.")
    parser.add_argument("--no-txt", "-T", action='store_true', help="Disable plain text metadata writing.")

    parser.add_argument("--collection", "-c", type=str, metavar="CVC",
                        help="File to write a collection specification to, such that a later run can use the "
                             "same file ordering (but e.g. different encoding) using -i. "
                             "Default is next to --out.")
    parser.add_argument("--no-collection", "-C", action='store_true', help="Disable writing of a collection file.")
    parser.add_argument("--in-collection", "-i", type=str, metavar="CVC",
                        help="Collection file to use as input file list. "
                             "Cannot be combined with command-line specified input files.")

    parser.add_argument("--log", "-l", metavar="LOGFILE", type=str,
                        help="Logfile to write ffmpeg output to when creating output video file. "
                             "Default is next to --out.")
    parser.add_argument("--no-log", "-L", action="store_true", help="Disable writing of log file.")

    parser.add_argument("--srt", "-s", metavar="SUBSFILE", type=str,
                        help="File to write SRT 'subtitles' to, which just briefly flashes the recording date at the "
                             "start of each new video file. Default is next to --out.")
    parser.add_argument("--no-srt", "-S", action="store_true", help="Disable writing of SRT subtitles files.")

    parser.add_argument("--out", "-o", metavar="FILE", type=str, help="Output video filename to write to")

    parser.add_argument("--no-cache", action="store_true", help="Don't use the metadata cache")
    parser.add_argument("--no-periodic-cache-save", action="store_true",
                        help="Stop saving the cache every 100 files (might help with extreme amounts of small files)")
    parser.add_argument("--renew-cache", action="store_true", help="Start with an empty metadata cache")

    parser.add_argument("--preset", "-p", type=str, nargs="?", default="copy", choices=encode_presets,
                        help="Ffmpeg preset to use; use --list-presets to get a list. Default: copy")
    parser.add_argument("--list-presets", "-P", action="store_true",
                        help="List the ffmpeg presets available for encoding")

    parser.add_argument("--overwrite", "-y", action="store_true", help="Don't ask before overwriting existing files.")

    parser.add_argument("file", nargs="*", type=str, help="Input video files")

    args = parser.parse_args()

    logging.basicConfig(format="%(message)s", level=logging.DEBUG if args.verbose else logging.INFO, stream=sys.stdout)

    if args.list_presets:
        print("Available presets:")
        for preset_name, preset in encode_presets.items():
            print(" - {}".format(preset_name))
            print("   {}".format(preset.description))
            print("   ffmpeg arguments: {}".format(" ".join(preset.ffmpeg_params)))
            print("   concatenation method: {}".format("concat protocol" if preset.concat_strategy else "concat filter"))
            print()
        sys.exit(0)
    elif not args.file and not args.in_collection:
        print("Must specify at least one input file or collection (--in-collection)")
        parser.print_help()
        sys.exit(0)

    if not args.no_cache and not args.renew_cache:
        cache.load()

    xlsx = get_meta_out_file(args.xlsx, args.no_xlsx, args.overwrite, args.out, "xlsx")
    txt = get_meta_out_file(args.txt, args.no_txt, args.overwrite, args.out, "txt")
    cvc = get_meta_out_file(args.collection, args.no_collection, args.overwrite, args.out, "cvc")
    srt = get_meta_out_file(args.srt, args.no_srt, args.overwrite, args.out, "srt")

    out_path = None
    logfile = None
    if args.out:
        out_path = os.path.abspath(args.out)
        if not args.overwrite:
            confirm_overwrite(out_path)

        logfile = get_meta_out_file(args.log, args.no_log, args.overwrite, args.out, "log")

    if args.file and args.in_collection:
        raise UserInputException("Specifying both input collection file and separate input video files is not supported")
    elif args.file:
        files = args.file
        if platform.system() == "Windows":
            files = [f for p in args.file for f in glob.glob(p)]
    elif args.in_collection:
        with open(args.in_collection, 'r') as f:
            files = [absolute_from_maybe_relative(p, args.in_collection) for p in json.load(f)["files"]]
    else:
        raise UserInputException("Must specify either input collection file, or separate video files")

    files = [str(Path(f).resolve()) for f in files]

    meta_description = " and ".join(t for t in ['xlsx', 'txt'] if args.__dict__[t])

    log.info("concatdv will:")
    log.info(" - Analyze %s files", len(files))
    log.info(" - Sort the files by %s", args.sort)
    if meta_description:
        log.info(" - Output metadata as %s", meta_description)
    if args.out:
        log.info(" - Concatenate and/or encode everything using preset '%s' and write output to '%s'",
                 args.preset, args.out)

    file_list = FileList(mediatools=tools, metacache=cache)
    for file_i, file in enumerate(files, 1):
        log.info("Adding %s", file)
        file_list.add_file(file)
        if not args.no_cache and not args.no_periodic_cache_save and file_i % 100 == 0:
            log.info("Analyzed %s files, saving cache.", file_i)
            cache.save()

    if not args.no_cache:
        cache.save()

    if args.sort == "name":
        file_list.sort_by_filename()
    elif args.sort == "path":
        file_list.sort_by_path()
    elif args.sort == "time":
        file_list.sort_by_datetime()

    if cvc:
        log.info("Writing catvid collection %s", cvc)
        with open(cvc, 'w') as f:
            json.dump({"files": [relative_to_or_absolute(p, cvc) for p in files]}, f)

    if xlsx:
        log.info("Writing XLSX report %s", xlsx)
        write_xlsx_report(xlsx, file_list)

    if txt:
        log.info("Writing TXT report %s", txt)
        write_txt_report(txt, file_list)

    if srt:
        log.info("Writing SRT subtitles %s", srt)
        write_srt(srt, file_list)

    if out_path:
        log.info("Starting concatenation")
        tools.do_concatenation(file_list, out_path, encode_presets[args.preset], logfile)

    log.info("Done.")


def get_meta_out_file(arg, disable_arg, overwrite_arg, out_path, ext):
    path = None
    if not disable_arg:
        path = replace_extension(out_path, ext) if out_path and not arg else arg
        if path and not overwrite_arg:
            confirm_overwrite(path)
    return path


if __name__ == '__main__':
    try:
        main()
    except (MediaToolsNotInstalledException, UserInputException, FileExistsError, OSError) as e:
        log.error("%s", str(e))
        sys.exit(-1)
    except KeyboardInterrupt:
        print("Aborted by user.")
        sys.exit(-2)

