import openslide
# get slide metadata. look at openslide


class Extractor(object):
    def __init__(self, filename):
        self.filename = filename

    def _md5(self,fileName):
        m = hashlib.md5()
        blocksize = 2**20
        with open(fileName, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                m.update(buf)
        return m.hexdigest()
    # given dict of slide info from reader
    # return something a thread can nicely use to do requests

    openslide.OpenSlide(self.filename)
    # what do we need from openslide?
    """    {
    	"_id" : ObjectId("5aaaa40ae4b094e3adb0527b"),
    	"mpp-x" : 0.499,
    	"height" : 32893,
    	"mpp-y" : 0.499,
    	"filename" : "/data/images/CMU-1-JP2K-33005-274ju.svs",
    	"level_count" : 3,
    	"timestamp" : 1521132552.9331686,
    	"subject_id" : "CMU1jp2k",
    	"md5sum" : "b08f34f9d16c49e2c4a5bc91c4597fd1",
    	"file-location" : "/data/images/CMU-1-JP2K-33005-274ju.svs",
    	"mpp_y" : 0.499,
    	"case_id" : "CMU1jp2k",
    	"mpp_x" : 0.499,
    	"width" : 46000,
    	"objective" : 20,
    	"study_id" : "default",
    	"vendor" : "aperio"
    }"""
