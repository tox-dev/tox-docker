import os

from docker.models.containers import Container
import docker
import pytest

from tox_docker.config import runas_name


def find_container(instance_name: str) -> Container:
    # TODO: refactor this as a pytest fixture

    # this is running in a child-process of the tox instance which
    # spawned the container; so we need to pass the parent pid to
    # get the right runas_name()
    running_name = runas_name(instance_name, pid=os.getppid())
    client = docker.from_env(version="auto")
    for container in client.containers.list():
        container.attrs["Config"].get("Labels", {})
        if container.name == running_name:
            return container

    pytest.fail(f"No running container with instance name {running_name!r}")
