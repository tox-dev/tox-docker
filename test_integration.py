import os
import unittest

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


class ToxDockerIntegrationTest(unittest.TestCase):
    # TODO: These tests depend too heavily on what's in tox.ini,
    # but they're better than nothing

    def test_it_sets_specific_env_vars(self):
        self.assertEqual("env-var-value", os.environ["ENV_VAR"])

    def test_it_sets_automatic_env_vars(self):
        # the nginx image we use exposes port 80
        self.assertIn("NGINX_HOST", os.environ)
        self.assertIn("NGINX_80_TCP", os.environ)
        self.assertIn("NGINX_80_TCP_PORT", os.environ)
        self.assertEqual(
            os.environ["NGINX_80_TCP_PORT"],
            os.environ["NGINX_80_TCP"],
        )

        # the test image we use exposes TCP port 1234 and UDP port 5678
        self.assertIn("KSDN117_TCP_UDP_TEST_1234_TCP", os.environ)
        self.assertIn("KSDN117_TCP_UDP_TEST_1234_TCP_PORT", os.environ)
        self.assertEqual(
            os.environ["KSDN117_TCP_UDP_TEST_1234_TCP_PORT"],
            os.environ["KSDN117_TCP_UDP_TEST_1234_TCP"],
        )
        self.assertIn("KSDN117_TCP_UDP_TEST_5678_UDP_PORT", os.environ)
        self.assertEqual(
            os.environ["KSDN117_TCP_UDP_TEST_5678_UDP_PORT"],
            os.environ["KSDN117_TCP_UDP_TEST_5678_UDP"],
        )

    def test_it_exposes_the_port(self):
        # the nginx image we use exposes port 80
        url = "http://{host}:{port}/".format(host=os.environ["NGINX_HOST"], port=os.environ["NGINX_80_TCP"])
        response = urlopen(url)
        self.assertEqual(200, response.getcode())
        self.assertIn("Thank you for using nginx.", str(response.read()))
