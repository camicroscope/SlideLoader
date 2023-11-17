from image_reader import construct_reader
from multiprocessing.pool import ThreadPool
import requests
import sys
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

if len(sys.argv <2):
    sys.exit("Expects a url as second argument")

url = sys.argv[1]

data = requests.get(url=url).json()


def get_thumbnail(obj):
    slide = obj['file-location']
    dest = obj['case_id'] + '.png'
    try:
        image = construct_reader(slide)
        image.get_thumbnail([200,200]).save(dest, "PNG")
        return dest
    except BaseException as e:
        return e

res = ThreadPool(20).imap_unordered(get_thumbnail, data)
print([r for r in res])
