import os

from tox_docker import escape_env_var


def test_it_sets_automatic_env_vars():
    # ksdn117/tcp-udp-test exposes TCP port 1234 and UDP port 5678
    assert "TCP_UDP_TEST_HOST" in os.environ
    assert "TCP_UDP_TEST_1234_TCP_PORT" in os.environ
    assert "TCP_UDP_TEST_5678_UDP_PORT" in os.environ

    # the old names of these variables were dropped in 2.0
    assert "TCP_UDP_TEST_1234_TCP" not in os.environ
    assert "TCP_UDP_TEST_5678_UDP" not in os.environ


def test_escape_env_var():
    assert (
        escape_env_var("my.private.registry/cat/image")
        == "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    )
