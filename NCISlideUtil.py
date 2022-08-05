import csv
import subprocess
import time
from multiprocessing.pool import ThreadPool
import json
import openslide
import os
import requests
from dev_utils import file_md5
from dev_utils import postslide
from dev_utils import post_url

# GLOBALS (for now)
# config = {'thumbnail_size': 100, 'thread_limit': 20}
config = {'thread_limit': 20}
manifest_path = 'manifest.csv'
# NCI DOE added flat file START
collections_path = 'specialties_list.json'
flat_file_path = 'flat_file.csv'

# NCI DOE added flat file END

# process expects a single image metadata as dictionary


def process(img):
    # check slides
    sid = None
    token_id = img['token_id']
    slide_name = img['name']
    res = requests.get(slide_find_url, params={'name': slide_name})
    if res.status_code == 200:
        rs = res.json()
        # the slide doesn't exist
        if len(rs) < 1:
            try:
                img = openslidedata(img)
                img['study'] = img.get('study', "")
                img['specimen'] = img.get('specimen', "")
                img['location'] = img['location'] or img['filename']
                img = postslide(img, post_url)
                res = requests.get(slide_find_url, params={'name': slide_name})
                sid = res.json()[0]['_id']['$oid']
                print('process img:')
                print(img)
            except BaseException as e:
                img['_status'] = e

        else:
            sid = res.json()[0]['_id']['$oid']
            print(sid)
            img['_status'] = 'existed'
        # add slide to collection
        cid = subspecialties_map.get(token_id.lower())
        if sid is not None or cid is not None:
            res = requests.post(add_slide_to_collection_url, data=json.dumps({'cid': cid, 'sids': [sid]}), headers={
                'content-type': 'application/json'})
        return img
    else:
        img['_status'] = res.status_code
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
    metadata['height'] = slideData.get(
        openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
    metadata['width'] = slideData.get(
        openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
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
    metadata['token_id'] = slideData.get(
        'aperio.CustomField.TokenID', metadata['token_id'])
    metadata['proc_seq'] = slideData.get('aperio.CustomField.Proc_Seq', None)
    metadata['spec_site'] = slideData.get('aperio.CustomField.Spec_Site', None)
    metadata['image_id'] = slideData.get('aperio.CustomField.ImageID', None)
    flat_matedata = flat_map[metadata['token_id'].lower()]

    metadata['registry_code'] = flat_matedata.get('registry', None)
    metadata['primary_tumor_site_code'] = flat_matedata.get(
        'primary_site', None)
    metadata['primary_tumor_site_term'] = flat_matedata.get('site_text', None)
    metadata['morphology_code'] = flat_matedata.get('histology_icdo3', None)
    metadata['seer_coded_histology'] = flat_matedata.get('hist_text', None)
    metadata['behavior_code'] = flat_matedata.get('behavior_icdo3', None)

    metadata['timestamp'] = time.time()
    # NCI DOE metadata END
    thumbnail_size = config.get('thumbnail_size', None)
    if thumbnail_size:
        gen_thumbnail(metadata['location'], slide, thumbnail_size)
    return metadata


# NCI DOE create a metadata dict START
flat_map = {}
subspecialties_map = {}
slide_find_url = 'http://ca-back:4010/data/Slide/find'
slide_post_url = 'http://ca-back:4010/data/Slide/post'
collection_find_url = 'http://ca-back:4010/data/Collection/find'
collection_post_url = 'http://ca-back:4010/data/Collection/post'
add_slide_to_collection_url = 'http://ca-back:4010/data/Collection/addSlidesToCollection'


def addSpecialty(data):
    # check specialty exists
    res = requests.get(collection_find_url, params=data)
    if res.status_code == 200:
        rs = res.json()
        # return collection id if exist
        if len(rs) > 0:
            return rs[0]['_id']['$oid']
        # add the new one and return collection id if not exist
        else:
            res = requests.post(collection_post_url, data=json.dumps(data), headers={
                'content-type': 'application/json'})
            return res.json()['ops'][0]['_id']
    else:
        return None


# read the specialty list
if os.path.exists(collections_path):
    with open(collections_path, 'r', encoding='utf-8-sig') as j:
        collections = json.load(j)
        for collection in collections:
            # add specialty
            pid = addSpecialty({'text': collection['specialty']})
            for sub in collection['subspecialties']:
                # add specialty
                cid = addSpecialty(
                    {'text': sub, 'pid': pid})
                # save the token id and collection id as map
                if cid is not None:
                    subspecialties_map[sub.lower()] = cid


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
