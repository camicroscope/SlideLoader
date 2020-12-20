from __future__ import print_function
import pickle
import wsgiref.simple_server
import wsgiref.util
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, _WSGIRequestHandler, _RedirectWSGIApp
from google.auth.transport.requests import Request
import sys
import os
import io
import shutil


# If modifying these scopes, delete the file "googleDrive<userID>.pickle"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Starting a local server on :4001 to listen for authentication response from user
def run_local_server(
    self=InstalledAppFlow,
    host="0.0.0.0",
    port=4001,
    authorization_prompt_message=InstalledAppFlow._DEFAULT_AUTH_PROMPT_MESSAGE,
    success_message=InstalledAppFlow._DEFAULT_WEB_SUCCESS_MESSAGE,
    userId=None,
):
    wsgi_app = _RedirectWSGIApp(success_message)
    local_server = wsgiref.simple_server.make_server(host, port, wsgi_app, handler_class=_WSGIRequestHandler)

    # Making a unique redirect URL for every user 
    self.redirect_uri = "http://localhost:4010/googleAuth/" + userId
    auth_url, _ = self.authorization_url()

    print(authorization_prompt_message.format(url=auth_url))

    return auth_url, local_server, wsgi_app, None


# Will be called after return of Auth URL
def afterUrlAuth(local_server, flow, wsgi_app, userId):
    local_server.handle_request()

    # Note: using https here because oauthlib is very picky that
    # OAuth 2.0 should only occur over https.
    authorization_response = wsgi_app.last_request_uri.replace("http", "https")
    flow.fetch_token(authorization_response=authorization_response)
    # Save the credentials for the next run
    with open(
        "/cloud-upload-apis/tokens/googleDrive" + userId + ".pickle", "wb"
    ) as token:
        pickle.dump(flow.credentials, token)
    return flow.credentials

# Starting the Auth process and checking for pickle file (Token) [Creating a new token if not exists]
def start(userId):
    creds = None
    # The file "googleDrive<userID>.pickle" stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("/cloud-upload-apis/tokens/googleDrive" + userId + ".pickle"):
        with open(
            "/cloud-upload-apis/tokens/googleDrive" + userId + ".pickle", "rb"
        ) as token:
            creds = pickle.load(token)
        return None, None, None, None, creds
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "/cloud-upload-apis/credentials/google-drive.json", SCOPES
            )
            auth_url, local_server, wsgi_app, creds = run_local_server(
                self=flow, userId=userId
            )
            return {
                "auth_url": auth_url,
                "local_server": local_server,
                "wsgi_app": wsgi_app,
                "flow": flow,
                "creds": creds,
            }


# Calling the Drive API to download a file
def callApi(creds, fileId, token):
    downloadDone = False
    service = build("drive", "v3", credentials=creds)

    # Call the Drive v3 API
    request = service.files().get_media(fileId=fileId)
    fileName = service.files().get(fileId=fileId).execute()["name"]

    fh = io.BytesIO()

    # Initialise a downloader object to download the file
    downloader = MediaIoBaseDownload(fh, request)

    try:
        # Download the data in chunks
        while not downloadDone:
            status, downloadDone = downloader.next_chunk()
        fh.seek(0)
        # Write the received data to the file
        with open("/images/uploading/" + token, "wb") as f:
            shutil.copyfileobj(fh, f)

        # Return True if file Downloaded successfully
        return {"status": True, "fileName": fileName, "token": token}
    except:
        return False
