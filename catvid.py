import argparse
import glob
import logging
import platform

from pathlib import Path
from appdirs import *

from metacache import MetaCache
from mediatools import encode_presets, MediaTools, MediaToolsNotInstalledException, FileList
from report import write_txt_report, write_xlsx_report

log = logging.getLogger(__name__)


def replace_extension(path, new_ext):
    return os.path.splitext(path)[0] + "." + new_ext


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
    parser.add_argument("--out", "-o", type=str, help="Output filename to write to")
    parser.add_argument("--no-cache", action="store_true", help="Don't use the metadata cache")
    parser.add_argument("--no-periodic-cache-save", action="store_true",
                        help="Stop saving the cache every 100 files (might help with extreme amounts of small files)")
    parser.add_argument("--renew-cache", action="store_true", help="Start with an empty metadata cache")
    parser.add_argument("--preset", "-p", type=str, nargs="?", default="copy", choices=encode_presets,
                        help="Ffmpeg preset to use; use --list-presets to get a list. Default: copy")
    parser.add_argument("--list-presets", "-l", action="store_true",
                        help="List the ffmpeg presets available for encoding")
    parser.add_argument("file", nargs="*", type=str, help="Input video files")
    args = parser.parse_args()

    logging.basicConfig(format="%(message)s", level=logging.DEBUG if args.verbose else logging.INFO)

    if args.list_presets:
        print("Available presets:")
        for preset_name, preset in encode_presets.items():
            print(" - {}".format(preset_name))
            print("   {}".format(preset.description))
            print("   ffmpeg arguments: {}".format(" ".join(preset.ffmpeg_params)))
            print("   concatenation method: {}".format("concat protocol" if preset.concat_strategy else "concat filter"))
            print()
        sys.exit(0)
    elif not args.file:
        parser.print_help()
        sys.exit(0)

    if not args.no_cache and not args.renew_cache:
        cache.load()

    files = args.file
    if platform.system() == "Windows":
        files = [f for p in args.file for f in glob.glob(p)]

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

    if not args.no_xlsx:
        xlsx = replace_extension(args.out, "xlsx") if args.out and not args.xlsx else args.xlsx
        if xlsx:
            log.info("Writing XLSX report %s", xlsx)
            write_xlsx_report(xlsx, file_list)

    if not args.no_txt:
        txt = replace_extension(args.out, "txt") if args.out and not args.txt else args.txt
        if txt:
            log.info("Writing TXT report %s", txt)
            write_txt_report(txt, file_list)

    if args.out:
        log.info("Starting concatenation")
        tools.do_concatenation(files, args.out, encode_presets[args.preset])

    log.info("Done.")


if __name__ == '__main__':
    try:
        main()
    except MediaToolsNotInstalledException as e:
        log.error("%s", str(e))
        sys.exit(-1)
    except KeyboardInterrupt:
        print("Aborted by user.")
        sys.exit(-2)
    except OSError as e:
        log.error("%s", str(e))

