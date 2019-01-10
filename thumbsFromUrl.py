import requests
import openslide
from multiprocessing.pool import ThreadPool

FILE_FIELD = "file-location"
NAME_FIELD = "case_id"
URL = "http://172.20.11.223:9099/services/Camic_TCIA/Image/query/find"
IM_SIZE = 200
THREADS = 10

def gen_thumbnail(filename, slide, size, imgtype="png"):
    dest = filename + "." + imgtype
    print(dest)
    slide.get_thumbnail([size, size]).save(dest, imgtype.upper())

def process(record):
    file = record[FILE_FIELD]
    name = record[NAME_FIELD]
    try:
        slide = openslide.OpenSlide(file)
        gen_thumbnail(name, slide, IM_SIZE, imgtype="png")
        return ""
    except BaseException as e:
        # return errors only
        return name

# do it
manifest = requests.get('https://api.github.com/events').json()
res = ThreadPool(THREADS).imap_unordered(process, manifest)
print([r for r in res])
