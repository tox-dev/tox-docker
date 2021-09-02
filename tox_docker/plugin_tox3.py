from typing import Any, cast, Dict, List, Mapping, Optional, Union
import os.path
import time

from docker.errors import ImageNotFound
from docker.models.containers import Container
from tox import hookimpl
from tox.action import Action
from tox.config import Config, Parser
from tox.session import Session
from tox.venv import VirtualEnv
import docker as docker_module

from tox_docker.config import ContainerConfig
from tox_docker.config_tox3 import (
    discover_container_configs,
    parse_container_config,
)
from tox_docker.plugin import escape_env_var, get_gateway_ip, HealthCheckFailed


def _newaction(venv: VirtualEnv, message: str) -> Action:
    try:
        # tox 3.7 and later
        return venv.new_action(message)
    except AttributeError:
        return venv.session.newaction(venv, message)


@hookimpl
def tox_configure(config: Config) -> None:
    container_config_names = discover_container_configs(config)

    # validate command line options
    for container_name in config.option.docker_dont_stop:
        if container_name not in container_config_names:
            raise ValueError(
                f"Container {container_name!r} not found (from --docker-dont-stop)"
            )

    container_configs: Dict[str, ContainerConfig] = {}
    for container_name in container_config_names:
        container_configs[container_name] = parse_container_config(
            config, container_name, container_config_names
        )

    config._docker_container_configs = container_configs


@hookimpl  # noqa: C901
def tox_runtest_pre(venv: VirtualEnv) -> None:  # noqa: C901
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    config = envconfig.config
    container_configs: Mapping[str, ContainerConfig] = config._docker_container_configs

    docker = docker_module.from_env(version="auto")
    action = _newaction(venv, "docker")

    seen = set()
    for container_name in envconfig.docker:
        if container_name not in container_configs:
            raise ValueError(f"Missing [docker:{container_name}] in tox.ini")
        if container_name in seen:
            raise ValueError(f"Container {container_name!r} specified more than once")
        seen.add(container_name)

        image = container_configs[container_name].image
        name, _, tag = image.partition(":")

        try:
            docker.images.get(image)
        except ImageNotFound:
            action.setactivity("docker", f"pull {image!r} (from {container_name!r})")
            with action:
                docker.images.pull(name, tag=tag or None)

    envconfig._docker_containers = {}
    for container_name in envconfig.docker:
        container_config = container_configs[container_name]

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

        links = {}
        for other_container_name, alias in container_config.links.items():
            other_container = envconfig._docker_containers[other_container_name]
            links[other_container.id] = alias

        for mount in container_config.mounts:
            source = mount["Source"]
            if not os.path.exists(source):
                raise ValueError(f"Volume source {source!r} does not exist")

        action.setactivity(
            "docker", f"run {container_config.image!r} (from {container_name!r})"
        )
        with action:
            container = docker.containers.run(
                container_config.image,
                detach=True,
                environment=container_config.environment,
                healthcheck=healthcheck or None,
                labels={"tox_docker_container_name": container_name},
                links=links,
                name=container_name,
                ports=container_config.ports,
                publish_all_ports=len(container_config.ports) == 0,
                mounts=container_config.mounts,
            )

        envconfig._docker_containers[container_name] = container
        container.reload()

    for container_name, container in envconfig._docker_containers.items():
        image = container.attrs["Config"]["Image"]
        if "Health" in container.attrs["State"]:
            action.setactivity(
                "docker", f"health check {image!r} (from {container_name!r})"
            )
            with action:
                while True:
                    container.reload()
                    health = container.attrs["State"]["Health"]["Status"]
                    if health == "healthy":
                        break
                    elif health == "starting":
                        time.sleep(0.1)
                    elif health == "unhealthy":
                        # the health check failed after its own timeout
                        stop_containers(venv)
                        msg = f"{image!r} (from {container_name!r}) failed health check"
                        venv.status = msg
                        raise HealthCheckFailed(msg)

        gateway_ip = get_gateway_ip(container)
        for containerport, hostports in container.attrs["NetworkSettings"][
            "Ports"
        ].items():
            if hostports is None:
                # The port is exposed by the container, but not published.
                continue

            for spec in hostports:
                if spec["HostIp"] == "0.0.0.0":
                    hostport = spec["HostPort"]
                    break
            else:
                continue

            envvar = escape_env_var(f"{container_name}_HOST")
            venv.envconfig.setenv[envvar] = gateway_ip

            envvar = escape_env_var(f"{container_name}_{containerport}_PORT")
            venv.envconfig.setenv[envvar] = hostport


@hookimpl
def tox_runtest_post(venv: VirtualEnv) -> None:
    stop_containers(venv)


@hookimpl
def tox_cleanup(session: Session) -> None:  # noqa: F841
    for venv in session.existing_venvs.values():
        stop_containers(venv)


def stop_containers(venv: VirtualEnv) -> None:
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    config = envconfig.config
    action = _newaction(venv, "docker")

    container_configs: Mapping[str, ContainerConfig] = config._docker_container_configs

    for container_name, container in envconfig._docker_containers.items():
        container_config = container_configs[container_name]
        if container_config.stop:
            action.setactivity(
                "docker", f"remove '{container.short_id}' (from {container_name!r})"
            )
            with action:
                container.remove(v=True, force=True)
        else:
            action.setactivity(
                "docker",
                f"leave '{container.short_id}' (from {container_name!r}) running",
            )
            with action:
                pass
    envconfig._docker_containers.clear()


@hookimpl
def tox_addoption(parser: Parser) -> None:
    # necessary to allow the docker= directive in testenv sections
    parser.add_testenv_attribute(
        name="docker",
        type="line-list",
        help="Name of docker images, including tag, to start before the test run",
        default=[],
    )

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
