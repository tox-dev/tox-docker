from contextlib import contextmanager
import os
import sys
import unittest
from unittest.mock import patch

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from tox_docker import _get_gateway_ip


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


@contextmanager
def sys_platform_as(value):
    old_value = sys.platform
    sys.platform = value
    try:
        yield
    finally:
        sys.platform = old_value


class MacOSTest(unittest.TestCase):

    def test_gateway_ip_is_zero_zero_zero_zero(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4", }}
        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

        with sys_platform_as("darwin"):
            self.assertEqual(_get_gateway_ip(container), "0.0.0.0")


class GatewayIpTest(unittest.TestCase):
    def test_gateway_ip_env_override(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4", }}
        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

            with patch.dict('os.environ', {'TOX_DOCKER_GATEWAY_IP': '192.168.1.1'}):
                self.assertEqual(_get_gateway_ip(container), "192.168.1.1")

            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

    def test_gateway_host_env_override(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4", }}
        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

            with patch.dict('os.environ', {'TOX_DOCKER_GATEWAY_HOST': 'localhost'}):
                self.assertIn(_get_gateway_ip(container), ['127.0.0.1', '::1'])

            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

    def test_gateway_ip_and_host_env_override(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4", }}
        container = NotARealContainer()

        with patch.dict('os.environ', {'TOX_DOCKER_GATEWAY_HOST': 'localhost', 'TOX_DOCKER_GATEWAY_IP': '192.168.1.1'}):
            with self.assertRaises(RuntimeException):
                _get_gateway_ip(container)
