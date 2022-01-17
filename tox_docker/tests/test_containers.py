from tox_docker.tests.util import find_container


def test_it_can_run_two_of_the_same_image() -> None:
    hc_builtin = find_container("healthcheck-builtin")
    hc_custom = find_container("healthcheck-custom")

    assert hc_builtin.id != hc_custom.id
    assert hc_builtin.attrs["Image"] == hc_custom.attrs["Image"]


def test_container_has_unique_runas_suffix() -> None:
    container = find_container("healthcheck-builtin")
    assert container.name.startswith("healthcheck-builtin")
    assert container.name != "healthcheck-builtin"
    # don't test the details of how we do this; the suffix could be some
    # randomly-chosen suffix, could be PID (it is), or something else
