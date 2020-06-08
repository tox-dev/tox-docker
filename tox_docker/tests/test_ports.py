from urllib.request import urlopen
import os

import docker

from tox_docker.tests.util import find_container


def test_exposed_ports_are_accessible_to_test_runs():
    host = os.environ["NGINX_FROM_REGISTRY_URL_HOST"]
    port = os.environ["NGINX_FROM_REGISTRY_URL_80_TCP_PORT"]

    response = urlopen(f"http://{host}:{port}/")
    assert response.getcode() == 200
    assert b"Thank you for using nginx." in response.read()


def test_it_exposes_only_specified_port():
    client = docker.from_env(version="auto")
    mysql_container = None
    for container in client.containers.list():
        if "mysql" in container.attrs["Config"]["Image"]:
            mysql_container = container
            break

    mysql_container = find_container("custom-port-mapping")
    mapped_ports = mysql_container.attrs["NetworkSettings"]["Ports"]

    assert mapped_ports["3306/tcp"] is not None
    assert mapped_ports["33060/tcp"] is None
