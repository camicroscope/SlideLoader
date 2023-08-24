#!/usr/bin/env python3

import dev_utils # to get required slide metadata
import csv # to read csv
import sys # for csv limit
import os # for os and filepath utils
import argparse # to read arguments
import json # for json in and out
import requests # for api and pathdb in and out
import hashlib

# for large csv fields, especially segmentations
csv.field_size_limit(sys.maxsize)

parser = argparse.ArgumentParser(description='Load slides or results to caMicroscope.')
# read in collection
parser.add_argument('-i', type=str, default="slide", choices=['slide', 'heatmap', 'mark', 'user', 'segmentation'],
                    help='Input type')
# read in filepath
parser.add_argument('-f', type=str, default="manifest.csv",
                    help='Input file')
# read in dest type
parser.add_argument('-o', type=str, default="camic", choices=['jsonfile', 'camic', 'pathdb'],
                    help='Output destination type')
# read in pathdb collection
parser.add_argument('-pc', type=str, help='Pathdb Collection Name')
# read in dest uri or equivalent
parser.add_argument('-d', type=str, default="http://ca-back:4010/data/Slide/post",
                    help='Output destination')
# read in lookup type
parser.add_argument('-lt', type=str, help='Slide ID lookup type', default="camic", choices=['camic', 'pathdb'])
# read in lookup uri or equivalent
parser.add_argument('-ld', type=str, default="http://ca-back:4010/data/Slide/find",
                    help='Slide ID lookup source')

args = parser.parse_args()
print(args)

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

# get fields openslide expects
def openslidedata(manifest):
    for img in manifest:
        img['location'] = img.get("path", "") or img.get("location", "") or img.get("filename", "") or img.get("file", "")
        metadata = dev_utils.getMetadata(img['location'], False, True)
        for k, v in metadata.items():
          if k not in img:
            img[k] = v
        # required values which are often unused
        img['study'] = img.get('study', "")
        img['specimen'] = img.get('specimen', "")
    return manifest

def getWithAuth(url):
    x = requests.get(lookup_url)
    retry = True
    while (x.status_code == 401 and retry):
        token = input("API returned 401, try a (different) token? : ")
        if (token and token != "no" and token != "n"):
            x = requests.get(lookup_url, auth=token)
        else:
            retry = False
    return x

def postWithAuth(url, data):
    x = requests.post(args.d, json=data)
    retry = True
    while (x.status_code == 401 and retry):
        token = input("API returned 401, try a (different) token? : ")
        if (token and token != "no" and token != "n"):
            x = requests.post(args.d, json=data, auth=token)
        else:
            retry = False
    return x

def convertSegmentations(poly, name, area):
    # interpret the objectively bad polygon representation
    poly = poly.replace("[","")
    poly = poly.replace("]","")
    poly = poly.split(":")
    new_poly = []
    x_max = -1.
    x_min = 9e99
    y_max = -1.
    y_min = 9e99
    for i in range(0,len(poly),2):
        x_max = max(x_max, float(poly[i]))
        x_min = min(x_min, float(poly[i]))
        y_max = max(y_max, float(poly[i+1]))
        y_min = min(y_min, float(poly[i+1]))
        new_poly.append([float(poly[i]), float(poly[i+1])])
        # construct result
    # complete loop
    new_poly.append(new_poly[0])
    provenance = {}
    provenance['image'] = {}
    # may need better execution id
    provenance['analysis'] = {"source":"computer", "coordinate":"image", "execution_id":name, "name":name, "computation":"segmentation"}
    properties = {}
    properties['annotations'] = {"name": name, 'AreaInPixels':area, "PhysicalSize":area}
    geometries = {"type":"FeatureCollection"}
    feature = {"type":"Feature"}
    geometry = {"type":"Polygon"}
    geometry['coordinates'] = [new_poly]
    bound = {"type":"Polygon"}
    feature['geometry'] = geometry
    feature['bound'] = bound
    # get bound
    bound['coordinates'] = [[[x_min, y_min], [x_min, y_max], [x_max, y_max], [x_max, y_min], [x_min, y_min]]]
    geometries['features'] = [feature]
    res = {}
    res['geometries'] = geometries
    res['provenance'] = provenance
    res['properties'] = properties
    res['footprint'] = area
    res['x'] = x_min
    res['y'] = y_min
    res['object_type'] = "unknown"
    res['parent_id'] = "self"
    return res

## START script

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

# perform slide lookup for results, as applicable
if (args.i == "slide"):
    manifest = openslidedata(manifest)
else:

    if (args.lt == "camic"):
        for x in manifest:
            # TODO more flexible with manifest fields
            lookup_url = args.ld + "?name=" + x['slide']
            r = getWithAuth(lookup_url)
            res = r.json()
            try:
                x['id'] = res[0]["_id"]["$oid"]
            except:
                print("[WARN] - no match for slide '" + str(x) + "', skipping")
                del x
    if (args.lt == "pathdb"):
        for x in manifest:
            lookup_url = args.ld + "/" + args.pc + "/"
            lookup_url += x.get("studyid", "") or x.get("study")
            lookup_url += "/" + x.get("clinicaltrialsubjectid", "") or x.get("subject")
            lookup_url += "/" + x.get("imageid", "") or x.get("image", "") or x.get("slide", "")
            lookup_url += "?_format=json"
            r = getWithAuth(lookup_url)
            res = r.json()
            try:
                x['id'] = res[0]["nid"][0]['value']
            except:
                print("[WARN] - no match for slide '" + str(x) + "', skipping")
                del x


# TODO add validation (!!)
print("[WARNING] -- Validation not Implemented")

# take appropriate destination action
if (args.o == "jsonfile"):
    with open(args.d, 'w') as f:
        json.dump(manifest, f)
elif (args.o == "camic"):
    if (args.i == "slide"):
        r = postWithAuth(args.d, manifest)
        print(r.json())
        r.raise_for_status()
    else:
        for x in manifest:
            with open(x['path']) as f:
                if (args.i == "segmentation"):
                    reader = csv.DictReader(f)
                    segs = [row for row in reader]
                    fil = []
                    for rec in segs:
                        res = convertSegmentations(rec['Polygon'], x['segname'], rec['AreaInPixels'])
                        res['provenance']['image']['slide'] = x['id']
                        fil.append(res)
                else:
                    fil = json.load(f)
                    for rec in fil:
                        # TODO safer version of this?
                        rec['provenance']['image']['slide'] = x['id']
                r = postWithAuth(args.d, fil)
                print(r.json())
                r.raise_for_status()
elif (args.o == "pathdb"):
    #! TODO - need the url and pattern for adding a slide to pathdb
    if (args.i != "slide"):
        raise AssertionError("Pathdb only holds slide data.")
    raise NotImplementedError("Output type: " + args.o + " not yet implemented")
else:
    raise NotImplementedError("Output type: " + args.o + " not yet implemented")
