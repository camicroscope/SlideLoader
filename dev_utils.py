import hashlib
import os
import json
import requests

import openslide

post_url = "http://ca-back:4010/data/Slide/post"



# given a path, get metadata
def getMetadata(filepath, extended, raise_exception):
    # TODO consider restricting filepath
    metadata = {}
    if not os.path.isfile(filepath):
        if raise_exception:
            raise ValueError("No such file")
        msg = {"error": "No such file"}
        print(msg)
        return msg
    metadata['location'] = filepath
    try:
        slide = openslide.OpenSlide(filepath)
    except BaseException as e:
        if raise_exception:
            raise e
        msg = {"type": "Openslide", "error": str(e)}
        print(msg)
        return msg
    slideData = slide.properties
    if extended:
        return {k:v for (k,v) in slideData.items()}
    else:
        metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
        metadata['mpp-y'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
        metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None) or slideData.get(
            "openslide.level[0].height", None)
        metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None) or slideData.get(
            "openslide.level[0].width", None)
        metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
        metadata['level_count'] = int(slide.level_count)
        metadata['objective'] = float(slideData.get(openslide.PROPERTY_NAME_OBJECTIVE_POWER, 0) or
                                      slideData.get("aperio.AppMag", -1.0))
        metadata['md5sum'] = file_md5(filepath)
        metadata['comment'] = slideData.get(openslide.PROPERTY_NAME_COMMENT, None)
        metadata['study'] = ""
        metadata['specimen'] = ""
        return metadata


def postslide(img, url, token=''):
    if token != '':
        url = url + '?token='+token
    payload = json.dumps(img)
    res = requests.post(url, data=payload, headers={'content-type': 'application/json'})
    if res.status_code < 300:
        img['_status'] = 'success'
    else:
        img['_status'] = str(res.status_code)
    print('status ' + img['_status'])
    return img


# given a list of path, get metadata for each
def getMetadataList(filenames, extended, raise_exception):
    allData = []
    for filename in filenames:
        allData.append(getMetadata(filename, extended, raise_exception))
    return allData


def file_md5(fileName):
    m = hashlib.md5()
    blocksize = 2 ** 20
    with open(fileName, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()


def hello():
    print('hello!')
