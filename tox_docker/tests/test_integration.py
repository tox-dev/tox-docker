from contextlib import contextmanager
from unittest.mock import patch
from urllib.request import urlopen
import os
import sys
import unittest

from tox_docker import _get_gateway_ip


class ToxDockerIntegrationTest(unittest.TestCase):
    def test_it_sets_automatic_env_vars(self):
        # ksdn117/tcp-udp-test exposes TCP port 1234 and UDP port 5678
        self.assertIn("TCP_UDP_TEST_1234_TCP_PORT", os.environ)
        self.assertIn("TCP_UDP_TEST_5678_UDP_PORT", os.environ)

    def test_it_exposes_the_port(self):
        self.assertIn("NGINX_FROM_REGISTRY_URL_HOST", os.environ)
        self.assertIn("NGINX_FROM_REGISTRY_URL_80_TCP_PORT", os.environ)

        host = os.environ["NGINX_FROM_REGISTRY_URL_HOST"]
        port = os.environ["NGINX_FROM_REGISTRY_URL_80_TCP_PORT"]

        response = urlopen(f"http://{host}:{port}/")
        self.assertEqual(200, response.getcode())
        self.assertIn(b"Thank you for using nginx.", response.read())


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
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4"}}

        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

        with sys_platform_as("darwin"):
            self.assertEqual(_get_gateway_ip(container), "0.0.0.0")


class GatewayIpTest(unittest.TestCase):
    def test_gateway_ip_env_override(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4"}}

        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

            with patch.dict("os.environ", {"TOX_DOCKER_GATEWAY": "192.168.1.1"}):
                self.assertEqual(_get_gateway_ip(container), "192.168.1.1")

            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

    def test_gateway_host_env_override(self):
        class NotARealContainer(object):
            attrs = {"NetworkSettings": {"Gateway": "1.2.3.4"}}

        container = NotARealContainer()

        with sys_platform_as("linux2"):
            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")

            with patch.dict("os.environ", {"TOX_DOCKER_GATEWAY": "localhost"}):
                self.assertIn(_get_gateway_ip(container), ["127.0.0.1", "::1"])

            self.assertEqual(_get_gateway_ip(container), "1.2.3.4")
