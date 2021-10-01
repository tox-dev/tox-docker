from typing import Dict, List, Sequence

from tox.config.loader.section import Section
from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.tox_env.api import ToxEnv

from tox_docker.config import (
    ContainerConfig,
    Image,
    Link,
    Port,
    RunningContainers,
    Volume,
)

# nanoseconds in a second; named "SECOND" so that "1.5 * SECOND" makes sense
SECOND = 1000000000

EnvRunningContainers = Dict[ToxEnv, RunningContainers]


class MissingRequiredSetting(Exception):
    pass


def image_required(image: Image) -> Image:
    if not image.name:
        raise MissingRequiredSetting("image")

    return image


class DockerConfigSet(ConfigSet):
    def register_config(self) -> None:
        self.add_config(
            keys=["image"],
            of_type=Image,
            default=Image(""),
            desc="docker image to run",
            post_process=image_required,
        )
        self.add_config(
            keys=["environment"],
            of_type=Dict[str, str],
            default={},
            desc="environment variables to pass to the docker container",
        )
        self.add_config(
            keys=["ports"],
            of_type=List[Port],
            default=[],
            desc="ports to expose",
        )
        self.add_config(
            keys=["links"],
            of_type=List[Link],
            default=[],
            desc="containers to link",
        )
        self.add_config(
            keys=["volumes"],
            of_type=List[Volume],
            default=[],
            desc="volumes to attach",
        )

        self.add_config(
            keys=["healthcheck_cmd"],
            of_type=str,
            default="",
            desc="docker healthcheck command",
        )
        self.add_config(
            keys=["healthcheck_interval"],
            of_type=float,
            default=0,
            desc="docker healthcheck interval",
            post_process=lambda num: int(num * SECOND),
        )
        self.add_config(
            keys=["healthcheck_timeout"],
            of_type=float,
            default=0,
            desc="docker healthcheck timeout",
            post_process=lambda num: int(num * SECOND),
        )
        self.add_config(
            keys=["healthcheck_start_period"],
            of_type=float,
            default=0,
            desc="docker healthcheck startup grace period",
            post_process=lambda num: int(num * SECOND),
        )
        self.add_config(
            keys=["healthcheck_retries"],
            of_type=int,
            default=0,
            desc="docker healthcheck retry count",
        )


class EnvDockerConfigSet(ConfigSet):
    def register_config(self) -> None:
        def build_docker_config_set(container_name: object) -> DockerConfigSet:
            assert isinstance(container_name, str)
            return self._conf.get_section_config(
                section=Section("docker", container_name),
                base=[],
                of_type=DockerConfigSet,
                for_env=None,
            )

        self.add_config(
            keys=["docker"],
            of_type=List[DockerConfigSet],
            default=[],
            desc="docker image configs to load",
            factory=build_docker_config_set,  # type: ignore
        )


def discover_container_configs(config: Config) -> Sequence[DockerConfigSet]:
    """
    Read the tox.ini, and return a list of docker container configs.

    """

    docker_configs = set()
    for env_name in config:
        env_config = config.get_section_config(
            section=Section("testenv", env_name),
            base=[],
            of_type=EnvDockerConfigSet,
            for_env=None,
        )
        docker_configs.update(env_config.load("docker"))

    return list(docker_configs)


def parse_container_config(docker_config: DockerConfigSet) -> ContainerConfig:
    return ContainerConfig(
        name=docker_config.name,
        image=docker_config["image"],
        stop=docker_config.name not in docker_config._conf.options.docker_dont_stop,
        environment=docker_config["environment"],
        healthcheck_cmd=docker_config["healthcheck_cmd"],
        healthcheck_interval=docker_config["healthcheck_interval"],
        healthcheck_timeout=docker_config["healthcheck_timeout"],
        healthcheck_start_period=docker_config["healthcheck_start_period"],
        healthcheck_retries=docker_config["healthcheck_retries"],
        ports=docker_config["ports"],
        links=docker_config["links"],
        volumes=docker_config["volumes"],
    )
