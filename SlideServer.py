import base64
import json
import os
import random
import shutil
import string
import sys
from datetime import datetime
import pyvips
import os
from spritemaker import createSpritesheet
from PIL import Image
import urllib
import flask
import flask_cors
import threading
from flask import request
from image_reader import construct_reader, suggest_folder_name
from werkzeug.utils import secure_filename
import dev_utils
import requests
import zipfile
import csv 
import pathlib
import logging
from gdrive_utils import getFileFromGdrive, gDriveGetFile, checkDownloadStatus
from threading import Thread
from file_extensions import ALLOWED_EXTENSIONS
from time import sleep
import hashlib
from urllib.parse import urlparse
from dicomweb_client.api import DICOMwebClient

from DicomAnnotUtils import dicomToCamic
import pydicom

# mongo stuff
import pymongo
from bson.objectid import ObjectId



try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO

app = flask.Flask(__name__)
flask_cors.CORS(app)

# dataset storage location for the workbench tasks 
app.config['DATASET_FOLDER'] = "/images/dataset/"

# where to put and get slides
app.config['UPLOAD_FOLDER'] = "/images/"
app.config['TEMP_FOLDER'] = "/images/uploading/"
app.config['TOKEN_SIZE'] = 10
app.config['SECRET_KEY'] = os.urandom(24)
app.config['ROI_FOLDER'] = "/images/roiDownload"

#creating a uploading folder if it doesn't exist
if not os.path.exists(app.config['TEMP_FOLDER']):
    os.mkdir(app.config['TEMP_FOLDER'])


# should be used instead of secure_filename to create new files whose extensions are important.
# use secure_filename to access previous files.
# secure_filename ensures security but may result in invalid filenames.
# secure_filename should be used to access, because users of caMicroscope
# might have already uploaded what caMicroscope cannot read,
# and allow reading those.
def secure_filename_strict(filename):
    split_filename = secure_filename(filename).rsplit('.', 1)
    split_filename[-1] = split_filename[-1].lower() # .SvS, .Svs, ... shouldn't be allowed
    if len(split_filename) < 2:
        # for example, #.svs -> .svs -> svs, which removes the extension
        split_filename = ["noname", split_filename[-1]]
    return '.'.join(split_filename)

def verify_extension(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_relative_path(filename):
    if filename[0] == os.sep:
        raise ValueError("Filepath starts from the root directory which is forbidden")
    if os.sep + os.sep in filename:
        raise ValueError("Filepath contains '//' which is forbidden")
    if os.sep + '.' + os.sep in filename:
        raise ValueError("Filepath contains '/./' which is forbidden")
    if ".." in filename:
        raise ValueError("Filepath contains '..' which is forbidden")
    if filename[0] == '.':
        raise ValueError("Filepath starts with '.' (or is '.') which is forbidden")
    level_names = filename.split(os.sep)
    filename = ""
    for name in level_names:
        name = secure_filename(name)
        if len(name) == 0:
            name = "noname"
        filename += name
        filename += os.sep
    return filename[:-1]


def getThumbnail(filename, size=50):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(filepath):
        return {"error": "No such file"}
    try:
        slide = construct_reader(filepath)
    except BaseException as e:
        # here, e has attribute "error"
        return e

    try:
        thumb = slide.get_thumbnail((size, size))
        buffer = BytesIO()
        thumb.save(buffer, format="PNG")
        data = 'data:image/png;base64,' + str(base64.b64encode(buffer.getvalue()))[2:-1]
        return {"slide": data, "size": size}
    except BaseException as e:
        return {"type": slide.reader_name(), "error": str(e)}

@app.route('/slide/<filename>/pyramid/<dest>', methods=['POST'])
def makePyramid(filename, dest):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        destpath = os.path.join(app.config['UPLOAD_FOLDER'], dest)
        savedImg = pyvips.Image.new_from_file(filepath, access='sequential').tiffsave(destpath, tile=True, compression="lzw", tile_width=256, tile_height=256, pyramid=True, bigtiff=True)
        while not os.path.exists(filepath):
            os.sync()
            sleep(750)
        return flask.Response(json.dumps({"status": "OK", "srcFile":filename, "destFile":dest, "details":savedImg}), status=200, mimetype='text/json')
    except BaseException as e:
        return flask.Response(json.dumps({"type": "pyvips", "error": str(e)}), status=500, mimetype='text/json')


# routes

# start a file upload by registering the intent to upload, get a token to be used in future upload requests
@app.route('/upload/start', methods=['POST'])
def start_upload():
    token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
    token = secure_filename(token)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    # regenerate if we happen to collide
    while os.path.isfile(tmppath):
        token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
        token = secure_filename(token)
        tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    f = open(tmppath, 'a')
    f.close()
    res_body = {"upload_token": token}
    body = flask.request.get_json()
    if body and body.get('filename'):
        res_body['filename'] = secure_filename_strict(body['filename'])
    return flask.Response(json.dumps(res_body), status=200, mimetype='text/json')


# using the token from the start upload endpoint, post data given offset.
@app.route('/upload/continue/<token>', methods=['POST'])
def continue_file(token):
    token = secure_filename(token)
    print(token, file=sys.stderr)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    if os.path.isfile(tmppath):
        body = flask.request.get_json()
        if not body:
            return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400, mimetype='text/json')
        offset = body['offset'] or 0
        if not 'data' in body:
            return flask.Response(json.dumps({"error": "File data not found in body"}), status=400, mimetype='text/json')
        else:
            data = base64.b64decode(body['data'])
            f = open(tmppath, "ab")
            f.seek(int(offset))
            f.write(data)
            f.close()
            return flask.Response(json.dumps({"status": "OK"}), status=200, mimetype='text/json')
    else:
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400, mimetype='text/json')


