import base64
import json
import os
import random
import shutil
import string
import sys
import pyvips
import urllib
import flask
import flask_cors
import openslide
from werkzeug.utils import secure_filename
import dev_utils

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO

app = flask.Flask(__name__)
flask_cors.CORS(app)

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



class upload():
    uploadedStatus = "False"
uploadStatus = upload();

# using the token from the start url upload endpoint
@app.route('/urlupload/continue/<token>', methods=['POST'])
def continue_urlfile(token):
    uploadStatus.uploadedStatus = "False"
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
            uploadStatus.uploadedStatus = "False"
            try:
                url = urllib.parse.unquote(url)
                urllib.request.urlretrieve(url, tmppath)
                uploadStatus.uploadedStatus = "True"
                return flask.Response(json.dumps({"status": "OK Uploaded"}), status=200)
            except:
                return flask.Response(json.dumps({"status": "URL invalid"}), status=400)
    else:
        return flask.Response(json.dumps({"error": "Token Not Recognised"}), status=400)


@app.route('/urlupload/check', methods=['GET'])
def urlUploadStatus():
    if(uploadStatus.uploadedStatus=="True"):
        uploadStatus.uploadedStatus=="False"
        return flask.Response(json.dumps({"uploaded": "True"}), status=200)
    return flask.Response(json.dumps({"uploaded": "False"}), status=200)
