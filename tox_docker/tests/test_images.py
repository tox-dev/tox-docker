from tox_docker.config import Image


def test_it_parses_name_and_tag() -> None:
    i = Image("nginx:latest")
    assert i.name == "nginx"
    assert i.tag == "latest"


def test_it_defaults_tag_to_None() -> None:
    i = Image("nginx")
    assert i.name == "nginx"
    assert i.tag is None


def test_it_parses_registry_url_into_name() -> None:
    i = Image("docker.io/toxdocker/healthcheck:latest")
    assert i.name == "docker.io/toxdocker/healthcheck"
    assert i.tag == "latest"


def test_it_allows_port_in_registry_url() -> None:
    i = Image("private-registry:5000/namespace/image-name:1.0.0")
    assert i.name == "private-registry:5000/namespace/image-name"
    assert i.tag == "1.0.0"


def test_it_allows_port_in_registry_url_without_tag() -> None:
    i = Image("private-registry:5000/namespace/image-name")
    assert i.name == "private-registry:5000/namespace/image-name"
    assert i.tag is None