# end the upload, by removing the in progress indication; locks further modification
@app.route('/upload/finish/<token>', methods=['POST', "GET"])
def finish_upload(token):
    body = flask.request.get_json()
    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400, mimetype='text/json')
    token = secure_filename(token)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    if not os.path.isfile(tmppath):
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400, mimetype='text/json')
    filename = body['filename']
    if filename and verify_extension(filename):
        filename = secure_filename_strict(filename)
        foldername = suggest_folder_name(tmppath, filename.rsplit('.', 1)[1])
        if foldername != "":
            folderpath = os.path.join(app.config['UPLOAD_FOLDER'], foldername)
            if not os.path.isdir(folderpath):
                os.mkdir(folderpath)
            relpath = os.path.join(foldername, filename)
        else:
            relpath = filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], relpath)
        if not os.path.isfile(filepath):
            shutil.move(tmppath, filepath)
            return flask.Response(json.dumps({"ended": token, "filepath": filepath, "filename": filename, "relpath": relpath}), status=200, mimetype='text/json')
        else:
            return flask.Response(json.dumps({"error": "File with name '" + filename + "' already exists", "filepath": filepath, "filename": filename}), status=400, mimetype='text/json')
        # The above return "filename" to show the user the sanitized filename
        # and on success, return relpath for subsequent SlideLoader calls by the frontend.
    else:
        return flask.Response(json.dumps({"error": "Invalid filename"}), status=400, mimetype='text/json')

    # check for token
    # get info associated with token
    # move the file out of temp to upload dir

