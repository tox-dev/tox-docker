__all__ = (
    "tox_add_env_config",
    "tox_add_option",
    "tox_after_run_commands",
    "tox_before_run_commands",
)

from logging import getLogger
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union
import os
import socket
import sys
import time

from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container
from tox.config.cli.parser import ToxParser
from tox.config.loader.section import Section
from tox.config.sets import EnvConfigSet
from tox.execute.api import Outcome
from tox.plugin import impl
from tox.session.state import State
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Fail
import docker as docker_module

from tox_docker.config import (
    ContainerConfig,
    DockerConfigSet,
    parse_container_config,
    RunningContainers,
)


def log(line: str) -> None:
    getLogger().warning(f"docker> {line}")


class HealthCheckFailed(Exception):
    pass


def get_gateway_ip(container: Container) -> str:
    gateway = os.getenv("TOX_DOCKER_GATEWAY")
    if gateway:
        ip = socket.gethostbyname(gateway)
    elif sys.platform == "darwin":
        # https://docs.docker.com/docker-for-mac/networking/#use-cases-and-workarounds:
        # there is no bridge network available in Docker for Mac, and exposed ports are
        # made available on localhost (but 0.0.0.0 works just as well)
        ip = "0.0.0.0"
    else:
        ip = container.attrs["NetworkSettings"]["Gateway"] or "0.0.0.0"
    return ip


def escape_env_var(varname: str) -> str:
    """
    Convert a string to a form suitable for use as an environment variable.

    The result will be all uppercase, and will have all invalid characters
    replaced by an underscore.

    The result will match the following regex: [a-zA-Z_][a-zA-Z0-9_]*

    Example:
        "my.private.registry/cat/image" will become
        "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    """
    varletters = list(varname.upper())
    if not varletters[0].isalpha():
        varletters[0] = "_"
    for i, c in enumerate(varletters):
        if not c.isalnum() and c != "_":
            varletters[i] = "_"
    return "".join(varletters)


def get_host_env_var(container_config: ContainerConfig) -> str:
    if container_config.host_var:
        return container_config.host_var

    return escape_env_var(f"{container_config.name}_HOST")


def get_container_env_var(container_config: ContainerConfig) -> str:
    if container_config.container_var:
        return container_config.container_var

    return escape_env_var(f"{container_config.name}_CONTAINER")


def get_env_vars(
    container_config: ContainerConfig, container: Container
) -> Mapping[str, str]:
    env = {}
    for containerport, hostports in container.attrs["NetworkSettings"]["Ports"].items():
        if hostports is None:
            # The port is exposed by the container, but not published.
            continue

        for spec in hostports:
            if spec["HostIp"] == "0.0.0.0":
                hostport = spec["HostPort"]
                env_var = get_port_env_var(container_config, containerport)
                env[env_var] = hostport
                break

    gateway_ip = get_gateway_ip(container)
    env_var = get_host_env_var(container_config)
    env[env_var] = gateway_ip
    env_var = get_container_env_var(container_config)
    env[env_var] = container_config.runas_name
    return env


def get_port_env_var(container_config: ContainerConfig, containerport: str) -> str:
    for exposed_port in container_config.expose:
        if exposed_port.container_port_proto == containerport:
            return exposed_port.env_var

    return escape_env_var(f"{container_config.name}_{containerport}_PORT")


def docker_build_or_pull(container_config: ContainerConfig) -> None:
    if container_config.image:
        docker_pull(container_config)
    else:
        docker_build(container_config)


def docker_pull(container_config: ContainerConfig) -> None:
    assert container_config.image

    docker = docker_module.from_env(version="auto")

    try:
        docker.images.get(str(container_config.image))
    except ImageNotFound:
        log(f"pull {container_config.image!r} (from {container_config.name!r})")
        docker.images.pull(container_config.image.name, tag=container_config.image.tag)

    container_config.runnable_image = docker.images.get(str(container_config.image))


def docker_build(container_config: ContainerConfig) -> None:
    assert container_config.dockerfile

    docker = docker_module.from_env(version="auto")

    if container_config.dockerfile_target:
        log(
            f"build {container_config.dockerfile!r} target {container_config.dockerfile_target!r}"
        )
    else:
        log(f"build {container_config.dockerfile!r}")

    image, _ = docker.images.build(
        path=container_config.dockerfile.directory,
        dockerfile=container_config.dockerfile.filename,
        target=container_config.dockerfile_target or None,
        pull=True,
        forcerm=True,
    )
    log(f"built: {image.short_id}")

    container_config.runnable_image = image


