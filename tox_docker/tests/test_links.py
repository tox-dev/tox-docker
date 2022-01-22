import pytest

from tox_docker.config import Link, runas_name
from tox_docker.tests.util import find_container


def test_linked_containers_can_communicate() -> None:
    outer_container = find_container("networking-two")
    # the outer container should have a link named "linked_host"
    # to the inner container, listening on port 1234
    exitcode, _ = outer_container.exec_run("nc linked_host 1234")
    assert exitcode == 0


def test_link_parsing() -> None:
    assert Link("httpd").target == runas_name("httpd")
    assert Link("httpd").alias == "httpd"

    assert Link("httpd:apache").target == runas_name("httpd")
    assert Link("httpd:apache").alias == "apache"


def test_link_parsing_rejects_trailing_colon() -> None:
    with pytest.raises(ValueError):
        Link("httpd:")
