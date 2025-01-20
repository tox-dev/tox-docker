from pathlib import Path
from typing import Collection, Dict, List, Mapping, Optional
import os
import os.path
import re

from docker.models.containers import Container as DockerContainer
from docker.models.images import Image as DockerImage
from docker.types import Mount
from tox.config.sets import ConfigSet

# nanoseconds in a second; named "SECOND" so that "1.5 * SECOND" makes sense
SECOND = 1000000000

RunningContainers = Dict[str, DockerContainer]

IMAGE_NAME = re.compile(
    # adapted from https://stackoverflow.com/a/39672069, used under CC-BY-SA
    r"^"
    r"("
    r"(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?"
    r"(?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*"
    r")"
    r"(?::((?![.-])[a-zA-Z0-9_.-]{1,128}))?"
    r"$"
)

ENV_VAR = re.compile("[A-Z0-9_]+")


def runas_name(container_name: str, pid: Optional[int] = None) -> str:
    """
    Generate a name safe for use in parallel scenarios

    This can be either separate invocations of tox (eg on a busy CI server)
    or `tox -p`. The returned name will be stable for a given container name,
    to avoid needing to maintain a mapping.

    """
    pid = pid or os.getpid()
    return f"{container_name}-tox-{pid}"


class Image:
    def __init__(self, config_line: str) -> None:
        match = IMAGE_NAME.match(config_line)
        if not match:
            raise ValueError(f"{config_line!r} is not a valid image name")
        self.name, self.tag = match.groups()

    def __str__(self) -> str:
        if self.tag:
            return f"{self.name}:{self.tag}"
        return self.name

    def __repr__(self) -> str:
        return repr(str(self))


class Dockerfile:
    def __init__(self, config_line: str) -> None:
        self.path = Path(config_line)
        self.directory = str(self.path.parent)
        self.filename = str(self.path.name)

    def __repr__(self) -> str:
        return str(self.path)


class ExposedPort:
    def __init__(self, config_line: str) -> None:
        env_var, _, container_port_proto = config_line.partition("=")
        container_port, _, protocol = container_port_proto.partition("/")

        if not ENV_VAR.match(env_var):
            raise ValueError(f"{env_var} is not a valid environment variable")
        if not container_port.isdigit():
            raise ValueError("container port must be an int")
        if protocol.lower() not in ("tcp", "udp"):
            raise ValueError("protocol must be tcp or udp")

        self.env_var = env_var
        self.container_port = container_port
        self.protocol = protocol

    @property
    def container_port_proto(self) -> str:
        return f"{self.container_port}/{self.protocol}"


class HostVar:
    def __init__(self, config_line: str) -> None:
        if not ENV_VAR.match(config_line):
            raise ValueError(f"{config_line!r} is not a valid environment variable")
        self.host_var = config_line

    def __str__(self) -> str:
        return self.host_var

    def __repr__(self) -> str:
        return repr(str(self))


class ContainerVar:
    def __init__(self, config_line: str) -> None:
        if not ENV_VAR.match(config_line):
            raise ValueError(f"{config_line!r} is not a valid environment variable")
        self.container_var = config_line

    def __str__(self) -> str:
        return self.container_var

    def __repr__(self) -> str:
        return repr(str(self))


class Link:
    def __init__(self, config_line: str) -> None:
        target, sep, alias = config_line.partition(":")

        if sep and not alias:
            raise ValueError(f"Link '{target}:' missing alias")

        self.target = runas_name(target)

        # this is what the target will be known as INSIDE the
        # container, so don't substitute the runas_name here
        self.alias = alias or target


class Volume:
    def __init__(self, config_line: str) -> None:
        parts = config_line.split(":")
        if len(parts) != 4:
            raise ValueError(f"Volume {config_line!r} is malformed")
        if parts[0] != "bind":
            raise ValueError(f"Volume {config_line!r} type must be 'bind:'")
        if parts[1] not in ("ro", "rw"):
            raise ValueError(f"Volume {config_line!r} options must be 'ro' or 'rw'")

        volume_type, mode, outside, inside = parts
        if not os.path.isabs(outside):
            raise ValueError(f"Volume source {outside!r} must be an absolute path")
        elif not os.path.exists(outside) and parts[1] == "rw":
            os.makedirs(outside, exist_ok=True)
        if not os.path.isabs(inside):
            raise ValueError(f"Mount point {inside!r} must be an absolute path")

        self.docker_mount = Mount(
            source=outside,
            target=inside,
            type=volume_type,
            read_only=bool(mode == "ro"),
        )


class ContainerConfig:
    def __init__(
        self,
        name: str,
        image: Optional[Image],
        dockerfile: Optional[Dockerfile],
        dockerfile_target: str,
        stop: bool,
        environment: Optional[Mapping[str, str]] = None,
        healthcheck_cmd: Optional[str] = None,
        healthcheck_interval: Optional[float] = None,
        healthcheck_timeout: Optional[float] = None,
        healthcheck_start_period: Optional[float] = None,
        healthcheck_retries: Optional[int] = None,
        expose: Optional[Collection[ExposedPort]] = None,
        host_var: Optional[HostVar] = None,
        container_var: Optional[ContainerVar] = None,
        links: Optional[Collection[Link]] = None,
        volumes: Optional[Collection[Volume]] = None,
    ) -> None:
        self.name = name
        self.runas_name = runas_name(name)
        self.image = image
        self.dockerfile = dockerfile
        self.dockerfile_target = dockerfile_target
        self.stop = stop
        self.environment: Mapping[str, str] = environment or {}
        self.expose: Collection[ExposedPort] = expose or []
        self.host_var = str(host_var) if host_var else ""
        self.container_var = str(container_var) if container_var else ""
        self.links: Collection[Link] = links or []
        self.mounts: Collection[Mount] = [v.docker_mount for v in volumes or ()]

        self.healthcheck_cmd = healthcheck_cmd
        self.healthcheck_interval = (
            int(healthcheck_interval) if healthcheck_interval else None
        )
        self.healthcheck_timeout = (
            int(healthcheck_timeout) if healthcheck_timeout else None
        )
        self.healthcheck_start_period = (
            int(healthcheck_start_period) if healthcheck_start_period else None
        )
        self.healthcheck_retries = healthcheck_retries

        self.runnable_image: Optional[DockerImage] = None


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
            keys=["expose"],
            of_type=List[ExposedPort],
            default=[],
            desc="container ports to expose to the testenv",
        )
        self.add_config(
            keys=["host_var"],
            of_type=Optional[HostVar],
            default=None,
            desc="environment variable to pass hostname or IP of container to testenv",
        )
        self.add_config(
            keys=["container_var"],
            of_type=Optional[ContainerVar],
            default=None,
            desc="environment variable to pass the name of the container to testenv",
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
        expose=docker_config["expose"],
        host_var=docker_config["host_var"],
        links=docker_config["links"],
        volumes=docker_config["volumes"],
    )
