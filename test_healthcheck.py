import os
import unittest

import docker


class ToxDockerHealthCheckTest(unittest.TestCase):

    def test_it_waits_for_builtin_health_check_to_succeed(self):
        # the redis instance takes a few seconds to ack its healthcheck;
        # this is sloppy and might have false positives, but it should
        # have no false negatives (if it fails, tox-docker _is_ broken)
        client = docker.from_env(version="auto")
        redis_container = None
        for container in client.containers.list():
            if "healthcheck/redis" in container.attrs['Config']['Image']:
                redis_container = container
                break

        self.assertIsNotNone(redis_container, "could not find redis container")
        self.assertEqual("healthy", redis_container.attrs["State"]["Health"]["Status"])
