from docker.models.containers import Container
import docker
import pytest


def find_container(instance_name: str) -> Container:
    # TODO: refactor this as a pytest fixture
    client = docker.from_env(version="auto")
    for container in client.containers.list():
        labels = container.attrs["Config"].get("Labels", {})
        if labels.get("tox_docker_container_name") == instance_name:
            return container

    pytest.fail(f"No running container with instance name {instance_name!r}")
