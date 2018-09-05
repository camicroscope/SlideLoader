import openslide, time, hashlib, subprocess, csv, requests, json
from multiprocessing.pool import ThreadPool
# GLOBALS (for now)
config={'thumbnail_size': 100, 'thread_limit': 20}
api_key = "0401fcb9-f513-47c2-aed1-29fd9dab2e24"
check_url = "http://quip-data:9099/services/Camicroscope_DataLoader/DataLoader/query/getFileLocationByIID?api_key=" + api_key + "&TCGAId="
post_url = "http://quip-data:9099/services/Camicroscope_DataLoader/DataLoader/submit/json"
manifest_path='manifest.csv'


'''process expects a single image metadata as dictionary'''
def process(img):
    if checkslide(img['case_id'], check_url):
        try:
            img = openslidedata(img)
            img = postslide(img, post_url)
        except BaseException as e:
            img['_status'] = e
    return img

def file_md5(fileName):
    m = hashlib.md5()
    blocksize = 2**20
    with open(fileName, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()

def gen_thumbnail(filename, slide, size, imgtype="png"):
        dest =  filename + "." + imgtype
        print(dest)
        slide.get_thumbnail([size,size]).save(dest, imgtype.upper())

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
    thumbnail_size = config.get('thumbnail_size', None)
    if thumbnail_size:
        gen_thumbnail(metadata['filename'], slide, thumbnail_size)
    return metadata

def postslide(img, url):
    payload = json.dumps(img)
    res = requests.post(url, data=payload, headers={'content-type': 'application/json', 'api_key': api_key})
    if (res.status_code<300):
        img['_status'] = 'success'
    else:
        img['_status'] = res.status_code
    return img

def checkslide(id, url):
    return subprocess.check_output(["curl", url+id]) == '[]'

#get manifest
with open(manifest_path, 'r') as f:
    reader = csv.DictReader(f)
    manifest = [row for row in reader]
    thread_limit = config.get('thread_limit', 10)
    # run process on each image
    res = ThreadPool(thread_limit).imap_unordered(process, manifest)
    print(json.dumps([r for r in res]))
