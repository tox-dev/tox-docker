import pytest

from tox_docker.tests.util import find_container


@pytest.mark.parametrize("instance_name", ["healthcheck-builtin", "healthcheck-custom"])
def test_the_image_is_healthy_builtin(instance_name):
    container = find_container("healthcheck-builtin")
    assert container.attrs["State"]["Health"]["Status"] == "healthy"
