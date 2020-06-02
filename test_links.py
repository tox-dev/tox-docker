import os
import unittest

import docker
from tox_docker import _validate_link_line


class ToxDockerLinksTest(unittest.TestCase):

    def test_links_created(self):
        client = docker.from_env(version="auto")
        httpd_container = None
        registry_container = None
        nginx_container = None
        for container in client.containers.list():
            if httpd_container is None and "httpd" in container.attrs['Config']['Image']:
                httpd_container = container

            if registry_container is None and "registry" in container.attrs['Config']['Image']:
                registry_container = container
            
            if nginx_container is None and "nginx" in container.attrs['Config']['Image']:
                nginx_container = container
            
            if all([httpd_container, registry_container, nginx_container]):
                break

        self.assertIsNotNone(httpd_container, "could not find httpd container")
        self.assertIsNotNone(registry_container, "could not find registry container")
        self.assertIsNotNone(nginx_container, "could not find nginx container")
        
        httpd_name = httpd_container.attrs["Name"]
        registry_name = registry_container.attrs["Name"]
        nginx_name = nginx_container.attrs["Name"]
        
        httpd_links = httpd_container.attrs["HostConfig"]["Links"]
        registry_links = registry_container.attrs["HostConfig"]["Links"]
        nginx_links = nginx_container.attrs["HostConfig"]["Links"]
        
        self.assertIsNone(httpd_links)
        
        expected_registry_links = [
            "{}:{}/apache".format(httpd_name, registry_name)
        ]
        self.assertEqual(expected_registry_links, registry_links)
        
        expected_nginx_links = [
            "{}:{}/apache".format(httpd_name, nginx_name),
            "{}:{}/hub".format(registry_name, nginx_name)
        ]
        self.assertEqual(sorted(expected_nginx_links), sorted(nginx_links))

    def test_links_work(self):
        client = docker.from_env(version="auto")
        registry_container = None
        nginx_container = None
        for container in client.containers.list():
            if registry_container is None and "registry" in container.attrs['Config']['Image']:
                registry_container = container

            if nginx_container is None and "nginx" in container.attrs['Config']['Image']:
                nginx_container = container
            
            if all([registry_container, nginx_container]):
                break

        self.assertIsNotNone(registry_container)
        self.assertIsNotNone(nginx_container)
        
        self.assertEqual(registry_container.exec_run("ping -c 1 apache")[0], 0)
        self.assertEqual(nginx_container.exec_run("curl --noproxy '*' http://hub:5000")[0], 0)
        self.assertEqual(nginx_container.exec_run("curl --noproxy '*' http://apache")[0], 0)

    def test_validate_link_line_requires_alias(self):
        for line in (
            'some-image-name',
            'some-image-name:',
        ):
            with self.assertRaises(ValueError) as cm:
                _validate_link_line(line)
            self.assertEqual("Linked to 'some-image-name' container without specifying an alias.")
