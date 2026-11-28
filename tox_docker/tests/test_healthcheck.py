from typing import Any, Dict
from unittest.mock import Mock, patch
from urllib.request import urlopen
import os

import pytest

from tox_docker.plugin import docker_health_check, HealthCheckFailed


@pytest.mark.parametrize("instance", ["HEALTHCHECK_BUILTIN", "HEALTHCHECK_CUSTOM"])
def test_the_image_is_healthy(instance: str) -> None:
    host = os.environ[f"{instance}_HOST"]
    port = os.environ[f"{instance}_8000_TCP_PORT"]
    url = f"http://{host}:{port}/healthy"

    response = urlopen(url)
    assert response.getcode() == 200, f"GET {url} => {response.getcode()}"


@pytest.mark.parametrize(
    "health, expected_detail",
    [
        (
            {
                "Log": [
                    {"ExitCode": 1, "Output": "first failure"},
                    {"ExitCode": 2, "Output": "database unavailable\n"},
                    {"ExitCode": 1, "Output": "  \n"},
                ]
            },
            ": database unavailable",
        ),
        (
            {
                "Log": [
                    {"ExitCode": 0, "Output": "ready"},
                    {"ExitCode": 1, "Output": ""},
                ]
            },
            "",
        ),
        ({}, ""),
    ],
)
def test_unhealthy_container_reports_last_failure(
    health: Dict[str, Any], expected_detail: str
) -> None:
    container = Mock(attrs={"State": {"Health": {"Status": "unhealthy", **health}}})
    config = Mock(image="postgres:16")
    config.name = "db"
    with patch("tox_docker.plugin.docker_module.from_env"), pytest.raises(
        HealthCheckFailed
    ) as caught:
        docker_health_check(config, container)
    assert (
        str(caught.value)
        == "'postgres:16' (from 'db') failed health check" + expected_detail
    )
