import os
import unittest

import docker


class ToxDockerLinksTest(unittest.TestCase):

    def test_links_created(self):
        client = docker.from_env(version="auto")
        alpine_container = None
        busybox_container = None
        docker_container = None
        for container in client.containers.list():
            if alpine_container is None and "alpine" in container.attrs['Config']['Image']:
                alpine_container = container
            
            if busybox_container is None and "busybox" in container.attrs['Config']['Image']:
                busybox_container = container
            
            if docker_container is None and "docker" in container.attrs['Config']['Image']:
                docker_container = container
            
            if all([alpine_container, busybox_container, docker_container]):
                break

        self.assertIsNotNone(alpine_container, "could not find alpine container")
        self.assertIsNotNone(busybox_container, "could not find busybox container")
        self.assertIsNotNone(docker_container, "could not find docker container")
        
        alpine_name = alpine_container.attrs["Name"]
        busybox_name = busybox_container.attrs["Name"]
        docker_name = docker_container.attrs["Name"]
        
        alpine_links = alpine_container.attrs["HostConfig"]["Links"]
        busybox_links = busybox_container.attrs["HostConfig"]["Links"]
        docker_links = docker_container.attrs["HostConfig"]["Links"]
        
        self.assertIsNone(busybox_links)
        
        expected_alpine_links = [
            "{}:{}".format(busybox_name, alpine_name)
        ]
        self.assertEqual(expected_alpine_links, alpine_links)
        
        expected_docker_links = [
            "{}:{}/a-user-specified-link-ref".format(busybox_name, docker_name),
            "{}:{}".format(alpine_name, docker_name)
        ]
        self.assertEqual(expected_docker_links, docker_links)
