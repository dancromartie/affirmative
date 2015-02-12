import unittest
import subprocess
import os
import time

proc_string = "TESTjs9u3ij3ojd"
instance_name = proc_string
port = 5124

print "starting webserver..."
pid = subprocess.Popen(["./start_dev.sh", str(port), instance_name, proc_string]).pid
print "waiting a little..."
time.sleep(3)

class TestMyApp(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        print "stopping webserver..."
        subprocess.call(["pkill", "-f", proc_string])
        time.sleep(1)

    def test_data_fetch(self):
        self.assertTrue(5 == 5)

    def test_other_func(self):
        self.assertTrue(5 == 5)

if __name__ == '__main__':
    unittest.main()
