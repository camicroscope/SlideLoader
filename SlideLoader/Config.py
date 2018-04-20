import yaml

class Config(object):
    def __init__(self, filepath, filetype="yaml"):
        self.filepath = filepath
        self.file = open(self.filepath, "r")
        self.filetype = filetype

    def read(self):
        if self.filetype.lower() == "yaml":
            return yaml.load(self.file)
        else:
            raise TypeError(self.filetype + " type not supported for config file")
