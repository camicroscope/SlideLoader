import openslide, time, hashlib
# get slide metadata. look at openslide


class Extractor(object):
    def __init__(self, filename):
        self.filename = filename

    def _md5(self):
        m = hashlib.md5()
        blocksize = 2**20
        with open(self.fileName, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                m.update(buf)
        return m.hexdigest()
    # given dict of slide info from reader
    # return something a thread can nicely use to do requests

    def metadata(self):
        metadata = {}
        slideData = openslide.OpenSlide(self.filename)
        metadata['mpp-x'] = slideData.get("tiff.XResolution", None)
        metadata['mpp-y'] = slideData.get("tiff.YResolution", None)
        metadata['height'] = slideData.get("openslide.level[0].height", None)
        metadata['width'] = slideData.get("openslide.level[0].width", None)
        metadata['vendor'] = slideData.get("openslide.vendor", None)
        metadata['level_count'] = int(slideData.get('level_count', 1))
        metadata['objective'] = float(slideData.get("aperio.AppMag", None))
        metadata['md5sum'] = self._md5()
        metadata['timestamp'] = time.time()
        # TODO sanity check
        return metadata