# Delete the requested slide
@app.route('/slide/delete', methods=['POST'])
def slide_delete():
    body = flask.request.get_json()

    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400, mimetype='text/json')
        
    filename = body['filename']
    if filename and verify_extension(filename):
        filename = secure_relative_path(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(filepath):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return flask.Response(json.dumps({"deleted": filename, "success": True}), mimetype='text/json') 
        else:
            return flask.Response(json.dumps({"error": "File with name '" + filename + "' does not exist"}), status=400, mimetype='text/json')

    else:
        return flask.Response(json.dumps({"error": "Invalid filename"}), status=400, mimetype='text/json')

    # check for file if it exists or not
    # delete the file

@app.route("/test", methods=['GET'])
def testRoute():
    return '{"Status":"up"}'


@app.route("/data/one/<path:filepath>", methods=['GET'])
def singleSlide(filepath):
    filepath = secure_relative_path(filepath)
    extended = request.args.get('extended')
    res = dev_utils.getMetadata(os.path.join(app.config['UPLOAD_FOLDER'], filepath), extended, False)
    res["filepath"] = filepath
    if (hasattr(res, 'error')):
        return flask.Response(json.dumps(res), status=500, mimetype='text/json')
    else:
        return flask.Response(json.dumps(res), status=200, mimetype='text/json')


@app.route("/data/thumbnail/<path:filepath>", methods=['GET'])
def singleThumb(filepath):
    filepath = secure_relative_path(filepath)
    size = flask.request.args.get('size', default=50, type=int)
    size = min(500, size)
    res = getThumbnail(filepath, size)
    if (hasattr(res, 'error')):
        return flask.Response(json.dumps(res), status=500, mimetype='text/json')
    else:
        return flask.Response(json.dumps(res), status=200, mimetype='text/json')


@app.route("/data/many/<filepathlist>", methods=['GET'])
def multiSlide(filepathlist):
    extended = request.args.get('extended')
    filenames = json.loads(filepathlist)
    paths = [secure_relative_path(filename) for filename in filenames]
    absolute_paths = [os.path.join(app.config['UPLOAD_FOLDER'], path) for path in paths]
    res = dev_utils.getMetadataList(absolute_paths, extended, False)
    for i in range(len(absolute_paths)):
        res[i]["filepath"] = paths[i]
    if (hasattr(res, 'error')):
        return flask.Response(json.dumps(res), status=500, mimetype='text/json')
    else:
        return flask.Response(json.dumps(res), status=200, mimetype='text/json')

# Used by Caracal; may be removed after our schema fully supports multifile formats in a subdir
@app.route("/data/folder/<path:relpath>", methods=['GET'])
def listFolderContents(relpath):
    res = {}
    try:
        relpath = secure_relative_path(relpath)
        absolutepath = os.path.join(app.config['UPLOAD_FOLDER'], relpath)
    except BaseException as e:
        res['error'] = "bad folderpath: " + str(e)
        return flask.Response(json.dumps(res), status=400, mimetype='text/json')

    try:
        res['contents'] = os.listdir(absolutepath)
        res['contents'] = [filename for filename in res['contents'] if not filename.startswith('.')]
        return flask.Response(json.dumps(res), status=200, mimetype='text/json')
    except:
        res['contents'] = []
        return flask.Response(json.dumps(res), status=200, mimetype='text/json')

@app.route("/getSlide/<path:image_name>")
def getSlide(image_name):
    image_name = secure_relative_path(image_name)
    if not verify_extension(image_name):
        return flask.Response(json.dumps({"error": "Bad image type requested"}), status=400, mimetype='text/json')
    folder = app.config['UPLOAD_FOLDER']
    if os.sep in image_name:
        folder_and_file = image_name.rsplit(os.sep, 1)
        folder = os.path.join(folder, folder_and_file[0])
        image_name = folder_and_file[1]
    if(os.path.isfile(os.path.join(folder, image_name))):
        return flask.send_from_directory(folder, image_name, as_attachment=True)
    else:
        return flask.Response(json.dumps({"error": "File does not exist"}), status=404, mimetype='text/json')

# using the token from the start url upload endpoint
@app.route('/urlupload/continue/<token>', methods=['POST'])
def continue_urlfile(token):
    token = secure_filename(token)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    if os.path.isfile(tmppath):
        body = flask.request.get_json()
        if not body:
            return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400, mimetype='text/json')
        if not 'url' in body:
            return flask.Response(json.dumps({"error": "File url not present in body"}), status=400, mimetype='text/json')
        else:
            url = body['url']
            try:
                url = urllib.parse.unquote(url)
                urllib.request.urlretrieve(url, tmppath)
                return flask.Response(json.dumps({"status": "OK Uploaded"}), status=200, mimetype='text/json')
            except:
                return flask.Response(json.dumps({"error": "URL invalid"}), status=400, mimetype='text/json')
    else:
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400, mimetype='text/json')

# Route to check if the URL file has completely uploaded to the server 
# Query Params: 'url', 'token'
@app.route('/urlupload/check', methods=['GET'])
def urlUploadStatus():
    url = flask.request.args.get('url')
    url = urllib.parse.unquote(url)
    token = flask.request.args.get('token')
    info = requests.head(url)
    urlFileSize = int(info.headers['Content-Length'])
    fileSize = os.path.getsize(app.config['TEMP_FOLDER']+'/'+token)
    if(fileSize >= urlFileSize):
        return flask.Response(json.dumps({"uploaded": "True"}), status=200, mimetype='text/json')
    else:
        return flask.Response(json.dumps({"uploaded": "False"}), status=200, mimetype='text/json')



# Workbench Dataset Creation help-routes

# Route to receive base64 encoded zip files.
# Files are extracted and patches.csv is read and label details are sent back
@app.route('/workbench/getLabelsZips', methods=['POST'])
def getLabelsZips():
    data = flask.request.get_json()
    userFolder = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for _ in range(20))
    labelsData = {'labels': [], 'counts': [], 'userFolder': userFolder}
    if not os.path.isdir(app.config['DATASET_FOLDER']+userFolder):
        os.makedirs(app.config['DATASET_FOLDER']+userFolder)
    for i in range(len(data['files'])):
        tmppath = os.path.join(
            app.config['DATASET_FOLDER']+userFolder+'/', data['fileNames'][i])
        fileData = base64.b64decode(data['files'][i])
        file = open(tmppath, "ab")
        file.seek(0)
        file.write(fileData)
        file.close()
        if(zipfile.is_zipfile(tmppath) == False):
            deleteDataset(userFolder)
            return flask.Response(json.dumps({'error': 'Not a valid zip file/files'}), status=400, mimetype='text/json')
        with zipfile.ZipFile(tmppath, 'r') as zip_ref:
            zip_ref.extractall(tmppath[0:-4])
        csvFile = pathlib.Path(tmppath[0:-4]+'/patches.csv')
        if not csvFile.is_file():
            deleteDataset(userFolder)
            return flask.Response(json.dumps({'error': 'Not a valid labels zip/zips'}), status=400, mimetype='text/json')
        csvFile = tmppath[0:-4]+'/patches.csv'
        with open(csvFile, 'r') as data1:
            i = 0
            for line in csv.reader(data1):
                if i != 0 and line[2] != '':
                    if line[2] not in labelsData['labels']:
                        labelsData['labels'].append(line[2])
                        labelsData['counts'].append(1)
                    else:
                        labelsData['counts'][labelsData['labels'].index(
                            line[2])] += 1
                i += 1
    return flask.Response(json.dumps(labelsData), status=200, mimetype='text/json')


