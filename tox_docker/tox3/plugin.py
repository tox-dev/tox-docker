__all__ = (
    "tox_configure",
    "tox_runtest_pre",
    "tox_runtest_post",
    "tox_addoption",
)

from typing import Dict
import os

from tox import hookimpl
from tox.action import Action
from tox.config import Config, Parser
from tox.venv import VirtualEnv

from tox_docker.config import ContainerConfig, RunningContainers
from tox_docker.plugin import (
    docker_health_check,
    docker_pull,
    docker_run,
    get_env_vars,
    HealthCheckFailed,
    stop_containers,
)
from tox_docker.tox3.config import (
    discover_container_configs,
    EnvRunningContainers,
    parse_container_config,
)
from tox_docker.tox3.log import make_logger

CONTAINER_CONFIGS: Dict[str, ContainerConfig] = {}
ENV_CONTAINERS: EnvRunningContainers = {}


def _newaction(venv: VirtualEnv, message: str) -> Action:
    try:
        # tox 3.7 and later
        return venv.new_action(message)
    except AttributeError:
        return venv.session.newaction(venv, message)


def _config_name(running_name: str) -> str:
    # inverse of tox_docker.config.runas_name()
    suffix = f"-tox-{os.getpid()}"
    assert running_name.endswith(suffix)
    return running_name[: -len(suffix)]


@hookimpl
def tox_configure(config: Config) -> None:
    container_config_names = discover_container_configs(config)

    # validate command line options
    for container_name in config.option.docker_dont_stop:
        if container_name not in container_config_names:
            raise ValueError(
                f"Container {container_name!r} not found (from --docker-dont-stop)"
            )

    for container_name in container_config_names:
        CONTAINER_CONFIGS[container_name] = parse_container_config(
            config, container_name, container_config_names
        )


@hookimpl
def tox_runtest_pre(venv: VirtualEnv) -> None:
    envconfig = venv.envconfig
    container_names = envconfig.docker

    log = make_logger(venv)

    env_container_configs = []

    seen = set()
    for container_name in container_names:
        if container_name not in CONTAINER_CONFIGS:
            raise ValueError(f"Missing [docker:{container_name}] in tox.ini")
        if container_name in seen:
            raise ValueError(f"Container {container_name!r} specified more than once")
        seen.add(container_name)
        env_container_configs.append(CONTAINER_CONFIGS[container_name])

    for container_config in env_container_configs:
        docker_pull(container_config, log)

    ENV_CONTAINERS.setdefault(venv, {})
    running_containers = ENV_CONTAINERS[venv]

    for container_config in env_container_configs:
        container = docker_run(container_config, running_containers, log)
        running_containers[container_config.runas_name] = container

    for running_name, container in running_containers.items():
        container_name = _config_name(running_name)
        container_config = CONTAINER_CONFIGS[container_name]
        try:
            docker_health_check(container_config, container, log)
        except HealthCheckFailed:
            msg = f"{container_config.image!r} (from {container_name!r}) failed health check"
            venv.status = msg
            tox_runtest_post(venv)
            raise

    for running_name, container in running_containers.items():
        container_name = _config_name(running_name)
        container_config = CONTAINER_CONFIGS[container_name]
        for key, val in get_env_vars(container_config, container).items():
            venv.envconfig.setenv[key] = val


@hookimpl
def tox_runtest_post(venv: VirtualEnv) -> None:
    env_containers: RunningContainers = ENV_CONTAINERS.get(venv, {})
    containers_and_configs = [
        (CONTAINER_CONFIGS[_config_name(name)], container)
        for name, container in env_containers.items()
    ]
    log = make_logger(venv)
    stop_containers(containers_and_configs, log)


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
