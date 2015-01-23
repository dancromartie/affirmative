import requests
import json
import random
from datetime import datetime
import time

# These variables should be set in your app's config or startup scripts.  Ain't my problem!
APP_ENV = "prod"
AFFIRMATIVE_URL = "http://localhost:5123/affirmative/store"

def affirm(name, data):
    try:
        utc_datetime = datetime.utcnow()
        now_ts = utc_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        print now_ts
        payload = {"events": [{"env": APP_ENV, "name": name, "time": now_ts, "data": data}]}
        requests.post(BROCOLLI_URL, data=json.dumps(payload), timeout=.1)
    except Exception, e:
        print "woops, something went wrong"







#########################################
################USAGE###################
for i in range(1, 100):
    # here's a string
    affirm("my_apps_health_checks", "good")
    # a number
    affirm("wrote_unit_test", "good")

    time.sleep(.05)
