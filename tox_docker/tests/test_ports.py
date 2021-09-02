from urllib.request import urlopen
import os


def test_exposed_ports_are_accessible_to_test_runs() -> None:
    host = os.environ["HEALTHCHECK_BUILTIN_HOST"]
    port = os.environ["HEALTHCHECK_BUILTIN_8000_TCP_PORT"]

    response = urlopen(f"http://{host}:{port}/")
    assert response.getcode() == 200
    assert b"Directory listing for /" in response.read()


def test_it_exposes_only_specified_port() -> None:
    # this container remaps 1234/tcp to 2345, and hides 5678/udp
    assert os.environ["NETWORKING_TWO_1234_TCP_PORT"] == "2345"
    assert "NETWORKING_TWO_5678_UDP_PORT" not in os.environ
