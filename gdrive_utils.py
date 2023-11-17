from threading import Thread
from gDriveDownload import start, afterUrlAuth, callApi
import flask
import os
import random
import string
from werkzeug.utils import secure_filename
import sys

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

def gDriveGetFile(body):
    token = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    token = secure_filename(token)
    tmppath = os.path.join("/images/uploading/", token)
    # regenerate if we happen to collide
    while os.path.isfile(tmppath):
        token = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        token = secure_filename(token)
        tmppath = os.path.join("/images/uploading/", token)

    try:
        params = start(body['userId'])
    except:
        return flask.Response(json.dumps({'error': str(sys.exc_info()[0])}), status=400)
    thread_a = getFileFromGdrive(params, body['userId'], body['fileId'], token)
    thread_a.start()
    return flask.Response(json.dumps({"authURL": params["auth_url"], "token": token}), status=200)

def checkDownloadStatus(body):
    token = body['token']
    path = app.config['TEMP_FOLDER']+'/'+token
    if os.path.isfile(path):
        return flask.Response(json.dumps({"downloadDone": True}), status=200)
    return flask.Response(json.dumps({"downloadDone": False}), status=200)