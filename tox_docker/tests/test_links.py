import pytest

from tox_docker.config import validate_link
from tox_docker.tests.util import find_container


def test_linked_containers_can_communicate() -> None:
    outer_container = find_container("networking-two")
    # the outer container should have a link named "linked_host"
    # to the inner container, listening on port 1234
    exitcode, _ = outer_container.exec_run("nc linked_host 1234")
    assert exitcode == 0


def test_validate_link_line() -> None:
    names = {"httpd"}
    assert validate_link("httpd:apache", names) == ("httpd", "apache")
    assert validate_link("httpd", names) == ("httpd", "httpd")


def test_validate_link_line_rejects_dangling_comma() -> None:
    names = {"httpd"}
    with pytest.raises(ValueError):
        validate_link("httpd:", names)
    with pytest.raises(ValueError):
        validate_link("httpd", set())
