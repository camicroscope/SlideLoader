#!/usr/bin/env python3

import openslide # to get required slide metadata
import csv # to read csv
import argparse # to read arguments
import time # for timestamp
import os # for os/fs systems
import json # for json in and out

parser = argparse.ArgumentParser(description='Load slides or results to caMicroscope.')
# read in collection
parser.add_argument('-i', type=str, default="slide", choices=['slide', 'heatmap', 'mark', 'user'],
                    help='Input type (collection)')
# read in filepath
parser.add_argument('-f', type=str, default="manifest.csv",
                    help='Input file')
# read in dest type
parser.add_argument('-o', type=str, default="mongo", choices=['mongo', 'jsonfile', 'api', 'pathdb'],
                    help='Output destination type')
# read in dest uri or equivalent
parser.add_argument('-d', type=str, default="ca-mongo",
                    help='Output destination')
# perform slide lookups for mongo or pathdb
parser.add_argument('--lookup', type=str, help='Lookup slide id for results')

args = parser.parse_args()
print(args)

def openslidedata(manifest):
    for img in manifest:
        img['location'] = img['location'] or img['filename'] or img['file']
        slide = openslide.OpenSlide(img['location'])
        slideData = slide.properties
        img['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
        img['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
        img['mpp'] = img['mpp-x'] or img['mpp-x'] or None
        img['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
        img['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
        img['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
        img['level_count'] = int(slideData.get('level_count', 1))
        img['objective'] = float(slideData.get("aperio.AppMag", None))
        img['timestamp'] = time.time()
        # required values which are often unused
        img['study'] = img.get('study', "")
        img['specimen'] = img.get('specimen', "")
    return manifest

manifest = []

# context for file
with open(args.f, 'r') as f:
    # determine type
    ext = os.path.splitext(args.f)[1]
    if (ext==".csv"):
        reader = csv.DictReader(f)
        manifest = [row for row in reader]
    elif (ext==".json"):
        manifest = json.load(f)
    else:
        raise NotImplementedError("Extension: " + ext + " Unsupported")

# if it's slide, do the slide info fill in
if (args.i == "slide"):
    manifest = openslidedata(manifest)
else:
    print("[WARNING] -- Slide id lookup not implemented")

# perform validation (!!)
print("[WARNING] -- Validation not Implemented")
# perform slide lookup for results, as applicable

# if dest is file, then write them
if(args.o == "jsonfile"):
    with open(args.d, 'w') as f:
        json.dump(manifest, f)
else:
    raise NotImplementedError("Output type: " + args.o + " not yet implemented")

# if dest is mongo, connect

# if dest is an api, try
# ^^ if 401, ask for a token

# if dest is pathdb, ask for token
