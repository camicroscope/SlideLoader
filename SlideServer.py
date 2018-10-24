import openslide
import flask
import os
import json
import hashlib
import flask_cors
import sys
import random
import base64
import string
import shutil
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)
flask_cors.CORS(app)

# where to put and get slides
app.config['UPLOAD_FOLDER'] = "/data/images/"
app.config['TEMP_FOLDER'] = "/data/images/uploading/"
app.config['TOKEN_SIZE'] = 10
app.config['SECRET_KEY'] = os.urandom(24)

ALLOWED_EXTENSIONS = set(['svs','tif'])


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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# given a path, get metadata
def getMetadata(filename):
    # TODO consider restricting filepath
    metadata = {}
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(filepath):
        return {"error": "No such file"}
    metadata['filename'] = filepath
    try:
        slide = openslide.OpenSlide(filepath)
    except BaseException as e:
        return {"type": "Openslide", "error": str(e)}
    slideData = slide.properties
    metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
    metadata['mpp-y'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
    metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
    metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
    metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
    metadata['level_count'] = int(slideData.get('level_count', 1))
    metadata['objective'] = float(slideData.get("aperio.AppMag", None))
    metadata['md5sum'] = file_md5(filepath)
    return metadata

# given a list of path, get metadata for each
def getMetadataList(filenames):
    allData = []
    for filename in filenames:
        allData.append(getMetadata(filename))
    return allData

## routes

## start a file upload by registering the intent to upload, get a token to be used in future upload requests
@app.route('/upload/start', methods=['POST'])
def start_upload():
    token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
    token = secure_filename(token)
    tmppath =  os.path.join(app.config['TEMP_FOLDER'], token)
    # regenerate if we happen to collide
    while os.path.isfile(tmppath):
        token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
        token = secure_filename(token)
        tmppath =  os.path.join(app.config['TEMP_FOLDER'], token)
    f = open(tmppath, 'a')
    f.close()
    return flask.Response(json.dumps({"upload_token": token}), status=200)

## using the token from the start upload endpoint, post data given offset.
@app.route('/upload/continue/<token>', methods=['POST'])
def continue_file(token):
    token = secure_filename(token)
    print(token, file=sys.stderr)
    tmppath =  os.path.join(app.config['TEMP_FOLDER'], token)
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


## end the upload, by removing the in progress indication; locks further modification
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
        tmppath =  os.path.join(app.config['TEMP_FOLDER'], token)
        if not os.path.isfile(filepath):
            if os.path.isfile(tmppath):
                shutil.move(tmppath, filepath)
                return flask.Response(json.dumps({"ended": token, "filepath": filepath}))
            else:
                return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400)
        else:
            return flask.Response(json.dumps({"error": "Invalid filename"}), status=400)

    else:
        return flask.Response(json.dumps({"error": "Invalid filename"}), status=400)


    # check for token
    # get info associated with token
    # move the file out of temp to upload dir


@app.route("/test", methods=['GET'])
def testRoute():
    return '{"Status":"up"}'

@app.route("/data/one/<filepath>", methods=['GET'])
def singleSlide(filepath):
    return json.dumps(getMetadata(filepath))

@app.route("/data/many/<filepathlist>", methods=['GET'])
def multiSlide(filepathlist):
    return json.dumps(getMetadataList(json.loads(filepathlist)))
