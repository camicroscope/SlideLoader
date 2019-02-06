import csv
import subprocess
import time
from multiprocessing.pool import ThreadPool

import openslide

from dev_utils import file_md5
from dev_utils import postslide
from dev_utils import post_url

# GLOBALS (for now)
config = {'thumbnail_size': 100, 'thread_limit': 20}
check_url = "http://ca-security:4010/data/Slide/find?slide="
manifest_path = 'manifest.csv'


# process expects a single image metadata as dictionary
def process(img):
    if checkslide(img['name'], check_url):
        try:
            img = openslidedata(img)
            img['study'] = img['study'] or ""
            img['specimen'] = img['specimen'] or ""
            img = postslide(img, post_url)
        except BaseException as e:
            img['_status'] = e
    return img


def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = filename + "." + imgtype
    print(dest)
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())


def openslidedata(metadata):
    slide = openslide.OpenSlide(metadata['filename'])
    slideData = slide.properties
    metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
    metadata['mpp-y'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
    # metadata['height'] = slideData.get("openslide.level[0].height", None)
    # metadata['width'] = slideData.get("openslide.level[0].width", None)
    metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
    metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
    metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
    metadata['level_count'] = int(slideData.get('level_count', 1))
    metadata['objective'] = float(slideData.get("aperio.AppMag", None))
    metadata['md5sum'] = file_md5(metadata['filename'])
    metadata['timestamp'] = time.time()
    metadata['study'] = ""
    metadata['specimen'] = ""
    thumbnail_size = config.get('thumbnail_size', None)
    if thumbnail_size:
        gen_thumbnail(metadata['filename'], slide, thumbnail_size)
    return metadata


def checkslide(id, url):
    return subprocess.check_output(["curl", url + id]) == '[]'


# get manifest
with open(manifest_path, 'r') as f:
    reader = csv.DictReader(f)
    manifest = [row for row in reader]
    thread_limit = config.get('thread_limit', 10)
    # run process on each image
    res = ThreadPool(thread_limit).imap_unordered(process, manifest)
    print([r for r in res])