# Route to receive base64 encoded zip file for custom dataset.
@app.route('/workbench/getCustomData', methods=['POST'])
def getCustomData():
    data = flask.request.get_json()
    fileName = data['fileName']
    userFolder = data['userFolder']
    if not os.path.isdir(app.config['DATASET_FOLDER']+userFolder):
        os.makedirs(app.config['DATASET_FOLDER']+userFolder)
    path = os.path.join(app.config['DATASET_FOLDER']+userFolder+'/', fileName)
    fileData = base64.b64decode(data['file'])
    offset = data['offset']
    file = open(path, "ab")
    file.seek(int(offset))
    file.write(fileData)
    file.close()
    final = data['final']
    if(final == 'true'):
        if(zipfile.is_zipfile(path) == False):
            deleteDataset(userFolder)
            return flask.Response(json.dumps({'error': 'Not a valid zip file/files'}), status=400, mimetype='text/json')
        file = zipfile.ZipFile(path, 'r')
        # app.logger.info(file.namelist())
        contents = file.namelist()
        labelsData = {'labels': [], 'counts': [], 'userFolder': userFolder}
        for item in contents:
            if '/' not in item:
                deleteDataset(userFolder)
                return flask.Response(json.dumps({'error': 'zip should contain only folders!'}), status=400, mimetype='text/json')
            if item.endswith('/') == False and item.endswith('.jpg') == False and item.endswith('.jpeg') == False and item.endswith('.png') == False and item.endswith('.tif') == False and item.endswith('.tiff') == False:
                deleteDataset(userFolder)
                return flask.Response(json.dumps({'error': 'Dataset zip should have only png/jpg/tif files!'}), status=400, mimetype='text/json')
            if item.split('/')[0] not in labelsData['labels']:
                labelsData['labels'].append(item.split('/')[0])
        for label in labelsData['labels']:
            count = -1
            for item in contents:
                if item.startswith(label+'/'):
                    count+=1
            labelsData['counts'].append(count)
        return flask.Response(json.dumps(labelsData), status=200, mimetype='text/json')
    else:
        return flask.Response(json.dumps({'status' : 'pending'}), status=200, mimetype='text/json')


