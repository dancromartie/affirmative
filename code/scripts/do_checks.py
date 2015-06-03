import requests
import sys
import time

seconds_per_check = 60
if len(sys.argv) > 1:
    seconds_per_check = int(sys.argv[1])

url = "http://localhost:5123/affirmative/do_minutely_cron"
for i in xrange(1000):
    print "making request..."
    requests.get(url)
    print "done"
    time.sleep(60)
