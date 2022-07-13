import requests
import openslide
import pycurl
from multiprocessing.pool import ThreadPool

SLIDE_LIST_URL = "http://ca-back:4010/data/Slide/find"
IIP_BASE = "http://ca-back:4010/img/IIP/raw/?FIF="
# TODO -- token input?
IM_SIZE = 256
THREADS = 5
REGNERATE = False
SAVE_DIR = "./images/thumbnails/"

def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = SAVE_DIR + filename + "." + imgtype
    print(dest)
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())

def process(record):
    file = record["location"]
    name = record["name"]
    # skip ones which already have a thumbnail, unless otherwise specified
    if not REGNERATE and not record["thumbnail"]:
        try:
            slide = openslide.OpenSlide(file)
            gen_thumbnail(name, slide, IM_SIZE, imgtype="png")
            return ""
        except BaseException as e:
            try:
                 url = IIP_BASE + file + "&WID=200&CVT=png"
                 c = pycurl.Curl()
                 c.setopt(c.URL, url)
                 with open(SAVE_DIR+name+".png", "wb") as f:
                     c.setopt(c.WRITEFUNCTION, f.write)
                     c.perform()
            except BaseException as y:
                 return [name, y]

# do it
manifest = requests.get(SLIDE_LIST_URL).json()
print(manifest[0])

res = ThreadPool(THREADS).imap_unordered(process, manifest)
print([x for x in filter(None,[r for r in res])])
