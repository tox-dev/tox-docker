from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch
import sys

import pytest

from tox_docker.plugin import get_gateway_ip


@contextmanager
def sys_platform_as(value: str) -> Iterator[None]:
    old_value = sys.platform
    sys.platform = value
    try:
        yield
    finally:
        sys.platform = old_value


class NotARealContainer(object):
    attrs = {"NetworkSettings": {"Gateway": "1.2.3.4"}}


def test_gateway_ip_is_read_from_container_attrs_on_linux() -> None:
    container = NotARealContainer()
    with sys_platform_as("linux2"):
        assert get_gateway_ip(container) == "1.2.3.4"


def test_gateway_ip_is_zero_zero_zero_zero_on_macos() -> None:
    container = NotARealContainer()
    with sys_platform_as("darwin"):
        assert get_gateway_ip(container) == "0.0.0.0"


@pytest.mark.parametrize("sys_platform", ["linux2", "darwin"])
def test_gateway_ip_from_env_var_overrides_attrs_on_linux(sys_platform: str) -> None:
    container = NotARealContainer()
    with sys_platform_as(sys_platform):
        with patch.dict("os.environ", {"TOX_DOCKER_GATEWAY": "192.168.1.1"}):
            assert get_gateway_ip(container) == "192.168.1.1"


@pytest.mark.parametrize("sys_platform", ["linux2", "darwin"])
def test_gateway_ip_is_looked_up_from_hostname(sys_platform: str) -> None:
    container = NotARealContainer()
    with sys_platform_as(sys_platform):
        with patch.dict("os.environ", {"TOX_DOCKER_GATEWAY": "localhost"}):
            assert get_gateway_ip(container) in {"127.0.0.1", "::1"}
