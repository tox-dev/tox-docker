import os
import unittest

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


class ToxDockerRegistryTest(unittest.TestCase):
    def test_it_sets_specific_env_vars(self):
        self.assertEqual("env-var-value", os.environ["ENV_VAR"])

    def test_it_sets_automatic_env_vars(self):
        # the nginx image we use exposes port 80
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_HOST", os.environ)
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_80_TCP", os.environ)

    def test_it_exposes_the_port(self):
        # the nginx image we use exposes port 80
        url = "http://{host}:{port}/".format(host=os.environ["DOCKER_IO_LIBRARY_NGINX_HOST"], port=os.environ["DOCKER_IO_LIBRARY_NGINX_80_TCP"])
        response = urlopen(url)
        self.assertEqual(200, response.getcode())
        self.assertIn("Thank you for using nginx.", str(response.read()))