# Route to organise the extracted zip file data according to user sent customized labels and create a spritesheet
# Link to download the dataset.zip is sent back to the user
@app.route('/workbench/generateSprite', methods=['POST'])
def generateSprite():
    data = flask.request.get_json()
    userFolder = data['userFolder']
    labels = data['labels']
    included = data['included']
    fileNames = data['fileNames']
    height = int(data['height'])
    width = int(data['width'])
    selectedLabels = []
    for i in range(len(labels)):
        if included[i] == True:
            selectedLabels.append(labels[i])
    for i in range(len(fileNames)):
        path = os.path.join(
            app.config['DATASET_FOLDER']+userFolder+'/', fileNames[i])[0:-4]
        csvFile = path+'/patches.csv'
        with open(csvFile, 'r') as data1:
            i = 0
            for line in csv.reader(data1):
                if i != 0 and line[2] != '' and line[2] in selectedLabels:
                        if not os.path.isdir(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'+line[2]):
                            os.makedirs(
                                app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'+line[2])
                        file = pathlib.Path(path+line[8][1:])
                        if not file.is_file():
                            deleteDataset(userFolder)
                            return flask.Response(json.dumps({'error': 'Images are missing from one or more zip files'}), status=400, mimetype='text/json')
                        file = path+line[8][1:]
                        fileName = ''.join(random.choice(
                            string.ascii_lowercase + string.digits) for _ in range(40))
                        newFile = app.config['DATASET_FOLDER']+userFolder + \
                            '/spritesheet/'+line[2]+'/'+fileName+'.jpg'
                        shutil.move(file, newFile)
                i += 1
    try:
        createSpritesheet(app.config['DATASET_FOLDER']+userFolder, selectedLabels, width, height)
    except:
        return flask.Response(json.dumps({'error': str(sys.exc_info()[0])}), status=400, mimetype='text/json')
    with open(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/labelnames.csv', 'w', newline='') as labelsnamesCSVfile:
        writer = csv.writer(labelsnamesCSVfile)
        writer.writerow(selectedLabels)
    zipObj = zipfile.ZipFile(
        app.config['DATASET_FOLDER']+userFolder+'/spritesheet/dataset.zip', 'w')
    zipObj.write(app.config['DATASET_FOLDER'] +
                 userFolder+'/spritesheet/data.jpg', '/data.jpg')
    zipObj.write(app.config['DATASET_FOLDER']+userFolder +
                 '/spritesheet/labels.bin', '/labels.bin')
    zipObj.write(app.config['DATASET_FOLDER']+userFolder +
                 '/spritesheet/labelnames.csv', '/labelnames.csv')
    download_link = '/workbench/sprite/download/'+userFolder
    download_file(userFolder)
    return flask.Response(json.dumps({'status': 'done', 'userFolder': userFolder, 'download': download_link}), status=200, mimetype='text/json')


# Route to extract images and create the spritesheet according to user defined labels incase of custom data
@app.route('/workbench/generateCustomSprite', methods=['POST'])
def generateCustomSprite():
    data = flask.request.get_json()
    userFolder = data['userFolder']
    labels = data['labels']
    included = data['included']
    fileName = data['fileNames'][0]
    height = int(data['height'])
    width = int(data['width'])
    selectedLabels = []
    for i in range(len(labels)):
        if included[i] == True:
            selectedLabels.append(labels[i])
    path = os.path.join(
            app.config['DATASET_FOLDER']+userFolder+'/', fileName)
    if not os.path.isdir(app.config['DATASET_FOLDER']+userFolder+'/spritesheet'):
        os.makedirs(app.config['DATASET_FOLDER']+userFolder+'/spritesheet')
    file = zipfile.ZipFile(path, 'r')
    contents = file.namelist()
    selectedFiles = []
    for item in contents:
        if included[labels.index(item.split('/')[0])] == True:
            selectedFiles.append(item)
    file.extractall(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/', selectedFiles)
    try:
        createSpritesheet(app.config['DATASET_FOLDER']+userFolder, selectedLabels, width, height)
    except:
         return flask.Response(json.dumps({'error': str(sys.exc_info()[0])}), status=400, mimetype='text/json')
    with open(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/labelnames.csv', 'w', newline='') as labelsnamesCSVfile:
        writer = csv.writer(labelsnamesCSVfile)
        writer.writerow(selectedLabels)
    zipObj = zipfile.ZipFile(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/dataset.zip', 'w')
    zipObj.write(app.config['DATASET_FOLDER'] +
                 userFolder+'/spritesheet/data.jpg', '/data.jpg')
    zipObj.write(app.config['DATASET_FOLDER']+userFolder +
                 '/spritesheet/labels.bin', '/labels.bin')
    zipObj.write(app.config['DATASET_FOLDER']+userFolder +
                 '/spritesheet/labelnames.csv', '/labelnames.csv')
    download_link = '/workbench/sprite/download/'+userFolder
    download_file(userFolder)
    return flask.Response(json.dumps({'status': 'done', 'userFolder': userFolder, 'download': download_link}), status=200, mimetype='text/json')


# Dynamic download route for dataset.zip
@app.route('/workbench/sprite/download/<userFolder>')
def download_file(userFolder):
    path = app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'
    return flask.send_from_directory(path, 'dataset.zip', as_attachment=True)


# To delete the the user-specific useless files after download is complete
@app.route('/workbench/deleteDataset/<userFolder>', methods=['POST'])
def deleteDataset(userFolder):
    if '/' in userFolder or '..' in userFolder or len(userFolder) != 20:
        return flask.Response(json.dumps({"deleted": "false", 'message': 'Traversal detected or invalid foldername'}), status=403, mimetype='text/json')
    shutil.rmtree(app.config['DATASET_FOLDER']+userFolder)
    return flask.Response(json.dumps({"deleted": "true"}), status=200, mimetype='text/json')


# Helper function for converting slides into jpg 
def _get_concat_h(img_lst):
    width, height, h = sum([img.width for img in img_lst]), img_lst[0].height, 0
    dst = Image.new('RGB', (width, height))
    for img in img_lst:
        dst.paste(img, (h, 0))
        h += img.width
    return dst

# Helper function for converting slides into jpg 
def _get_concat_v(img_lst):
    width, height, v = img_lst[0].width, sum([img.height for img in img_lst]), 0
    dst = Image.new('RGB', (width, height))
    for img in img_lst:
        dst.paste(img, (0, v))
        v += img.height
    return dst

# FUnction to convert slides into jpg images
def convert(fname, input_dir , output_dir):
    UNIT_X, UNIT_Y = 5000, 5000
    try:
        
        save_name = fname.split(".")[0] + ".jpg"
        os_obj = construct_reader(input_dir+"/"+fname)
        w, h = os_obj.dimensions
        w_rep, h_rep = int(w/UNIT_X)+1, int(h/UNIT_Y)+1
        w_end, h_end = w%UNIT_X, h%UNIT_Y
        w_size, h_size = UNIT_X, UNIT_Y
        w_start, h_start = 0, 0
        v_lst = []
        for i in range(h_rep):
            if i == h_rep-1:
                h_size = h_end 
            h_lst = []
            for j in range(w_rep):
                if j == w_rep-1:
                    w_size = w_end
                img = os_obj.read_region((w_start,h_start), 0, (w_size,h_size))
                img = img.convert("RGB")
                h_lst.append(img)
                w_start += UNIT_X
            v_lst.append(h_lst)
            w_size = UNIT_X
            h_start += UNIT_Y
            w_start = 0
        concat_h = [_get_concat_h(v) for v in v_lst]
        concat_hv = _get_concat_v(concat_h)
        concat_hv.save(output_dir+"/"+save_name)
    except:
        print("Can't open image file : %s"%fname)
        traceback.print_exc()
    return    

# Route to extract the patches using the predictions recieved 
@app.route('/roiExtract', methods = ['POST'])
def roiExtract():
    data = flask.request.get_json()
    pred = data['predictions']
    filename = data['filename']
    step = data['patchsize']
    fn =filename.split(".")[0] + ".jpg"
    if  os.path.isdir("/images/roiDownload"):
        shutil.rmtree(app.config['ROI_FOLDER'])
    os.makedirs("/images/roiDownload")
    filepath = "/images/roiDownload/roi_Download" + filename + ".zip"
    convert(filename, "/images","/images/roiDownload")
    download_patches = zipfile.ZipFile(filepath, 'w')
    img = Image.open("/images/roiDownload/"+fn)
    for i in range(len(data['predictions'])):
        img1 = img.crop((int(data['predictions'][i]['X']),int(data['predictions'][i]['Y']) , int(data['predictions'][i]['X'])+int(step),int(data['predictions'][i]['Y'])+int(step)))
        img1.save("/images/roiDownload/"+str(data['predictions'][i]['cls'])+'_'+str(i)+'_'+ str(data['predictions'][i]['acc']*100)+".jpg")
        download_patches.write("/images/roiDownload/"+str(data['predictions'][i]['cls'])+'_'+str(i)+'_'+ str(data['predictions'][i]['acc']*100)+".jpg" , "/patches/"+
        str(data['predictions'][i]['cls'])+"/"+str(data['predictions'][i]['cls'])+'_'+str(i)+'_'+ str(data['predictions'][i]['acc']*100)+".jpg")
        
    download_patches.close()

    # img = openslide.OpenSlide.read_region((0,0),0,(100,100))
    # img = slide.open_image(img_path)
    # res= { "data" :"" }
    # res['data']= pred
    return flask.Response(json.dumps({"extracted": "true"}), status=200, mimetype='text/json')
    
# Route to send back the extracted
@app.route('/roiextract/<file_name>')
def roiextract(file_name):

    return flask.send_from_directory(app.config["ROI_FOLDER"], file_name, as_attachment=True, cache_timeout=0 )


# Google Drive API (OAuth and File Download) Routes

# A new Thread to call the Gdrive API after an Auth Response is returned to the user.
class getFileFromGdrive(Thread):
    def __init__(self, params, userId, fileId, token):
        Thread.__init__(self)
        self.params, self.userId, self.fileId , self.token = params, userId, fileId, token

    def run(self):
        if(self.params["auth_url"] != None):
            self.params["creds"] = afterUrlAuth(self.params["local_server"], self.params["flow"], self.params["wsgi_app"], self.userId)
        call = callApi(self.params["creds"], self.fileId, self.token)
        app.logger.info(call)

# Route to start the OAuth Server(to listen if user is Authenticated) and start the file Download after Authentication
@app.route('/googleDriveUpload/getFile', methods=['POST'])
def gDriveGetFileRoute():
    body = flask.request.get_json()
    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
    return gDriveGetFile(body)

# To check if a particular file is downloaded from Gdrive
@app.route('/googleDriveUpload/checkStatus', methods=['POST'])
def checkDownloadStatusRoute():
    body = flask.request.get_json()
    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
    return checkDownloadStatus(body)

# DICOM Explorer UI and DICOM server hostname and port
@app.route('/dicomsrv/location', methods=['GET'])
def guiLocation():
    port = os.getenv("DICOM_PORT")
    hostname = os.getenv("DICOM_HOSTNAME")
    ui_port = os.getenv("DICOM_UI_PORT")
    ui_hostname = os.getenv("DICOM_UI_HOSTNAME")
    res = {}
    if port is not None:
        res["port"] = int(port)
    else:
        print("DICOM_PORT env variable not found")

    if ui_port is not None:
        res["ui_port"] = int(ui_port)
    else:
        print("DICOM_UI_PORT env variable not found")


    # If the DICOM server is on a different computer, this can be uncommented,
    # the frontend will parse this, but it's better to keep this in a comment against env var poisoning
    # if hostname is not None:
    #     res["hostname"] = hostname
    # if ui_hostname is not None:
    #     res["ui_hostname"] = ui_hostname

    success = "port" in res and "ui_port" in res
    return flask.Response(json.dumps(res), status=200 if success else 500, mimetype='text/json')

# things needed for just dicom routes
app.config['MONGO_URI'] = "mongodb://ca-mongo:27017/"
app.config['MONGO_DB'] = "camic"

mongo_client = pymongo.MongoClient(app.config['MONGO_URI'])
mongo_db = mongo_client[app.config['MONGO_DB']]

# find if a slide already exists for this
def _findMatchingSlide(study, series):
    query = {"study": study, "series": series}
    return mongo_db['slide'].find_one(query)
    
def _getSlide(slide_id):
    object_id = ObjectId(slide_id)
    result = mongo_db['slide'].find_one({"_id": object_id})
    return result

def _setSlideStatus(slide_id, status):
    object_id = ObjectId(slide_id)
    result = mongo_db['slide'].update_one({"_id": object_id}, {"$set": {"status": status}})
    return result

def _add_slide(document):
    insert_result = mongo_db['slide'].insert_one(document)
    return str(insert_result.inserted_id)

def _add_mark(document):
    insert_result = mongo_db['mark'].insert_one(document)
    return str(insert_result.inserted_id)


def _get_hash_prefix(input_string, length=8):
    algorithm='sha256'
    input_bytes = input_string.encode('utf-8')
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(input_bytes)
    full_hash = hash_obj.hexdigest()
    hash_prefix = full_hash[:length]
    return hash_prefix

def find_referenced_image(study, ds):
    instance_uid = ds.ReferencedImageSequence[0].ReferencedSOPInstanceUID
    study_directory = app.config['UPLOAD_FOLDER'] + _get_hash_prefix(study, length=10) + "_dicomweb"
    # Traverse through the study directory
    for root, dirs, files in os.walk(study_directory):
        for file_name in files:
            if file_name.endswith('.dcm'):
                file_path = os.path.join(root, file_name)
                ds = pydicom.dcmread(file_path)
                if ds.SOPInstanceUID == instance_uid:
                    # Found the instance, return its SeriesInstanceUID
                    return ds.SeriesInstanceUID, file_path

    # If the instance is not found in the study
    return None, None

def downloadRawDicom(source_url, study_uid, series_uid, instance_uid, output_fn):
    instance_url = source_url + f"/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}"
    response = requests.get(instance_url, stream=True)
    if response.status_code == 200:
        with open(output_fn, "wb") as file:
            content_type_header = response.headers.get('Content-Type')
            boundary = content_type_header.split('boundary=')[1].split(';')[0].strip()
            app.logger.info("Working on file: " +  output_fn)
            dicom_started = False
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    if not dicom_started:
                        # Check if the chunk contains "\r\n\r\n""
                        if b"\r\n\r\n" in chunk:
                            # Find the position of "\r\n\r\n"" in the chunk
                            start_idx = chunk.find(b"\r\n\r\n")
                            file.write(chunk[start_idx + 4:])
                            # Set dicom_started to True
                            dicom_started = True
                    else:
                        # Write entire chunk to the file
                        file.write(chunk)
            # remove the trailing multipart stuff
            file.seek(-len(boundary) - 6, 2)  # Move the file pointer to before the boundary
            file.truncate()  # Truncate the file at the current position
        
        print("DICOM instance saved successfully.")
    else:
        print(f"Failed to retrieve DICOM instance. Status code: {response.status_code}")

# dicom web based routes

def doDicomSlideDownloads(source_url, study, series, instance_list, camic_slide_id):
    client = DICOMwebClient(source_url)
    for instance in instance_list:
        app.logger.info("Working on instance: " +  instance)
        try:
            dest_directory = app.config['UPLOAD_FOLDER'] + _get_hash_prefix(study, length=10) + "_dicomweb"
            if not os.path.exists(dest_directory):
                os.makedirs(dest_directory)
            output_fn = dest_directory + "/" + instance + ".dcm"
            downloadRawDicom(source_url, study, series, instance, output_fn)
        except BaseException as e:
            app.logger.info("err: " + str(e))
    # we're done, update the camic slide instance to done
    _setSlideStatus(camic_slide_id, "done")
    camic_slide_id

def doDicomAnnDownloads(source_url, study, series, instance_list):
    client = DICOMwebClient(source_url)
    for instance in instance_list:
        app.logger.info("Working on instance: " + instance)
        try:
            instance_resp = client.retrieve_instance(
                study_instance_uid=study,
                series_instance_uid=series,
                sop_instance_uid=instance
            )
            ref_series, ref_file = find_referenced_image(study, instance_resp)
            if ref_series:
                slide_res = _findMatchingSlide(study, ref_series)
                if slide_res:
                    slide_id = str(slide_res['_id'])
                    reference_slide_path = ref_file
                    dest_directory = app.config['UPLOAD_FOLDER'] + _get_hash_prefix(study, length=10) + "_dicomweb"
                    if not os.path.exists(dest_directory):
                        os.makedirs(dest_directory)
                    annot_path = dest_directory + "/" + instance + ".dcm"
                    instance_resp.save_as(annot_path)
                    res = dicomToCamic(annot_path, reference_slide_path, None, slide_id, file_mode=False)
                    # load into camic
                    for doc in res:
                        _add_mark(doc)
                else:
                    # get the slide then try this again
                    getDicomSmThenAnn(source_url, study, ref_series, study, series)
            else:
                e = {"err": "err", "msg": "couldn't find the reference"}
                app.logger.info("err: " + str(e))
                return e 
        except BaseException as e:
            app.logger.info("err: " +  str(e))
            


def getDicomSeriesANN(source_url, study, series):
    client = DICOMwebClient(source_url)
    instances = client.search_for_instances(
        study_instance_uid=study,
        series_instance_uid=series
    )
    instance_list = [x['00080018']['Value'][0] for x in instances]
    load_thread = threading.Thread(target=doDicomAnnDownloads, args=(source_url, study, series, instance_list))
    load_thread.start()

def getDicomSeriesSM(source_url, study, series, blocking=False):
    # check if the slide object matching already exists, returning it if so.
    matching_slide = _findMatchingSlide(study, series)
    if matching_slide:
        return {'status': 'already exists', 'slide_id': str(matching_slide["_id"])}
    client = DICOMwebClient(source_url)
    instances = client.search_for_instances(
        study_instance_uid=study,
        series_instance_uid=series
    )
    instance_list = [x['00080018']['Value'][0] for x in instances]

    # do the download
    dest_directory = app.config['UPLOAD_FOLDER'] + _get_hash_prefix(study, length=10) + "_dicomweb"
    if not os.path.exists(dest_directory):
        os.makedirs(dest_directory)
    first_file = dest_directory + "/" + instance_list[0] + ".dcm"
    # if the slide object does not exist, make it using the first instance file name with in progress status
    current_time = datetime.now()
    formatted_time = current_time.strftime("%m/%d/%Y, %I:%M:%S %p")
    new_slide = {
        'location': first_file,
        'filepath': instance_list[0] + ".dcm",
        'upload_date': formatted_time ,
        'creator': "DicomWebImport",
        'dicom-source-url': source_url,
        'study': study,
        'series': series,
        'specimen': '',
        'status': 'loading',
        'name': _get_hash_prefix(study + "~" + series, length=12)
    }
    slide_id = _add_slide(new_slide)
    if blocking:
        doDicomSlideDownloads(source_url, study, series, instance_list, slide_id)
    else:
        load_thread = threading.Thread(target=doDicomSlideDownloads, args=(source_url, study, series, instance_list, slide_id))
        load_thread.start()
    return slide_id

def getDicomSmThenAnn(source_url, slide_study, slide_series, annot_study, annot_series):
    slide_id = getDicomSeriesSM(source_url, slide_study, slide_series, blocking=True)
    # slide is loaded, so just eventually load the annotations
    getDicomSeriesANN(source_url, annot_study, annot_series)

@app.route('/dicomWeb/importSeries', methods=['POST'])
def dicom_import():
    try:
        data = flask.request.get_json()
        source_url = data['source_url']
        study = data['study']
        series = data['series']
        modality = data['modality']
        if modality == "ANN":
            slide_id =  getDicomSeriesANN(source_url, study, series)
            return({"modality": modality, "status": "starting"})
        else:
            slide_id = getDicomSeriesSM(source_url, study, series, blocking=False)
            return({"modality": modality, 'slide_id': slide_id})
    except BaseException as e:
        raise e