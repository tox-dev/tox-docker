from tox_docker.tests.util import find_container


def test_can_grant_privileged() -> None:
    container = find_container("healthcheck-custom")

    assert container.attrs["HostConfig"]["Privileged"] is True


def test_can_deny_privileged() -> None:
    container = find_container("networking-two")

    assert container.attrs["HostConfig"]["Privileged"] is False


def test_not_privileged_by_default() -> None:
    container = find_container("healthcheck-builtin")

    assert container.attrs["HostConfig"]["Privileged"] is False
