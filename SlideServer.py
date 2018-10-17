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
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)
flask_cors.CORS(app)

# where to put and get slides
app.config['UPLOAD_FOLDER'] = "/data/images/"
app.config['TOKEN_SIZE'] = 10
app.config['SECRET_KEY'] = os.urandom(24)

ALLOWED_EXTENSIONS = set(['svs','tif'])

__IN_PROGRESS = {}

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
    slide = openslide.OpenSlide(filepath)
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

# upload, file as file:
@app.route('/upload', methods=['POST', "GET"])
def upload_file():
    if flask.request.method == "GET":
        return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload>
        </form>
        '''
    # check if the post request has the file part
    if 'file' not in flask.request.files:
        return flask.Response(json.dumps({"error": "NOT UPLOADED: No File"}), status=400)
    file = flask.request.files['file']
    filename = flask.request.form.get("filename", file.filename)
    if filename == '':
        return flask.Response(json.dumps({"error": "NOT UPLOADED: No Filename Given"}), status=400)
    if file and allowed_file(filename):
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(filepath):
            file.save(filepath)
            return json.dumps({"file":filepath})
        else:
            return flask.Response(json.dumps({"error": "NOT UPLOADED: File Exists"}), status=400)
    else:
        return flask.Response(json.dumps({"error": "NOT UPLOADED: Server Error"}), status=500)

## start a file upload by registering the intent to upload, get a token to be used in future upload requests
@app.route('/start/upload', methods=['POST'])
def start_upload():
    body = flask.request.get_json()
    if not body:
        return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
    key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
    # regenrate if we happen to collide
    while key in __IN_PROGRESS:
        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(app.config['TOKEN_SIZE']))
    # check filename
    filename = body['filename']
    if filename and allowed_file(filename):
        filename = secure_filename(filename)
        if not os.path.isfile(filepath):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # register token info
            __IN_PROGRESS[key] = {'filepath': filepath, 'last_seen_offset':none}
            # create empty file
            open(filepath, 'a').close()
            return flask.Response(json.dumps({"upload_token": key}), status=200)
        else:
            # BAD FILEPATH
            return flask.Response(json.dumps({"error": "Bad or unallowed filepath: " + filepath}), status=400)
    else:
        # MISSING FILE INFO
        return flask.Response(json.dumps({"error": "Filename missing or not allowed"}), status=400)

## using the token from the start upload endpoint, post data given offset.
@app.route('/upload/continue/<token>', methods=['POST', "GET"])
def continue_file(token):
    if flask.request.method == "GET":
        if token in __IN_PROGRESS:
            return flask.Response(json.dumps(__IN_PROGRESS[token]))
        else:
            return flask.Response(json.dumps({"error": "Token not recognized"}), status=400)
    else:
        if token in __IN_PROGRESS:
            body = flask.request.get_json()
            if not body:
                return flask.Response(json.dumps({"error": "Missing JSON body"}), status=400)
            offset = body.offset or 0
            if not data in body:
                return flask.Response(json.dumps({"error": "File data not found in body"}), status=400)
            data = base64.b64decode(body.data)
            process = __IN_PROGRESS[token]
            if not os.path.isfile(filepath):
                return flask.Response(json.dumps({"error": "File is missing from server"}), status=500)
            f = open(process['filepath'], "wb")
            f.seek(offset)
            f.write(data)
            f.close()
            __IN_PROGRESS['last_seen_offset'] = offset
        else:
            return flask.Response(json.dumps({"error": "Token not recognized"}), status=400)

## end the upload, by removing the in progress indication; locks further modification
@app.route('/upload/finish/<token>', methods=['POST', "GET"])
def finish_upload(token):
    if token in __IN_PROGRESS:
        s = __IN_PROGRESS[token]
        del __IN_PROGRESS[token]
        return flask.Response(json.dumps({"ended": s}))
    else:
        return flask.Response(json.dumps({"error": "Token not recognized"}), status=400)


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
