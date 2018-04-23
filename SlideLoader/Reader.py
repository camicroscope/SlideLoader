import csv, json
# convert the file to a list of dicts

class Reader(object):
    def __init__(self, manifest, config):
        self.path = path
        self.filetype = config.get("filetype", "csv").lower()

    def read(self):
        with open(self.path, 'r') as f:
            if self.filetype == "csv":
                reader = csv.DictReader(f)
                return [row for row in reader]
            elif self.filetype == "json":
                data = json.load(f)
        else:
            raise TypeError(self.filetype + " type not supported for manifests")
