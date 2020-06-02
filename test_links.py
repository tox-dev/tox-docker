import os
import unittest

import docker
from tox_docker import _validate_link_line


class ToxDockerLinksTest(unittest.TestCase):

    def test_links_created(self):
        client = docker.from_env(version="auto")
        postgres_container = None
        memcached_container = None
        elasticsearch_container = None
        for container in client.containers.list():
            if postgres_container is None and "postgres" in container.attrs['Config']['Image']:
                postgres_container = container
            
            if memcached_container is None and "memcached" in container.attrs['Config']['Image']:
                memcached_container = container
            
            if elasticsearch_container is None and "elasticsearch" in container.attrs['Config']['Image']:
                elasticsearch_container = container
            
            if all([postgres_container, memcached_container, elasticsearch_container]):
                break

        self.assertIsNotNone(postgres_container, "could not find postgres container")
        self.assertIsNotNone(memcached_container, "could not find memcached container")
        self.assertIsNotNone(elasticsearch_container, "could not find elasticsearch container")
        
        postgres_name = postgres_container.attrs["Name"]
        memcached_name = memcached_container.attrs["Name"]
        elasticsearch_name = elasticsearch_container.attrs["Name"]
        
        postgres_links = postgres_container.attrs["HostConfig"]["Links"]
        memcached_links = memcached_container.attrs["HostConfig"]["Links"]
        elasticsearch_links = elasticsearch_container.attrs["HostConfig"]["Links"]
        
        self.assertIsNone(memcached_links)
        
        expected_postgres_links = [
            "{}:{}/{}".format(memcached_name, postgres_name, memcached_container.id)
        ]
        self.assertEqual(expected_postgres_links, postgres_links)
        
        expected_elasticsearch_links = [
            "{}:{}/a-user-specified-alias".format(memcached_name, elasticsearch_name),
            "{}:{}/{}".format(postgres_name, elasticsearch_name, postgres_container.id),
        ]
        self.assertEqual(sorted(expected_elasticsearch_links), sorted(elasticsearch_links))

    def test_validate_link_line_with_dangling_colon(self):
        with self.assertRaises(ValueError) as cm:
            _validate_link_line('some-image-name:')
        self.assertEqual("Linked to 'some-image-name' container with dangling ':'. Remove it or add an alias.")
