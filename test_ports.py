import unittest

import docker


class ToxDockerPortTest(unittest.TestCase):

    def test_it_exposes_only_specified_port(self):
        client = docker.from_env(version="auto")
        mysql_container = None
        for container in client.containers.list():
            if "mysql" in container.attrs["Config"]["Image"]:
                mysql_container = container
                break

        self.assertIsNotNone(mysql_container, "could not find mysql container")
        self.assertIsNotNone(mysql_container.attrs["NetworkSettings"]["Ports"]["3306/tcp"])
        self.assertIsNone(mysql_container.attrs["NetworkSettings"]["Ports"]["33060/tcp"])
