import requests
import json
import random
import time

class Client:

    def __init__(self, url, verify_cert=True):
        self.storage_url = url + "/affirmative/store"
        self.verify_cert = verify_cert

    def affirm_one(self, name, data):
        payload = {
            "events": [
                {"name": name, "time": time.time(), "data": data}
            ]
        }
        headers = {'content-type': 'application/json'}
        requests.post(
            self.storage_url,
            data=json.dumps(payload),
            headers=headers,
            verify=self.verify_cert,
            timeout=.1
        )
