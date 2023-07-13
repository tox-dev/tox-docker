from urllib.request import urlopen
import os


def test_default_host_name_var() -> None:
    # [docker:healthcheck-builtin] doesn't specify host_var
    assert "HEALTHCHECK_BUILTIN_HOST" in os.environ


def test_custom_host_name_var() -> None:
    # [docker:healthcheck-custom] _does_ specify host_var=...
    assert "NET_TWO_CUSTOM_HOST" in os.environ


def test_EXPOSEd_ports_are_available_when_expose_is_not_set() -> None:
    # [docker:healthcheck-builtin] does not have expose=
    assert "HEALTHCHECK_BUILTIN_8000_TCP_PORT" in os.environ


def test_EXPOSEd_ports_are_not_available_if_not_listed_in_expose() -> None:
    # [docker:networking-two] doesn't map 5678/udp, but it is EXPOSEd
    assert "NETWORKING_TWO_5678_UDP_PORT" not in os.environ


def test_manually_mapped_ports_dont_get_default_port_envvar() -> None:
    # [docker:networking-two] explicitly maps 1234/tcp
    assert "NETWORKING_TWO_1234_TCP_PORT" not in os.environ


def test_exposed_ports_are_accessible_to_test_runs() -> None:
    host = os.environ["HEALTHCHECK_BUILTIN_HOST"]
    port = os.environ["HEALTHCHECK_BUILTIN_8000_TCP_PORT"]

    response = urlopen(f"http://{host}:{port}/")
    assert response.getcode() == 200
    assert b"Directory listing for /" in response.read()
