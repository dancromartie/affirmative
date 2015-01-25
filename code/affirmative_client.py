import requests
import json
import random
from datetime import datetime
import time

class Client:

    def __init__(self, url, environment):
        self.storage_url = url + "/affirmative/store"
        self.environment = environment

    def affirm_one(self, name, data):
        utc_datetime = datetime.utcnow()
        now_ts = utc_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        payload = {
            "events": [
                {"env": self.environment, "name": name, "time": time.time(), "data": data}
            ]
        }
        headers = {'content-type': 'application/json'}
        requests.post(self.storage_url, data=json.dumps(payload), headers=headers, timeout=.1)
