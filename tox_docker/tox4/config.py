from typing import Dict, List, Optional

from tox.config.sets import ConfigSet

from tox_docker.config import (
    ContainerConfig,
    Dockerfile,
    Image,
    Link,
    Port,
    Volume,
)

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
            of_type=Optional[Image],
            default=None,
            desc="docker image to run [specify one of image or dockerfile]",
        )
        self.add_config(
            keys=["dockerfile"],
            of_type=Optional[Dockerfile],
            default=None,
            desc="Dockerfile to build/run [specify one of image or dockerfile]",
        )
        self.add_config(
            keys=["dockerfile_target"],
            of_type=str,
            default="",
            desc="Dockerfile target to build/run",
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
    if docker_config["image"] and docker_config["dockerfile"]:
        raise ValueError(f"{docker_config.name}: specify image or dockerfile, not both")
    elif not docker_config["image"] and not docker_config["dockerfile"]:
        raise ValueError(f"{docker_config.name}: specify one of image or dockerfile")

    if docker_config["dockerfile_target"] and not docker_config["dockerfile"]:
        raise ValueError(
            f"{docker_config.name}: dockerfile_target specified, but no dockerfile"
        )

    return ContainerConfig(
        name=docker_config.name,
        image=docker_config["image"],
        dockerfile=docker_config["dockerfile"],
        dockerfile_target=docker_config["dockerfile_target"],
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
