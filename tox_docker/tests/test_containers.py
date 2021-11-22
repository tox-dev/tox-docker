import re

from tox_docker.tests.util import find_container


def test_it_can_run_two_of_the_same_image():
    hc_builtin = find_container("healthcheck-builtin")
    hc_custom = find_container("healthcheck-custom")

    assert hc_builtin.id != hc_custom.id
    assert hc_builtin.attrs["Image"] == hc_custom.attrs["Image"]


def test_container_name_has_random_suffix():
    networking_container = find_container("networking-one")
    # 5 digit random number
    assert re.search("^networking-one_\d{5}", networking_container.name)
