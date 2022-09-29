import requests
import openslide
import pycurl
import os

SLIDE_LIST_URL = "http://ca-back:4010/data/Slide/find"
IIP_BASE = "http://ca-back:4010/img/IIP/raw/?FIF="
UPDATE_URL = "http://ca-back:4010/data/Slide/update"
# TODO -- token input?
IM_SIZE = 256
REGNERATE = True
SAVE_DIR = "/images/thumbnails/"

# make this SAVE_DIR if it does not exist
try:
    os.mkdir(SAVE_DIR)
    print("created thumbnail SAVE_DIR at", SAVE_DIR)
except FileExistsError:
    pass


def setThumb(id, val):
    requests.post(UPDATE_URL + "?_id=" + id, json={'thumbnail': val})

def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = SAVE_DIR + filename + "." + imgtype
    print(dest)
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())

def process(record):
    file = record["location"]
    name = record["name"]
    # skip ones which already have a thumbnail, unless otherwise specified
    if REGNERATE or not record.get("thumbnail", False):
        try:
            slide = openslide.OpenSlide(file)
            gen_thumbnail(name, slide, IM_SIZE, imgtype="png")
            setThumb(record['_id']["$oid"], name+".png")
            return ""
        except BaseException as e:
            try:
                 url = IIP_BASE + file + "&WID=200&CVT=png"
                 c = pycurl.Curl()
                 c.setopt(c.URL, url)
                 with open(SAVE_DIR+name+".png", "wb") as f:
                     c.setopt(c.WRITEFUNCTION, f.write)
                     c.perform()
                     setThumb(record['_id']["$oid"], name+".png")
            except BaseException as y:
                 return [name, y]

def make_thumbnails():
    manifest = requests.get(SLIDE_LIST_URL).json()
    print(manifest[0])
    res = [process(x) for x in manifest]
    print([x for x in filter(None,[r for r in res])])

if __name__ == "__main__":
    make_thumbnails()
