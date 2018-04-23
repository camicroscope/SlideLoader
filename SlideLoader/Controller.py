from multiprocessing.pool import ThreadPool

# results = ThreadPool(limit).imap_unordered(*function*, *list*)

class Controller(object):
    # get options
    # get converted file
    # run converted manifest through extractor
    # call threads per each file in manifest
    # ? if a thread fails, relaunch its data, else log
