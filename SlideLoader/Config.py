import yaml

"""
Config:
Reads a configuration file for slide loading.

Args:
    filepath (str): the path of the configuration type
    filetype (str): the parsing engine to use, default yaml

Run with .read() to get a dictionary of configuration variables.
"""
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
