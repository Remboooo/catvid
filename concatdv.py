import argparse
import datetime
import re
import subprocess
from os.path import basename
import xlsxwriter

duration_match = re.compile(r'\d\d:\d\d:\d\d.\d\d\d')


def get_info(file):
    result = subprocess.run(["mediainfo", "--fullscan", file], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf8')
    info = {}
    for line in output.splitlines():
        if line.startswith("Recorded date"):
            if 'datetime' not in info:
                info['datetime'] = datetime.datetime.strptime(line.split(": ", 1)[1], '%Y-%m-%d %H:%M:%S.000')
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
            txt.write("  Record date/time    : {}\n".format(info['datetime'].strftime('%Y-%m-%d %H:%M:%S')))
            txt.write("  Duration (mm:ss.ms) : {}\n".format(ms_to_mm_ss_ms(info['milliseconds'])))
            txt.write("  Duration (ms)       : {}\n".format(info['milliseconds']))
            txt.write("  Duration (frames)   : {}\n".format(info['frames']))
            txt.write("  Source filename     : {}\n".format(basename(file)))
            txt.write("\n")

            offset_ms += info['milliseconds']
            offset_frames += info['frames']
            scene += 1


def write_xlsx_report(xlsx, files, file_info):
    with xlsxwriter.Workbook(xlsx) as workbook:
        sheet = workbook.add_worksheet()
        int_fmt = workbook.add_format({'num_format': '0', 'align': 'left'})
        bold_fmt = workbook.add_format({'bold': True, 'align': 'left'})
        datetime_fmt = workbook.add_format({'num_format': 'yyyy-dd-mm hh:mm:ss', 'align': 'left'})

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
            sheet.write_datetime(row, 3, info['datetime'], datetime_fmt)
            sheet.write(row, 4, ms_to_mm_ss_ms(info['milliseconds']))
            sheet.write(row, 5, info['milliseconds'], int_fmt)
            sheet.write(row, 6, info['frames'], int_fmt)
            sheet.write(row, 7, basename(file))

            offset_ms += info['milliseconds']
            offset_frames += info['frames']

            row += 1


def do_concatenation(files, output):
    files_arg = "concat:{}".format('|'.join(files))
    subprocess.run(["avconv", "-i", files_arg, "-c", "copy", output])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Concatenate miniDV-sourced AVI scene files and export date/time info of the output to XLSX/TXT")
    parser.add_argument("--sorted", action="store_true", help="Sort files by filename before concatenating")
    parser.add_argument("--xlsx", type=str, help="File to write XLSX information to")
    parser.add_argument("--txt", type=str, help="File to write plain text information to")
    parser.add_argument("outfile", type=str, help="Output AVI file to write")
    parser.add_argument("file", nargs="+", type=str, help="AVI input files")
    args = parser.parse_args()

    file_info = {}

    files = args.file

    if args.sorted:
        files = list(sorted(files, key=basename))

    for file in files:
        print("Analyzing {} ... ".format(file), end='', flush=True)
        file_info[file] = get_info(file)
        print("done")

    if args.xlsx:
        print("Writing XLSX report {} ... ".format(args.xlsx))
        write_xlsx_report(args.xlsx, files, file_info)
        print("done")

    if args.txt:
        print("Writing TXT report {} ... ".format(args.txt))
        write_txt_report(args.txt, files, file_info)
        print("done")

    print("Starting concatenation process")
    do_concatenation(files, args.outfile)
    print("Done.")
