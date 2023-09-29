import csv
import os
import time
from multiprocessing.pool import ThreadPool

from image_reader import construct_reader

from dev_utils import getMetadata
from dev_utils import postslide
from dev_utils import post_url

# GLOBALS (for now)
config = {'thumbnail_size': 100, 'thread_limit': 20}
manifest_path = 'manifest.csv'
apiKey = '<apiKey>'

# process expects a single image metadata as dictionary
def process(img):
    try:
        img = openslidedata(img)
        img['study'] = img.get('study', "")
        img['specimen'] = img.get('specimen', "")
        img['location'] = img['location'] or img['filename']
        img = postslide(img, post_url, apiKey)
    except BaseException as e:
        img['_status'] = e
    return img


def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = filename + "." + imgtype
    print(dest)
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())


def openslidedata(metadata):
    if not os.path.isfile(metadata['location']):
        raise IOError("No such file")

    slide = construct_reader(metadata['location'])
    metadata_retrieved = slide.get_basic_metadata(False)
    for k, v in metadata_retrieved.items():
        if k not in metadata:
            metadata[k] = v
    metadata['timestamp'] = time.time()
    thumbnail_size = config.get('thumbnail_size', None)
    if thumbnail_size:
        gen_thumbnail(metadata['location'], slide, thumbnail_size)
    return metadata

# get manifest
with open(manifest_path, 'r') as f:
    reader = csv.DictReader(f)
    manifest = [row for row in reader]
    thread_limit = config.get('thread_limit', 10)
    # run process on each image
    res = ThreadPool(thread_limit).imap_unordered(process, manifest)
    print([r for r in res])
