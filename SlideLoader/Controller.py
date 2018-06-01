from multiprocessing.pool import ThreadPool
from SlideLoader import Config, Extractor, Reader, Requester

"""
Controller: Handles processing of slides
Can be used for thumbnail generation, metadata loading, or both.

Args:
    cnf_file (str): the file path of the configuration file
    manifest_file (str): the file path of the manifest (list of images)

Runs multithreaded, where each thread extracts slide metadata, generates thumbnails, and posts results

Config variables used:
    globals (dict): fields to use to replace missing data in the manifest or metadata
    threadLimit (int): the max number of threads in the thread pool
    fileKey (str): the key in the manifest which represents a file's local location
    retry_limit (int): the max number of times to retry failed requests

Beware that dependent classes (may) use other configuration options.

The request sent is based on the information provided from metadata, the manifest, and config globals.
Metadata is overwritten by manifest data, and both are overwritten by globals in config.
"""
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
        self.retry_limit = self.config.get("retry_limit", {})

    def _run_one(self, record):
        try:
            payLoad = self.extractor.metadata(record[self.fileKey])
            payLoad.update(record)
            payLoad.update(self.globals)
            return self.requester.request(payLoad)
        except(BaseException):
            status = "metadata-err"
            return {"status": status, "payLoad": payLoad}


    def _one_thumbnail(self, record):
        return self.extractor.metadata(record[self.fileKey])

    def run(self):
        retry = True
        successful = []
        i = 0
        # initial try
        retry_list = self.reader.read()
        while retry:
            results = ThreadPool(self.threadLimit).imap_unordered(self._run_one, retry_list)
            successful = successful + [res['payLoad'] for res in results if res['status']=="success"]
            retry_list = [res['payLoad'] for res in results if not res['status']=="success"]
            i = i + 1
            retry = i < self.retry_limit and len(retry_list) > 0
        return {"successful": successful, "failed": retry_list}

    def thumbnails(self):
        results = ThreadPool(self.threadLimit).imap_unordered(self._one_thumbnail, self.reader.read())
        return results
