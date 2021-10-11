from tox_docker.tests.util import find_container


def test_it_can_run_two_of_the_same_image():
    hc_builtin = find_container("healthcheck-builtin")
    hc_custom = find_container("healthcheck-custom")

    assert hc_builtin.id != hc_custom.id
    assert hc_builtin.attrs["Image"] == hc_custom.attrs["Image"]


def test_can_run_with_command():
    default = find_container("networking-one")
    custom = find_container("networking-cmd")

    assert default.attrs["Args"] == ["/run.sh"]
    assert custom.attrs["Args"] == ["/run.sh", "with", "some", "options"]
