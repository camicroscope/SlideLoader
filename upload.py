import sys
from dev_utils import getMetadata
from dev_utils import post_url
from dev_utils import postslide


def process(a):
    d = getMetadata(a[0], a[1])
    d['name'] = a[0]
    tmp = d['filename']
    tmp = tmp.replace("/data", "")
    d['location'] = tmp
    d['mpp'] = float(d['mpp-x'])
    print(d, post_url)
    postslide(d, post_url)


if __name__ == "__main__":
    args = sys.argv[1:]
    process(args)
