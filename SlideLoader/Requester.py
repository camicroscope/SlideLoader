import requests

class Requester(object):
    # using options...
    # check the check route
    check = requests.get(url + "?" + key + "=" + slideid +"&api_key=" + )
    check.text
    # log if present
    # if not, post to post route
    headers = {'api_key': apiKey}
    requests.post(url, json=payLoad, headers=headers)
    # log if error
    r.status_code
    # (error log should be usable as a retry manifest)
