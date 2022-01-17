__all__ = (
    "tox_add_env_config",
    "tox_add_option",
    "tox_after_run_commands",
    "tox_before_run_commands",
)

from typing import List

from tox.config.cli.parser import ToxParser
from tox.config.loader.section import Section
from tox.config.sets import EnvConfigSet
from tox.execute.api import Outcome
from tox.plugin import impl
from tox.session.state import State
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Fail

from tox_docker.config import RunningContainers
from tox_docker.plugin import (
    docker_get,
    docker_health_check,
    docker_pull,
    docker_run,
    get_env_vars,
    HealthCheckFailed,
    stop_containers,
)
from tox_docker.tox4.config import DockerConfigSet, parse_container_config
from tox_docker.tox4.log import log


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
        docker_pull(container_config, log)

    config_and_container = []
    running_containers: RunningContainers = {}
    for container_config in container_configs:
        container = docker_run(container_config, running_containers, log)
        config_and_container.append((container_config, container))
        running_containers[container_config.runas_name] = container

    for container_config, container in config_and_container:
        try:
            docker_health_check(container_config, container, log)
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

    stop_containers(configs_and_containers, log)


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
