import re

from tox.config import SectionReader
import py

from tox_docker.config import validate_link, validate_port, validate_volume

# nanoseconds in a second; named "SECOND" so that "1.5 * SECOND" makes sense
SECOND = 1000000000


def getfloat(reader, key):
    val = reader.getstring(key)
    if val is None:
        return None

    try:
        return float(val)
    except ValueError:
        msg = f"{val!r} is not a number (for {key} in [{reader.section_name}])"
        raise ValueError(msg)


def gettime(reader, key):
    return int(getfloat(reader, key) * SECOND)


def getint(reader, key):
    raw = getfloat(reader, key)
    val = int(raw)
    if val != raw:
        msg = f"{val!r} is not an int (for {key} in [{reader.section_name}])"
        raise ValueError(msg)
    return val


def getenvdict(reader, key):
    environment = {}
    for value in reader.getlist(key):
        envvar, _, value = value.partition("=")
        environment[envvar] = value
    return environment


def discover_container_configs(config):
    """
    Read the tox.ini, and return a list of docker container configs.

    """

    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    container_configs = set()
    for section in iniparser.sections:
        if not section.startswith("docker:"):
            continue

        _, _, container_name = section.partition(":")
        if not re.match(r"^[a-zA-Z][-_.a-zA-Z0-9]+$", container_name):
            raise ValueError(f"{container_name!r} is not a valid container name")

        # populated in the next loop
        container_configs.add(container_name)

    return list(container_configs)


def parse_container_config(config, container_name, all_container_names):
    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    reader = SectionReader(f"docker:{container_name}", iniparser)
    reader.addsubstitutions(
        distdir=config.distdir,
        homedir=config.homedir,
        toxinidir=config.toxinidir,
        toxworkdir=config.toxworkdir,
    )

    container_config = {
        "image": reader.getstring("image"),
        "stop": container_name not in config.option.docker_dont_stop,
    }

    if reader.getstring("environment"):
        env = getenvdict(reader, "environment")
        container_config["environment"] = env

    if reader.getstring("healthcheck_cmd"):
        container_config["healthcheck_cmd"] = reader.getstring("healthcheck_cmd")
    if reader.getstring("healthcheck_interval"):
        container_config["healthcheck_interval"] = gettime(
            reader, "healthcheck_interval"
        )
    if reader.getstring("healthcheck_timeout"):
        container_config["healthcheck_timeout"] = gettime(reader, "healthcheck_timeout")
    if reader.getstring("healthcheck_start_period"):
        container_config["healthcheck_start_period"] = gettime(
            reader, "healthcheck_start_period"
        )
    if reader.getstring("healthcheck_retries"):
        container_config["healthcheck_retries"] = getint(reader, "healthcheck_retries")

    if reader.getstring("ports"):
        ports = {}
        for port_mapping in reader.getlist("ports"):
            host_port, container_port_proto = validate_port(port_mapping)
            ports.setdefault(container_port_proto, set())
            ports[container_port_proto].add(host_port)

        container_config["ports"] = {k: list(v) for k, v in ports.items()}

    if reader.getstring("links"):
        container_config["links"] = dict(
            validate_link(link_line, all_container_names)
            for link_line in reader.getlist("links")
            if link_line.strip()
        )

    if reader.getstring("volumes"):
        container_config["mounts"] = [
            validate_volume(volume_line)
            for volume_line in reader.getlist("volumes")
            if volume_line.strip()
        ]

    return container_config
