import xlsxwriter

from util import ms_to_mm_ss_ms


def write_txt_report(txt_file, file_list):
    with open(txt_file, 'w') as txt:
        offset_ms = 0
        offset_frames = 0

        for scene, file in enumerate(file_list.paths, 1):
            info = file_list.meta[file]

            txt.write("Scene {:d}\n".format(scene))
            txt.write("  Offset (mm:ss.ms)   : {}\n".format(ms_to_mm_ss_ms(offset_ms)))
            txt.write("  Offset (ms)         : {}\n".format(offset_ms))
            txt.write("  Offset (frames)     : {}\n".format(offset_frames))
            txt.write("  Record date/time    : {}\n".format(info.datetime.strftime('%Y-%m-%d %H:%M:%S') if info.datetime else 'UNKNOWN'))
            txt.write("  Duration (mm:ss.ms) : {}\n".format(ms_to_mm_ss_ms(info.milliseconds) if info.milliseconds else 'UNKNOWN'))
            txt.write("  Duration (ms)       : {}\n".format(info.milliseconds if info.milliseconds else 'UNKNOWN'))
            txt.write("  Duration (frames)   : {}\n".format(info.frames if info.frames else 'UNKNOWN'))
            txt.write("  Source filename     : {}\n".format(file))
            txt.write("\n")

            if info.milliseconds:
                offset_ms += info.milliseconds
            if info.frames:
                offset_frames += info.frames


def write_srt(path, file_list, time_fmt='%Y-%m-%d %H:%M:%S', duration=5):
    def srt_duration(ms):
        hours = ms // 3600_000
        minutes = (ms // 60_000) % 60
        seconds = (ms // 1000) % 60
        millis = ms % 1000
        return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, millis)

    with open(path, 'w') as srt:
        offset_ms = 0

        for scene, file in enumerate(file_list.paths, 1):
            info = file_list.meta[file]

            if info.datetime:
                srt.write(f"{scene:d}\r\n")
                srt.write(f"{srt_duration(offset_ms)} --> {srt_duration(offset_ms + 1000*duration)}\r\n")
                srt.write(f"{info.datetime.strftime(time_fmt)}\r\n")
                srt.write("\r\n")

            if info.milliseconds:
                offset_ms += info.milliseconds


def write_xlsx_report(xlsx, file_list):
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

        offset_ms = 0
        offset_frames = 0

        for row, file in enumerate(file_list.paths, 1):
            info = file_list.meta[file]

            sheet.write(row, 0, ms_to_mm_ss_ms(offset_ms))
            sheet.write(row, 1, offset_ms, int_fmt)
            sheet.write(row, 2, offset_frames, int_fmt)
            if info.datetime:
                sheet.write_datetime(row, 3, info.datetime, datetime_fmt)
            if info.milliseconds:
                sheet.write(row, 4, ms_to_mm_ss_ms(info.milliseconds))
                sheet.write(row, 5, info.milliseconds, int_fmt)
            if info.frames:
                sheet.write(row, 6, info.frames, int_fmt)
            sheet.write(row, 7, file)

            if info.milliseconds:
                offset_ms += info.milliseconds
            if info.frames:
                offset_frames += info.frames
