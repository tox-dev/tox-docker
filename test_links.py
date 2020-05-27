import os
import unittest

import docker


class ToxDockerLinksTest(unittest.TestCase):

    def test_links_created(self):
        client = docker.from_env(version="auto")
        postgres_container = None
        memcached_container = None
        docker_container = None
        for container in client.containers.list():
            if postgres_container is None and "postgres" in container.attrs['Config']['Image']:
                postgres_container = container
            
            if memcached_container is None and "memcached" in container.attrs['Config']['Image']:
                memcached_container = container
            
            if docker_container is None and "elasticsearch" in container.attrs['Config']['Image']:
                docker_container = container
            
            if all([postgres_container, memcached_container, docker_container]):
                break

        self.assertIsNotNone(postgres_container, "could not find postgres container")
        self.assertIsNotNone(memcached_container, "could not find memcached container")
        self.assertIsNotNone(docker_container, "could not find docker container")
        
        postgres_name = postgres_container.attrs["Name"]
        memcached_name = memcached_container.attrs["Name"]
        docker_name = docker_container.attrs["Name"]
        
        postgres_links = postgres_container.attrs["HostConfig"]["Links"]
        memcached_links = memcached_container.attrs["HostConfig"]["Links"]
        docker_links = docker_container.attrs["HostConfig"]["Links"]
        
        self.assertIsNone(memcached_links)
        
        expected_postgres_links = [
            "{}:{}/{}".format(memcached_name, postgres_name, memcached_container.id)
        ]
        self.assertEqual(expected_postgres_links, postgres_links)
        
        expected_docker_links = [
            "{}:{}/a-user-specified-alias".format(memcached_name, docker_name),
            "{}:{}/{}".format(postgres_name, docker_name, postgres_container.id),
        ]
        self.assertEqual(expected_docker_links, docker_links)
