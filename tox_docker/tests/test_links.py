import pytest

from tox_docker import _validate_link_line
from tox_docker.tests.util import find_container


def test_links_created():
    httpd_container = find_container("links-httpd")
    registry_container = find_container("links-registry")
    nginx_container = find_container("links-nginx")

    # TODO: figure out why docker prepends / to the Name attribute,
    # and fix the handling here if we're doing something wrong...
    httpd_name = httpd_container.attrs["Name"].lstrip("/")
    registry_name = registry_container.attrs["Name"].lstrip("/")
    nginx_name = nginx_container.attrs["Name"].lstrip("/")

    httpd_links = httpd_container.attrs["HostConfig"]["Links"]
    registry_links = registry_container.attrs["HostConfig"]["Links"]
    nginx_links = nginx_container.attrs["HostConfig"]["Links"]

    assert httpd_links is None
    assert registry_links == [f"/{httpd_name}:/{registry_name}/apache"]

    assert sorted(nginx_links) == [
        f"/{httpd_name}:/{nginx_name}/{httpd_name}",
        f"/{registry_name}:/{nginx_name}/hub",
    ]


def test_links_work():
    registry_container = find_container("links-registry")
    nginx_container = find_container("links-nginx")

    assert registry_container.exec_run("ping -c 1 apache")[0] == 0
    assert nginx_container.exec_run("curl --noproxy '*' http://hub:5000")[0] == 0
    assert nginx_container.exec_run("curl --noproxy '*' http://links-httpd")[0] == 0


def test_validate_link_line():
    names = {"httpd"}
    assert _validate_link_line("httpd:apache", names) == ("httpd", "apache")
    assert _validate_link_line("httpd", names) == ("httpd", "httpd")


def test_validate_link_line_rejects_dangling_comma():
    names = {"httpd"}
    with pytest.raises(ValueError):
        _validate_link_line("httpd:", names)
    with pytest.raises(ValueError):
        _validate_link_line("httpd", set())
