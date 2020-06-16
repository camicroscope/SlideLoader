import base64
import json
import os
import random
import shutil
import string
import sys
import pyvips
from os import listdir
from os.path import isfile, join
from spritemaker import createSpritesheet

import urllib
import flask
import flask_cors
import openslide
from werkzeug.utils import secure_filename
import dev_utils
import requests
import zipfile
import csv 
import pathlib

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

ALLOWED_EXTENSIONS = set(['svs', 'tif', 'tiff', 'vms', 'vmu', 'ndpi', 'scn', 'mrxs', 'bif', 'svslide'])    


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def getThumbnail(filename, size=50):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(filepath):
        return {"error": "No such file"}
    try:
        slide = openslide.OpenSlide(filepath)
        thumb = slide.get_thumbnail((size, size))
        buffer = BytesIO()
        thumb.save(buffer, format="PNG")
        data = 'data:image/png;base64,' + str(base64.b64encode(buffer.getvalue()))[2:-1]
        return {"slide": data, "size": size}
    except BaseException as e:
        return {"type": "Openslide", "error": str(e)}

@app.route('/slide/<filename>/pyramid/<dest>', methods=['POST'])
def makePyramid(filename, dest):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        destpath = os.path.join(app.config['UPLOAD_FOLDER'], dest)
        pyvips.Image.new_from_file(filepath, access='sequential').tiffsave(destpath, tile=True, compression="lzw", tile_width=256, tile_height=256, pyramid=True, bigtiff=True, xres=0.254, yres=0.254)
        return flask.Response(json.dumps({"status": "OK"}), status=200)
    except BaseException as e:
        return flask.Response(json.dumps({"type": "pyvips", "error": str(e)}), status=500)


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
    return flask.Response(json.dumps({"upload_token": token}), status=200)


# using the token from the start upload endpoint, post data given offset.
@app.route('/upload/continue/<token>', methods=['POST'])
def continue_file(token):
    token = secure_filename(token)
    print(token, file=sys.stderr)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    if os.path.isfile(tmppath):
        body = flask.request.get_json()
        if not body:
            return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
        offset = body['offset'] or 0
        if not 'data' in body:
            return flask.Response(json.dumps({"error": "File data not found in body"}), status=400)
        else:
            data = base64.b64decode(body['data'])
            f = open(tmppath, "ab")
            f.seek(int(offset))
            f.write(data)
            f.close()
            return flask.Response(json.dumps({"status": "OK"}), status=200)
    else:
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400)


# end the upload, by removing the in progress indication; locks further modification
@app.route('/upload/finish/<token>', methods=['POST', "GET"])
def finish_upload(token):
    body = flask.request.get_json()
    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
    token = secure_filename(token)
    filename = body['filename']
    if filename and allowed_file(filename):
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
        if not os.path.isfile(filepath):
            if os.path.isfile(tmppath):
                shutil.move(tmppath, filepath)
                return flask.Response(json.dumps({"ended": token, "filepath": filepath}))
            else:
                return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400)
        else:
            return flask.Response(json.dumps({"error": "File with name '" + filename + "' already exists"}), status=400)

    else:
        return flask.Response(json.dumps({"error": "Invalid filename"}), status=400)

    # check for token
    # get info associated with token
    # move the file out of temp to upload dir

# Delete the requested slide
@app.route('/slide/delete', methods=['POST'])
def slide_delete():
    body = flask.request.get_json()

    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
        
    filename = body['filename']
    if filename and allowed_file(filename):
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(filepath):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return flask.Response(json.dumps({"deleted": filename, "success": True})) 
        else:
            return flask.Response(json.dumps({"error": "File with name '" + filename + "' does not exist"}), status=400)

    else:
        return flask.Response(json.dumps({"error": "Invalid filename"}), status=400)

    # check for file if it exists or not
    # delete the file

@app.route("/test", methods=['GET'])
def testRoute():
    return '{"Status":"up"}'


@app.route("/data/one/<filepath>", methods=['GET'])
def singleSlide(filepath):
    return json.dumps(dev_utils.getMetadata(filepath, app.config['UPLOAD_FOLDER']))


@app.route("/data/thumbnail/<filepath>", methods=['GET'])
def singleThumb(filepath):
    size = flask.request.args.get('size', default=50, type=int)
    return json.dumps(getThumbnail(filepath, size))


@app.route("/data/many/<filepathlist>", methods=['GET'])
def multiSlide(filepathlist):
    return json.dumps(dev_utils.getMetadataList(json.loads(filepathlist), app.config['UPLOAD_FOLDER']))


