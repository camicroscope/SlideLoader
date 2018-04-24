import requests, re

class Requester(object):
    # using options...
    # check the check route
    def __init__(self, config):
        self.config = config
        # relevant config options
        self.checkUrl = self.config['exist_check_url']
        self.record_uri_key = self.config.get("record_uri_key", "id")
        self.apiKey = self.config.get("api_key", "")
        self.existsRegex = self.confing.get("exist_check_test", "[]")
        self.postUrl = self.config['post_url']
        self.record_manifest_key = self.config.get("record_manifest_key", self.record_uri_key)
        self.dry_run = self.config.get("dry_run", None)

    def request(self, payLoad):
        exists = False
        if self.checkUrl:
            url = self.checkUrl + "?" + self.record_uri_key + "=" + payLoad[self.record_manifest_key] +"&api_key=" + self.apiKey
            check = requests.get(url)
            if re.search(self.existsRegex, check.text) is not None:
                exists = True
                print (payLoad[self.record_manifest_key] + " exists already")
            else:
                exists = False
        else :
            exists = False
        # if not, post to post route
        if not exists:
            headers = {'api_key': self.apiKey}
            url = self.postUrl
            if not self.dry_run:
                r = requests.post(url, json=payLoad, headers=headers)
                # log if error
                if r.status_code < 300:
                    # success
                else:
                    print("ERROR :"  + url )
                return r.text
            else:
                # just say what we're doing
                print("POST: " + url + str(payLoad) + str(headers))
