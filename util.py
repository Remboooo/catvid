import os

overwrite_all = False


def confirm_overwrite(path):
    global overwrite_all
    if os.path.exists(path) and not overwrite_all:
        answer = input(f"File '{path}' already exists. Overwrite (y(es)/a(ll)/N(o))? ").lower()
        if answer.startswith("y"):
            return True
        elif answer.startswith("a"):
            overwrite_all = True
            return True
        else:
            raise FileExistsError(f"File '{path}' already exists.")
    return True


def open_if_exists(file, mode='r'):
    if file:
        return open(file, mode=mode)
    else:
        class DummyOpener:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass


def ms_to_mm_ss_ms(ms):
    minutes = ms // 60000
    seconds = (ms // 1000) % 60
    millis = ms % 1000
    return "{:02d}:{:02d}.{:03d}".format(minutes, seconds, millis)
