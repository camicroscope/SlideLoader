import hashlib
import os
import json
import requests
import image_reader
import threading

post_url = "http://ca-back:4010/data/Slide/post"



# Keep BioFormats Java thread alive; to minimize reattaching thread
keep_alive_for_thread = threading.local()

# given a path, get metadata
def getMetadata(filepath, extended, raise_exception):
    # TODO consider restricting filepath
    if not os.path.isfile(filepath):
        if raise_exception:
            raise ValueError("No such file")
        msg = {"error": "No such file"}
        print(msg)
        return msg
    try:
        slide = image_reader.construct_reader(filepath)
    except BaseException as e:
        if raise_exception:
            raise e
        # here, e has attribute "error"
        return str(e)

    try:
        metadata = slide.get_basic_metadata(extended)
    except BaseException as e:
        if raise_exception:
            raise e
        return {'error': str(e)}
    metadata['location'] = filepath
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
