import os
import unittest

from tox_docker import escape_env_var


class ToxDockerRegistryTest(unittest.TestCase):
    def test_it_sets_automatic_env_vars(self):
        # the nginx image we use exposes port 80
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_HOST", os.environ)
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_80_TCP", os.environ)

    def test_escape_env_var(self):
        self.assertEqual(
            escape_env_var("my.private.registry/cat/image"),
            "MY_PRIVATE_REGISTRY_CAT_IMAGE",
        )
