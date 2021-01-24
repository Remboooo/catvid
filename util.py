import os


def confirm_overwrite(path):
    if os.path.exists(path):
        answer = input(f"File '{path}' already exists. Overwrite (y/N)?")
        if not answer.lower().startswith("y"):
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
