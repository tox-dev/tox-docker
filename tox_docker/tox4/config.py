from typing import Dict, List

from tox.config.sets import ConfigSet

from tox_docker.config import ContainerConfig, Image, Link, Port, Volume

# nanoseconds in a second; named "SECOND" so that "1.5 * SECOND" makes sense
SECOND = 1000000000


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
