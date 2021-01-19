class FileMeta:
    def __init__(self, data=None):
        self.datetime = None
        self.milliseconds = None
        self.frames = None

        if data is not None:
            self.__dict__.update(data)

    def to_dict(self):
        return self.__dict__
