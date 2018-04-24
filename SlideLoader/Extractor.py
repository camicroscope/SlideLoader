import openslide, time, hashlib
# get slide metadata. look at openslide

"""
Extractor: Generates slide metadata and thumbnails
Can be used for thumbnail generation, metadata loading, or both.

Args:
    config (dict): configuration dictionary, possibly from Config

Designed to be runnable multithreaded via .metadata (or .thumbnail) which works on one slide (per call)

.metadata returns a dictionary of extracted metadata
if thumbnail_size is set, it also generates a thumbnail

Config variables used:
    thumbnail_size (dict): the max dimension of the output thumbnail, absent or none to skip thumbnail generation
    thumbnail_path (str): the relative path for thumbnails, if applicable
"""
class Extractor(object):
    def __init__(self, config):
        self.config = config
        # relevant sections
        self.thumbnail_size = self.config.get("thumbnail_size", None)
        self.thumbnail_path = self.config.get("thumbnail_path", "./")

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

    def metadata(self, filename):
        metadata = {}
        slideData = openslide.OpenSlide(filename)
        metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
        metadata['mpp-y'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
        # metadata['height'] = slideData.get("openslide.level[0].height", None)
        # metadata['width'] = slideData.get("openslide.level[0].width", None)
        metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
        metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
        metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
        metadata['level_count'] = int(slideData.get('level_count', 1))
        metadata['objective'] = float(slideData.get("aperio.AppMag", None))
        metadata['md5sum'] = self._md5(filename)
        metadata['timestamp'] = time.time()
        if self.thumbnail_size:
            self.gen_thumbnail(filename, slideData)
        # TODO sanity check
        return metadata

    def gen_thumbnail(self, filename, slideData, size, imgtype="png"):
        dest = thumbnail_path + "/" + filename + "." + imgtype
        slideData.get_thumbnail(size).save(dest, imgtype.upper())
