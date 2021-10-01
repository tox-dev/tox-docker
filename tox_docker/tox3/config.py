from typing import Container, Dict, Mapping, Optional, Sequence
import re

from tox.config import Config, SectionReader
from tox.venv import VirtualEnv
import py

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


EnvRunningContainers = Dict[VirtualEnv, RunningContainers]


def getfloat(reader: SectionReader, key: str) -> Optional[float]:
    val = reader.getstring(key)
    if val is None:
        return None

    try:
        return float(val)
    except ValueError:
        msg = f"{val!r} is not a number (for {key} in [{reader.section_name}])"
        raise ValueError(msg)


def gettime(reader: SectionReader, key: str) -> Optional[int]:
    raw = getfloat(reader, key)
    if raw is None:
        return None

    return int(raw * SECOND)


def getint(reader: SectionReader, key: str) -> Optional[int]:
    raw = getfloat(reader, key)
    if raw is None:
        return None

    val = int(raw)
    if val != raw:
        msg = f"{val!r} is not an int (for {key} in [{reader.section_name}])"
        raise ValueError(msg)
    return val


def getenvdict(reader: SectionReader, key: str) -> Mapping[str, str]:
    environment = {}
    for value in reader.getlist(key):
        envvar, _, value = value.partition("=")
        environment[envvar] = value
    return environment


def discover_container_configs(config: Config) -> Sequence[str]:
    """
    Read the tox.ini, and return a list of docker container configs.

    """

    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    container_names = set()
    for section in iniparser.sections:
        if not section.startswith("docker:"):
            continue

        _, _, container_name = section.partition(":")
        if not re.match(r"^[a-zA-Z][-_.a-zA-Z0-9]+$", container_name):
            raise ValueError(f"{container_name!r} is not a valid container name")

        # populated in the next loop
        container_names.add(container_name)

    return list(container_names)


def parse_container_config(
    config: Config, container_name: str, all_container_names: Container[str]
) -> ContainerConfig:
    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    reader = SectionReader(f"docker:{container_name}", iniparser)
    reader.addsubstitutions(
        distdir=config.distdir,
        homedir=config.homedir,
        toxinidir=config.toxinidir,
        toxworkdir=config.toxworkdir,
    )

    kwargs = {
        "name": container_name,
        "image": Image(reader.getstring("image")),
        "stop": container_name not in config.option.docker_dont_stop,
    }

    if reader.getstring("environment"):
        env = getenvdict(reader, "environment")
        kwargs["environment"] = env

    if reader.getstring("healthcheck_cmd"):
        kwargs["healthcheck_cmd"] = reader.getstring("healthcheck_cmd")
    if reader.getstring("healthcheck_interval"):
        kwargs["healthcheck_interval"] = gettime(reader, "healthcheck_interval")
    if reader.getstring("healthcheck_timeout"):
        kwargs["healthcheck_timeout"] = gettime(reader, "healthcheck_timeout")
    if reader.getstring("healthcheck_start_period"):
        kwargs["healthcheck_start_period"] = gettime(reader, "healthcheck_start_period")
    if reader.getstring("healthcheck_retries"):
        kwargs["healthcheck_retries"] = getint(reader, "healthcheck_retries")

    if reader.getstring("ports"):
        kwargs["ports"] = [Port(line) for line in reader.getlist("ports")]

    if reader.getstring("links"):
        kwargs["links"] = [Link(line) for line in reader.getlist("links")]

    if reader.getstring("volumes"):
        kwargs["volumes"] = [Volume(line) for line in reader.getlist("volumes")]

    return ContainerConfig(**kwargs)
