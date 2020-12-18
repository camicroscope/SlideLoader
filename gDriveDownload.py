from __future__ import print_function
import pickle
import os.path
import wsgiref.simple_server
import wsgiref.util
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow, _WSGIRequestHandler, _RedirectWSGIApp
from google.auth.transport.requests import Request
import sys
import os

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def run_local_server(
    self=InstalledAppFlow,
    host="0.0.0.0",
    port=4001,
    authorization_prompt_message=InstalledAppFlow._DEFAULT_AUTH_PROMPT_MESSAGE,
    success_message=InstalledAppFlow._DEFAULT_WEB_SUCCESS_MESSAGE,
):
    wsgi_app = _RedirectWSGIApp(success_message)
    local_server = wsgiref.simple_server.make_server(
        host, port, wsgi_app, handler_class=_WSGIRequestHandler
    )

    self.redirect_uri = "http://localhost:4010/googleAuth/"
    auth_url, _ = self.authorization_url()


    print(authorization_prompt_message.format(url=auth_url))

    return auth_url, local_server, wsgi_app, None

def afterUrlAuth(local_server, flow, wsgi_app):
    local_server.handle_request()

    # Note: using https here because oauthlib is very picky that
    # OAuth 2.0 should only occur over https.
    authorization_response = wsgi_app.last_request_uri.replace("http", "https")
    flow.fetch_token(authorization_response=authorization_response)
            # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(flow.credentials, token)
    return flow.credentials

def startDownload():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        return None, None, None, None, creds
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                './credentials/google-drive.json', SCOPES)
            auth_url, local_server, wsgi_app, creds = run_local_server(self=flow)
            return auth_url, local_server, wsgi_app, flow, creds
            # creds = afterUrlAuth(local_server, flow, wsgi_app)
            


def callApi(creds):
    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
        return items
    else:
        print('Files:')
        return items
        # for item in items:
        #     print(u'{0} ({1})'.format(item['name'], item['id']))



# startDownload()
