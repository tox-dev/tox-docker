from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union
import os
import socket
import sys
import time

from docker.errors import ImageNotFound, NotFound
from docker.models.containers import Container
import docker as docker_module

from tox_docker.config import ContainerConfig, RunningContainers
from tox_docker.log import LogFunc


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


def docker_pull(container_config: ContainerConfig, log: LogFunc) -> None:
    docker = docker_module.from_env(version="auto")

    try:
        docker.images.get(container_config.image.name)
    except ImageNotFound:
        log(f"pull {container_config.image!r} (from {container_config.name!r})")
        docker.images.pull(container_config.image.name, tag=container_config.image.tag)


def docker_run(
    container_config: ContainerConfig,
    running_containers: RunningContainers,
    log: LogFunc,
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

    ports = {p.container_port_proto: p.host_port for p in container_config.ports}

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

    log(f"run {container_config.image!r} (from {container_config.name!r})")
    container = docker.containers.run(
        str(container_config.image),
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
    container_config: ContainerConfig, container: Container, log: LogFunc
) -> None:
    docker = docker_module.from_env(version="auto")

    if "Health" in container.attrs["State"]:
        log(f"health check {container_config.image!r} (from {container_config.name!r})")
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


def docker_stop(
    container_config: ContainerConfig, container: Container, log: LogFunc
) -> None:
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


def stop_containers(
    containers: Iterable[Tuple[ContainerConfig, Container]], log: LogFunc
) -> None:
    for container_config, container in containers:
        docker_stop(container_config, container, log)


def get_env_vars(
    container_config: ContainerConfig, container: Container
) -> Mapping[str, str]:
    env = {}
    gateway_ip = get_gateway_ip(container)
    for containerport, hostports in container.attrs["NetworkSettings"]["Ports"].items():
        if hostports is None:
            # The port is exposed by the container, but not published.
            continue

        for spec in hostports:
            if spec["HostIp"] == "0.0.0.0":
                hostport = spec["HostPort"]
                break
        else:
            continue

        env[escape_env_var(f"{container_config.name}_HOST")] = gateway_ip
        env[escape_env_var(f"{container_config.name}_{containerport}_PORT")] = hostport

    return env
