import csv
import json
# convert the file to a list of dicts

class Reader(object):
    def __init__(self, path, filetype="csv"):
        self.path = path
        self.filetype = filetype.lower()

    def read(self):
        with open(self.path, 'r') as f:
            if self.filetype == "csv":
                reader = csv.DictReader(f)
                return [row for row in reader]
            elif self.filetype == "json":
                data = json.load(f)
        else:
            raise TypeError(self.filetype + " type not supported for manifests")