def docker_run(
    container_config: ContainerConfig,
    running_containers: RunningContainers,
) -> Container:
    docker = docker_module.from_env(version="auto")

    healthcheck: Dict[str, Union[List[str], int]] = {}
    if container_config.healthcheck_cmd:
        healthcheck["test"] = ["CMD-SHELL", container_config.healthcheck_cmd]
    if container_config.healthcheck_interval:
        healthcheck["interval"] = container_config.healthcheck_interval
    if container_config.healthcheck_timeout:
        healthcheck["timeout"] = container_config.healthcheck_timeout
    if container_config.healthcheck_start_period:
        healthcheck["start_period"] = container_config.healthcheck_start_period
    if container_config.healthcheck_retries:
        healthcheck["retries"] = container_config.healthcheck_retries

    ports = {p.container_port_proto: 0 for p in container_config.expose}

    links = {}
    for link in container_config.links:
        if link.target not in running_containers:
            raise ValueError(
                f"Container {link.target!r} not running; it must come before {container_config.name!r} in the docker= list"
            )
        other_container = running_containers[link.target]
        links[other_container.id] = link.alias

    for mount in container_config.mounts:
        source = mount["Source"]
        if not os.path.exists(source):
            raise ValueError(f"Volume source {source!r} does not exist")

    assert container_config.runnable_image
    image_name = container_config.image or container_config.runnable_image.short_id
    log(f"run {image_name!r} (from {container_config.name!r})")

    container = docker.containers.run(
        container_config.runnable_image.id,
        name=container_config.runas_name,
        detach=True,
        environment=container_config.environment,
        healthcheck=healthcheck or None,
        links=links,
        ports=ports,
        publish_all_ports=len(ports) == 0,
        mounts=container_config.mounts,
    )
    container.reload()  # TODO: why do we need this?
    return container


def docker_health_check(
    container_config: ContainerConfig, container: Container
) -> None:
    docker = docker_module.from_env(version="auto")

    if "Health" in container.attrs["State"]:
        log(f"health check {container_config.name!r}")
        while True:
            container.reload()
            health = container.attrs["State"]["Health"]["Status"]
            if health == "healthy":
                break
            elif health == "starting":
                time.sleep(0.1)
            elif health == "unhealthy":
                # the health check failed after its own timeout
                msg = f"{container_config.image!r} (from {container_config.name!r}) failed health check"
                raise HealthCheckFailed(msg)


def docker_stop(container_config: ContainerConfig, container: Container) -> None:
    if container_config.stop:
        log(f"remove '{container.short_id}' (from {container_config.name!r})")
        container.remove(v=True, force=True)
    else:
        log(f"leave '{container.short_id}' (from {container_config.name!r}) running")


def docker_get(container_config: ContainerConfig) -> Optional[Container]:
    docker = docker_module.from_env(version="auto")
    try:
        return docker.containers.get(container_config.runas_name)
    except NotFound:
        return None


def stop_containers(containers: Iterable[Tuple[ContainerConfig, Container]]) -> None:
    for container_config, container in containers:
        docker_stop(container_config, container)


@impl
def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
    def build_docker_config_set(container_name: object) -> DockerConfigSet:
        assert isinstance(container_name, str)
        docker_conf = state.conf.get_section_config(
            section=Section("docker", container_name),
            base=[],
            of_type=DockerConfigSet,
            for_env=None,
        )
        if not docker_conf.loaders:
            raise ValueError(f"Missing [docker:{container_name}] in tox.ini")
        return docker_conf

    env_conf.add_config(
        keys=["docker"],
        of_type=List[DockerConfigSet],
        default=[],
        desc="docker image configs to load",
        factory=build_docker_config_set,  # type: ignore
    )


@impl
def tox_before_run_commands(tox_env: ToxEnv) -> None:
    docker_confs = tox_env.conf.load("docker")

    container_configs = [
        parse_container_config(docker_conf) for docker_conf in docker_confs
    ]

    seen = set()
    for container_config in container_configs:
        if container_config.name in seen:
            raise ValueError(
                f"Container {container_config.name!r} specified more than once"
            )
        seen.add(container_config.name)

    for container_config in container_configs:
        docker_build_or_pull(container_config)

    config_and_container = []
    running_containers: RunningContainers = {}
    for container_config in container_configs:
        container = docker_run(container_config, running_containers)
        config_and_container.append((container_config, container))
        running_containers[container_config.runas_name] = container

    for container_config, container in config_and_container:
        try:
            docker_health_check(container_config, container)
        except HealthCheckFailed:
            tox_env.interrupt()
            clean_up_containers(tox_env)
            raise Fail(
                f"{container_config.image!r} (from {container_config.name!r}) failed health check"
            )

        tox_env.conf["set_env"].update(get_env_vars(container_config, container))


@impl
def tox_after_run_commands(
    tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]
) -> None:
    clean_up_containers(tox_env)


def clean_up_containers(tox_env: ToxEnv) -> None:
    docker_confs = tox_env.conf.load("docker")

    container_configs = [
        parse_container_config(docker_conf) for docker_conf in docker_confs
    ]

    configs_and_containers = []
    for config in container_configs:
        container = docker_get(config)
        if container:
            configs_and_containers.append((config, container))

    stop_containers(configs_and_containers)


@impl
def tox_add_option(parser: ToxParser) -> None:
    # command line flag to keep docker containers running
    parser.add_argument(
        "--docker-dont-stop",
        default=[],
        action="append",
        metavar="CONTAINER",
        help=(
            "If specified, tox-docker will not stop CONTAINER after the test run. "
            "Can be specified multiple times."
        ),
    )
