import requests
import time

url = "http://localhost:5123/affirmative/simplest"
for i in range(1, 100):
    print "sending!"
    data = {"event_name": "sometest"}
    requests.post(url, data=data, verify=False)
    time.sleep(.05)
