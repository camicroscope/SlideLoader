import json
from six.moves.urllib.request import urlopen
from functools import wraps
# from SlideServer import app
import flask
from os import listdir
from os.path import isfile, join
import os

from flask import Flask, request, jsonify, _request_ctx_stack
from flask_cors import cross_origin
from jose import jwt

AUTH0_DOMAIN = False 
API_AUDIENCE = False
ALGORITHMS = ["RS256"]
DISABLE_SEC = False # Change to "True" for testing  


# Format error response and append status code
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                            "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must be"
                            " Bearer token"}, 401)

    token = parts[1]
    return token

# Error handler
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'

def requires_auth(access_level):
    """Determines if the Access Token is valid
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if DISABLE_SEC:

                if (flask.request.cookies.get('token')):
                    token = flask.request.cookies.get('token')
                    mypath = './keys/'
                    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
                    if 'key.pub' in onlyfiles:
                        public_key = open('./keys/key.pub', mode='r', encoding='utf-8').read()
                    else:
                        public_key = False
                    try:
                        payload = jwt.decode(token, public_key, algorithms=['RS256'])
                        
                        if str(payload["userType"]) not in access_level:                   
                            raise AuthError({"code": "invalid_usertype",
                                            "description": "You are not authorized for this action"}, 403)

                    except jwt.ExpiredSignatureError:
                        raise AuthError({"code": "token_expired",
                                        "description": "token is expired"}, 401)
                    except jwt.JWTClaimsError:
                        raise AuthError({"code": "invalid_claims",
                                        "description":
                                            "incorrect claims,"
                                            "please check the audience and issuer"}, 401)
                    except Exception as e:
                        raise AuthError({"code": "invalid_header",
                                        "description":
                                            "Unable to parse authentication"
                                            " token.", 
                                        "error": str(e)}, 401)
                    _request_ctx_stack.top.current_user = payload
                    return f(*args, **kwargs)

                else:
                    raise AuthError({"code": "invalid_header",
                                        "description":
                                            "Did not receive authentication"
                                            " token."}, 401)

            else:
                return f(*args, **kwargs)

        return decorated
    return decorator



# 