@app.route("/getSlide/<image_name>")
def getSlide(image_name):
    if(os.path.isfile("/images/"+image_name)):
        return flask.send_from_directory(app.config["UPLOAD_FOLDER"], filename=image_name, as_attachment=True)
    else:
        return flask.Response(json.dumps({"error": "File does not exist"}), status=404)

# using the token from the start url upload endpoint
@app.route('/urlupload/continue/<token>', methods=['POST'])
def continue_urlfile(token):
    token = secure_filename(token)
    tmppath = os.path.join(app.config['TEMP_FOLDER'], token)
    if os.path.isfile(tmppath):
        body = flask.request.get_json()
        if not body:
            return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
        if not 'url' in body:
            return flask.Response(json.dumps({"error": "File url not present in body"}), status=400)
        else:
            url = body['url']
            try:
                url = urllib.parse.unquote(url)
                urllib.request.urlretrieve(url, tmppath)
                return flask.Response(json.dumps({"status": "OK Uploaded"}), status=200)
            except:
                return flask.Response(json.dumps({"error": "URL invalid"}), status=400)
    else:
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400)

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
        return flask.Response(json.dumps({"uploaded": "True"}), status=200)
    else:
        return flask.Response(json.dumps({"uploaded": "False"}), status=200)



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
            return flask.Response(json.dumps({'error': 'Not a valid zip file/files'}), status=400)
        with zipfile.ZipFile(tmppath, 'r') as zip_ref:
            zip_ref.extractall(tmppath[0:-4])
        csvFile = pathlib.Path(tmppath[0:-4]+'/patches.csv')
        if not csvFile.is_file():
            deleteDataset(userFolder)
            return flask.Response(json.dumps({'error': 'Not a valid labels zip/zips'}), status=400)
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
    return flask.Response(json.dumps(labelsData), status=200)


# Route to organise the extracted zip file data according to user sent customized labels and create a spritesheet
# Link to download the dataset.zip is sent back to the user
@app.route('/workbench/generateSprite', methods=['POST'])
def generateSprite():
    data = flask.request.get_json()
    userFolder = data['userFolder']
    labels = data['labels']
    included = data['included']
    fileNames = data['fileNames']
    for i in range(len(fileNames)):
        path = os.path.join(
            app.config['DATASET_FOLDER']+userFolder+'/', fileNames[i])[0:-4]
        csvFile = path+'/patches.csv'
        with open(csvFile, 'r') as data1:
            i = 0
            for line in csv.reader(data1):
                if i != 0 and line[2] != '':
                    if line[2] in labels:
                        if not os.path.isdir(app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'+line[2]):
                            os.makedirs(
                                app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'+line[2])
                        file = pathlib.Path(path+line[8][1:])
                        if not file.is_file():
                            deleteDataset(userFolder)
                            return flask.Response(json.dumps({'error': 'Images are missing from one or more zip files'}), status=400)
                        file = path+line[8][1:]
                        fileName = ''.join(random.choice(
                            string.ascii_lowercase + string.digits) for _ in range(40))
                        newFile = app.config['DATASET_FOLDER']+userFolder + \
                            '/spritesheet/'+line[2]+'/'+fileName+'.jpg'
                        shutil.move(file, newFile)
                i += 1
    createSpritesheet(app.config['DATASET_FOLDER']+userFolder, labels)
    zipObj = zipfile.ZipFile(
        app.config['DATASET_FOLDER']+userFolder+'/spritesheet/dataset.zip', 'w')
    zipObj.write(app.config['DATASET_FOLDER'] +
                 userFolder+'/spritesheet/data.jpg', '/data.jpg')
    zipObj.write(app.config['DATASET_FOLDER']+userFolder +
                 '/spritesheet/labels.bin', '/labels.bin')
    download_link = '/workbench/sprite/download/'+userFolder
    download_file(userFolder)
    return flask.Response(json.dumps({'status': 'done', 'userFolder': userFolder, 'download': download_link}), status=200)


# Dynamic download route for dataset.zip
@app.route('/workbench/sprite/download/<userFolder>')
def download_file(userFolder):
    path = app.config['DATASET_FOLDER']+userFolder+'/spritesheet/'
    return flask.send_from_directory(path, 'dataset.zip', as_attachment=True)


# To delete the the user-specific useless files after download is complete
@app.route('/workbench/deleteDataset/<userFolder>', methods=['POST'])
def deleteDataset(userFolder):
    if '/' in userFolder or '..' in userFolder or len(userFolder) != 20:
        return flask.Response(json.dumps({"deleted": "false", 'message': 'Traversal detected'}), status=403)
    shutil.rmtree(app.config['DATASET_FOLDER']+userFolder)
    return flask.Response(json.dumps({"deleted": "true"}), status=200)