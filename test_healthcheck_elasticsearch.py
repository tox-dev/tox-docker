import os
import unittest

import docker


class ToxDockerHealthCheckTest(unittest.TestCase):

    def test_it_waits_for_health_check_to_succeed(self):
        # the elasticsearch instance takes awhile to ack its healthcheck;
        # this is sloppy and might have false positives, but it should
        # have no false negatives (if it fails, tox-docker _is_ broken)
        client = docker.from_env(version="auto")
        test_container = None
        for container in client.containers.list():
            if "elasticsearch" in container.attrs['Config']['Image']:
                test_container = container
                break

        self.assertIsNotNone(test_container, "could not find elasticsearch container")
        self.assertEqual("healthy", test_container.attrs["State"]["Health"]["Status"])
