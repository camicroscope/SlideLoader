import openslide
import flask
import os
import json
import hashlib
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)

# where to put and get slides
app.config['UPLOAD_FOLDER'] = "/data/images/"

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
@app.route('/upload', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    if 'file' not in flask.request.files:
        flask.flash("No file part")
        return flask.redirect(request.url)
    file = flask.request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return flask.redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath, filename)
        return filepath

@app.route("/test", methods=['GET'])
def testRoute():
    return '{"Status":"up"}'

@app.route("/data/one/<filepath>", methods=['GET'])
def singleSlide(filepath):
    return json.dumps(getMetadata(filepath))

@app.route("/data/many/<filepathlist>", methods=['GET'])
def multiSlide(filepathlist):
    return json.dumps(getMetadataList(json.loads(filepathlist)))
