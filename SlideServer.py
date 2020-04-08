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
from auth.authHandler import requires_auth, AuthError

import flask
import flask_cors
import openslide
from werkzeug.utils import secure_filename
import dev_utils

from functools import wraps

from flask import Flask, request, jsonify, _request_ctx_stack
from flask_cors import cross_origin
from jose import jwt

AUTH0_DOMAIN = 'YOUR_DOMAIN'
API_AUDIENCE = False
ALGORITHMS = ["RS256"]



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

# Delete the requested slide
@app.route('/slide/delete', methods=['POST'])
@requires_auth(access_level=["Admin"])
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
            return flask.Response(json.dumps({"error": "File with name '" + filename + "' does not exists"}), status=400)

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
            

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response