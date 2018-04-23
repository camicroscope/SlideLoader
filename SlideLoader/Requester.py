import requests

class Requester(object):
    # using options...
    # check the check route
    def __init__(self, config):
        self.config = config
        # relevant config options
        self.checkUrl = self.config['exist_check_url']
        self.checkKey = self.config.get("exist_check_param", "id")
        self.apiKey = self.config.get("api_key", "")

    def request(self, payLoad):
        exists = False
        if self.checkUrl:
            check = requests.get(self.checkUrl + "?" + self.checkKey + "=" + payLoad['tissueID'] +"&api_key=" + self.apiKey)
            check.text
            if blah:
                exists = True
                # log it
            else:
                exists = False
        else :
            exists = False
        # if not, post to post route
        if not exists:
            headers = {'api_key': self.apiKey}
            requests.post(url, json=payLoad, headers=headers)
            # log if error
            r.status_code
            # (error log should be usable as a retry manifest)
