import unittest

import pytest

from tox_docker import _validate_link_line
from tox_docker.tests.util import find_container


class ToxDockerLinksTest(unittest.TestCase):
    def test_links_created(self):
        httpd_container = find_container("links-httpd")
        registry_container = find_container("links-registry")
        nginx_container = find_container("links-nginx")

        # TODO: figure out why docker prepends / to the Name attribute,
        # and fix the handling here if we're doing something wrong...
        httpd_name = httpd_container.attrs["Name"].lstrip("/")
        registry_name = registry_container.attrs["Name"].lstrip("/")
        nginx_name = nginx_container.attrs["Name"].lstrip("/")

        httpd_links = httpd_container.attrs["HostConfig"]["Links"]
        registry_links = registry_container.attrs["HostConfig"]["Links"]
        nginx_links = nginx_container.attrs["HostConfig"]["Links"]

        self.assertIsNone(httpd_links)

        expected_registry_links = [f"/{httpd_name}:/{registry_name}/apache"]
        self.assertEqual(expected_registry_links, registry_links)

        expected_nginx_links = [
            f"/{httpd_name}:/{nginx_name}/{httpd_name}",
            f"/{registry_name}:/{nginx_name}/hub",
        ]
        self.assertEqual(sorted(expected_nginx_links), sorted(nginx_links))

    def test_links_work(self):
        registry_container = find_container("links-registry")
        nginx_container = find_container("links-nginx")

        self.assertIsNotNone(registry_container)
        self.assertIsNotNone(nginx_container)

        self.assertEqual(registry_container.exec_run("ping -c 1 apache")[0], 0)
        self.assertEqual(
            nginx_container.exec_run("curl --noproxy '*' http://hub:5000")[0], 0
        )
        self.assertEqual(
            nginx_container.exec_run("curl --noproxy '*' http://links-httpd")[0], 0
        )

    def test_validate_link_line(self):
        names = {"httpd"}
        assert _validate_link_line("httpd:apache", names) == ("httpd", "apache")
        assert _validate_link_line("httpd", names) == ("httpd", "httpd")

    def test_validate_link_line_rejects_dangling_comma(self):
        names = {"httpd"}
        with pytest.raises(ValueError):
            _validate_link_line("httpd:", names)
        with pytest.raises(ValueError):
            _validate_link_line("httpd", set())
