import openslide, time, hashlib
# get slide metadata. look at openslide


class Extractor(object):
    def __init__(self, config):
        self.config = config
        # relevant sections
        self.fileKey

    def _md5(self, filename):
        m = hashlib.md5()
        blocksize = 2**20
        with open(fileName, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                m.update(buf)
        return m.hexdigest()

    def metadata(self, record):
        metadata = {}
        slideData = openslide.OpenSlide(filename)
        metadata['mpp-x'] = slideData.get("tiff.XResolution", None)
        metadata['mpp-y'] = slideData.get("tiff.YResolution", None)
        metadata['height'] = slideData.get("openslide.level[0].height", None)
        metadata['width'] = slideData.get("openslide.level[0].width", None)
        metadata['vendor'] = slideData.get("openslide.vendor", None)
        metadata['level_count'] = int(slideData.get('level_count', 1))
        metadata['objective'] = float(slideData.get("aperio.AppMag", None))
        metadata['md5sum'] = self._md5(filename)
        metadata['timestamp'] = time.time()
        # TODO sanity check
        return metadata
