import os
import unittest

from tox_docker import escape_env_var


class ToxDockerRegistryTest(unittest.TestCase):
    def test_it_sets_automatic_env_vars(self):
        # we assume that if these envvars are set, the image (configured to
        # be pulled from a registry URI rather than by name) was successfully
        # pulled & started
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_HOST", os.environ)
        self.assertIn("DOCKER_IO_LIBRARY_NGINX_80_TCP_PORT", os.environ)

    def test_escape_env_var(self):
        self.assertEqual(
            escape_env_var("my.private.registry/cat/image"),
            "MY_PRIVATE_REGISTRY_CAT_IMAGE",
        )
