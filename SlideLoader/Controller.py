from multiprocessing.pool import ThreadPool

class Controller(object):
    def __init__(self, cnf_file, manifest_file):
        self.config = Config(cnf_file).read()
        self.extractor = Extractor(self.config)
        self.reader = Reader(manifest_file, self.config)
        self.requester = Requester(self.config)
        # relevant config variables
        self.fileKey = self.config.get("local_file_field", "file")
        self.threadLimit = self.config.get("thread_limit", 20)
        self.globals = self.config.get("globals", {})

    def _run_one(self, record):
        # TODO note the order of this merge in doc
        # metadata is overwritten by manifest, both overwritten by globals in config
        payLoad = self.extractor.extract(record[self.fileKey])
        payLoad.update(record)
        payLoad.update(self.globals)
        return self.requester.request(payLoad)

    def run(self):
        results = ThreadPool(self.threadLimit).imap_unordered(self._run_one, self.reader.read())
