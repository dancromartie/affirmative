import time

import affirmative_client

ac = affirmative_client.Client("http://localhost:5123", verify_cert=False)
for i in range(1, 100):
    print "sending!"
    ac.affirm_one("that_critical_app_health_check", "good")
    ac.affirm_one("sometest", "good")
    time.sleep(.05)
