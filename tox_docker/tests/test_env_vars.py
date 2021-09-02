import os

from tox_docker.plugin import escape_env_var


def test_it_sets_automatic_env_vars() -> None:
    # ksdn117/tcp-udp-test exposes TCP port 1234 and UDP port 5678
    assert "NETWORKING_ONE_HOST" in os.environ
    assert "NETWORKING_ONE_1234_TCP_PORT" in os.environ
    assert "NETWORKING_ONE_5678_UDP_PORT" in os.environ

    # the old names of these variables were dropped in 2.0
    assert "NETWORKING_ONE_1234_TCP" not in os.environ
    assert "NETWORKING_ONE_5678_UDP" not in os.environ


def test_escape_env_var() -> None:
    assert (
        escape_env_var("my.private.registry/cat/image")
        == "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    )
