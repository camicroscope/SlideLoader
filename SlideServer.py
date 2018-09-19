import openslide
import flask
from werkzeug.utils import secure_filename

app = flask.Flask(__name__)

# where to put slides
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['svs','tif'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# given a path, get metadata
def getMetadata(filename):
    metadata = {}
    metadata['filename'] = filename
    slide = openslide.OpenSlide(filename)
    slideData = slide.properties
    metadata['mpp-x'] = slideData.get(openslide.PROPERTY_NAME_MPP_X, None)
    metadata['mpp-y'] = slideData.get(openslide.PROPERTY_NAME_MPP_Y, None)
    metadata['height'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_HEIGHT, None)
    metadata['width'] = slideData.get(openslide.PROPERTY_NAME_BOUNDS_WIDTH, None)
    metadata['vendor'] = slideData.get(openslide.PROPERTY_NAME_VENDOR, None)
    metadata['level_count'] = int(slideData.get('level_count', 1))
    metadata['objective'] = float(slideData.get("aperio.AppMag", None))
    metadata['md5sum'] = file_md5(filename)
    return metadata

# given a list of path, get metadata for each
def getMetadataList(filenames):
    allData = []
    for filename in filenames:
        allData.append(getMetadata(filename))
    return allData

## routes

# upload, graciously stolen from pocoo
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
        file.save(filepath, filename))
        return filepath

@app.route("/data/one")
def uploadSlide():
    pass

@app.route("/data/many")
def uploadSlide():
    pass
