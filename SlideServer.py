import openslide
import flask
import os
import json
import hashlib
import flask_cors
import sys
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)
flask_cors.CORS(app)

# where to put and get slides
app.config['UPLOAD_FOLDER'] = "/data/images/"
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
    print(flask.request, file=sys.stderr)
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


@app.route("/test", methods=['GET'])
def testRoute():
    return '{"Status":"up"}'

@app.route("/data/one/<filepath>", methods=['GET'])
def singleSlide(filepath):
    return json.dumps(getMetadata(filepath))

@app.route("/data/many/<filepathlist>", methods=['GET'])
def multiSlide(filepathlist):
    return json.dumps(getMetadataList(json.loads(filepathlist)))
