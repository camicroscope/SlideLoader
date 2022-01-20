import csv
import subprocess
import time
from multiprocessing.pool import ThreadPool

import openslide

from dev_utils import file_md5
from dev_utils import postslide
from dev_utils import post_url

# GLOBALS (for now)
# config = {'thumbnail_size': 100, 'thread_limit': 20}
config = { 'thread_limit': 20}
manifest_path = 'manifest.csv'
# NCI DOE added flat file START
flat_file_path = 'flat_file.csv'
apiKey = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyVHlwZSI6IkFkbWluIiwidXNlckZpbHRlciI6WyJQdWJsaWMiXSwic3ViIjoibGluYW5sZGpAZ21haWwuY29tIiwiZW1haWwiOiJsaW5hbmxkakBnbWFpbC5jb20iLCJuYW1lIjoiTmFuIExpIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hLS9BT2gxNEdpRnBfRlRFYWxGbmlzclcwQzF6NDFPbW1wZS1uTTd0Wkx4SXRNbE9nPXM5Ni1jIiwiaWF0IjoxNjM0ODQ0MjQ5LCJleHAiOjE2MzQ5MzA2NDl9.oRDeM_i1i4fQB3wlVmodAF4NG_umCZL2DIObWYMCviJwWXPAfNDtyMEY2GwMzgeMcQNPjIbDem6mhuDvhyOSmQc0J5lpxJpZYCVKnOQ95Q2rNy1F9gQjpuJ_vfIKRoakH9lE_W3leg8ff-zvUbgpOyzQxEg4louUGGpqG_5FVQnHG88CGAzzG7MvCb6wuyDrRvhxGBIRicjFN_zj8ZeXzmXD7U9KhOgKAW21XWhL4RyBhQyq8CORPx23omRKk7u72oTY5dlfzHj6O9Ll92MqJQEF1Xz08nVLlSMSw7pTKmmGWkK2DUKsp9sRvc2uFXButUpIrvaqh1ukCV6HU0hGIg'
# NCI DOE added flat file END

# process expects a single image metadata as dictionary
def process(img):
    try:
        img = openslidedata(img)
        img['study'] = img.get('study', "")
        img['specimen'] = img.get('specimen', "")
        img['location'] = img['location'] or img['filename']
        img = postslide(img, post_url, apiKey)
        print('process img:')
        print(img)
    except BaseException as e:
        img['_status'] = e
    return img


def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = filename + "." + imgtype
    
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())


def openslidedata(metadata):
    slide = openslide.OpenSlide(metadata['location'])
    slideData = slide.properties
    metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
    metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
    metadata['mpp'] = metadata['mpp-x'] or metadata['mpp-x'] or None
    metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
    metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
    metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
    metadata['comment'] = slideData.get(openslide.PROPERTY_NAME_COMMENT, None)
    metadata['level_count'] = int(slideData.get('level_count', 1))
    metadata['objective'] = float(slideData.get("aperio.AppMag", 0.0))
    metadata['md5sum'] = file_md5(metadata['location'])
    
    # NCI DOE metadata START
    if metadata['height'] is None:
        metadata['height'] = slideData.get('aperio.OriginalHeight', None)
    if metadata['height'] is None:
        metadata['height'] = slideData.get('openslide.level[0].height', None)
    if metadata['width'] is None:
        metadata['width'] = slideData.get('aperio.OriginalWidth', None)
    if metadata['width'] is None:
        metadata['width'] = slideData.get('openslide.level[0].width', None)
    metadata['token_id'] = slideData.get('aperio.CustomField.TokenID', None)
    metadata['proc_seq'] = slideData.get('aperio.CustomField.Proc_Seq', None)
    metadata['spec_site'] = slideData.get('aperio.CustomField.Spec_Site', None)
    metadata['image_id'] = slideData.get('aperio.CustomField.ImageID', None)    
    flat_matedata = flat_map[metadata['token_id'].lower()]

    metadata['registry_code'] = flat_matedata.get('registry',None)
    metadata['primary_tumor_site_code'] =  flat_matedata.get('primary_site',None)
    metadata['primary_tumor_site_term'] =  flat_matedata.get('site_text',None)
    metadata['morphology_code'] =  flat_matedata.get('histology_icdo3',None)
    metadata['seer_coded_histology'] =  flat_matedata.get('hist_text',None)
    metadata['behavior_code'] =  flat_matedata.get('behavior_icdo3',None)

    metadata['timestamp'] = time.time()
    # NCI DOE metadata END
    thumbnail_size = config.get('thumbnail_size', None)
    if thumbnail_size:
        gen_thumbnail(metadata['location'], slide, thumbnail_size)
    return metadata


# NCI DOE create a metadata dict START
flat_map = {}
# get flat file and create dict as map [tokenId, data]
with open(flat_file_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        flat_map[row['tokenid'].lower()] = row
# NCI DOE create a metadata dict END

# get manifest
with open(manifest_path, 'r') as f:
    reader = csv.DictReader(f)
    manifest = [row for row in reader]
    thread_limit = config.get('thread_limit', 10)
    # run process on each image
    res = ThreadPool(thread_limit).imap_unordered(process, manifest)
    print([r for r in res])
