from typing import Any, cast, Dict, List, Mapping, Optional, Union
import os.path
import time

from docker.models.containers import Container
from tox.config.cli.parser import ToxParser
from tox.config.main import Config
from tox.config.types import EnvList
from tox.execute.api import Outcome
from tox.plugin import impl
from tox.tox_env.api import ToxEnv

from tox_docker.config import ContainerConfig
from tox_docker.plugin import (
    docker_health_check,
    docker_pull,
    docker_run,
    get_env_vars,
    HealthCheckFailed,
    stop_containers,
)
from tox_docker.tox4.config import (
    discover_container_configs,
    EnvRunningContainers,
    parse_container_config,
)
from tox_docker.tox4.log import log

CONTAINER_CONFIGS: Dict[str, ContainerConfig] = {}
ENV_CONTAINERS: EnvRunningContainers = {}


@impl
def tox_configure(config: Config) -> None:
    container_config_names = discover_container_configs(config)

    # validate command line options
    for container_name in config.options.docker_dont_stop:
        if container_name not in container_config_names:
            raise ValueError(
                f"Container {container_name!r} not found (from --docker-dont-stop)"
            )

    for container_name in container_config_names:
        CONTAINER_CONFIGS[container_name] = parse_container_config(
            config, container_name, container_config_names
        )


@impl
def tox_before_run_commands(tox_env: ToxEnv) -> None:
    tox_env.conf.add_config(
        keys=["docker"],
        of_type=EnvList,
        default=EnvList([]),
        desc="docker image configs to load",
        post_process=list,  # type: ignore
    )

    container_names = tox_env.conf["docker"]
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

    ENV_CONTAINERS.setdefault(tox_env, {})
    containers = ENV_CONTAINERS[tox_env]

    for container_config in env_container_configs:
        container = docker_run(container_config, containers, log)
        containers[container_config.name] = container

    all_healthy = True
    for container_name, container in containers.items():
        container_config = CONTAINER_CONFIGS[container_name]
        try:
            docker_health_check(container_config, container, log)
        except HealthCheckFailed as e:
            all_healthy = False
            # TODO: prevent tox from trying tests?
            break

    for container_name, container in containers.items():
        # TODO: we'd really like .update(), but YMMV if you set_env
        # one of the reserved var names manually in tox.ini
        container_config = CONTAINER_CONFIGS[container_name]
        tox_env.conf["set_env"].update_if_not_present(
            get_env_vars(container_config, container)
        )


@impl
def tox_after_run_commands(
    tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]
) -> None:
    env_containers = ENV_CONTAINERS.get(tox_env, [])
    containers_and_configs = [
        (CONTAINER_CONFIGS[name], container)
        for name, container in env_containers.items()
    ]
    stop_containers(containers_and_configs, log)


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
