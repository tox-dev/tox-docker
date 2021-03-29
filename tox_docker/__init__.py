import os
import re
import socket
import sys
import time

from docker.errors import ImageNotFound
from docker.types import Mount
from tox import hookimpl
from tox.config import SectionReader
import docker as docker_module
import py

# nanoseconds in a second; named "SECOND" so that "1.5 * SECOND" makes sense
SECOND = 1000000000


class HealthCheckFailed(Exception):
    pass


def escape_env_var(varname):
    """
    Convert a string to a form suitable for use as an environment variable.

    The result will be all uppercase, and will have all invalid characters
    replaced by an underscore.

    The result will match the following regex: [a-zA-Z_][a-zA-Z0-9_]*

    Example:
        "my.private.registry/cat/image" will become
        "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    """
    varname = list(varname.upper())
    if not varname[0].isalpha():
        varname[0] = "_"
    for i, c in enumerate(varname):
        if not c.isalnum() and c != "_":
            varname[i] = "_"
    return "".join(varname)


def _newaction(venv, message):
    try:
        # tox 3.7 and later
        return venv.new_action(message)
    except AttributeError:
        return venv.session.newaction(venv, message)


def _get_gateway_ip(container):
    gateway = os.getenv("TOX_DOCKER_GATEWAY")
    if gateway:
        ip = socket.gethostbyname(gateway)
    elif sys.platform == "darwin":
        # https://docs.docker.com/docker-for-mac/networking/#use-cases-and-workarounds:
        # there is no bridge network available in Docker for Mac, and exposed ports are
        # made available on localhost (but 0.0.0.0 works just as well)
        ip = "0.0.0.0"
    else:
        ip = container.attrs["NetworkSettings"]["Gateway"] or "0.0.0.0"
    return ip


@hookimpl  # noqa: C901
def tox_configure(config):  # noqa: C901
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

    # discover container configs
    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    container_configs = {}
    for section in iniparser.sections:
        if not section.startswith("docker:"):
            continue

        _, _, container_name = section.partition(":")
        if not re.match(r"^[a-zA-Z][-_.a-zA-Z0-9]+$", container_name):
            raise ValueError(f"{container_name!r} is not a valid container name")

        # populated in the next loop
        container_configs[container_name] = {}

    # validate command line options
    for container_name in config.option.docker_dont_stop:
        if container_name not in container_configs:
            raise ValueError(
                f"Container {container_name!r} not found (from --docker-dont-stop)"
            )

    # validate tox.ini
    for section in iniparser.sections:
        if not section.startswith("docker:"):
            continue
        reader = SectionReader(section, iniparser)
        reader.addsubstitutions(
            distdir=config.distdir,
            homedir=config.homedir,
            toxinidir=config.toxinidir,
            toxworkdir=config.toxworkdir,
        )
        _, _, container_name = section.partition(":")

        container_configs[container_name].update(
            {
                "image": reader.getstring("image"),
                "stop": container_name not in config.option.docker_dont_stop,
            }
        )

        if reader.getstring("environment"):
            env = getenvdict(reader, "environment")
            container_configs[container_name]["environment"] = env

        if reader.getstring("healthcheck_cmd"):
            container_configs[container_name]["healthcheck_cmd"] = reader.getstring(
                "healthcheck_cmd"
            )
        if reader.getstring("healthcheck_interval"):
            container_configs[container_name]["healthcheck_interval"] = gettime(
                reader, "healthcheck_interval"
            )
        if reader.getstring("healthcheck_timeout"):
            container_configs[container_name]["healthcheck_timeout"] = gettime(
                reader, "healthcheck_timeout"
            )
        if reader.getstring("healthcheck_start_period"):
            container_configs[container_name]["healthcheck_start_period"] = gettime(
                reader, "healthcheck_start_period"
            )
        if reader.getstring("healthcheck_retries"):
            container_configs[container_name]["healthcheck_retries"] = getint(
                reader, "healthcheck_retries"
            )

        if reader.getstring("ports"):
            container_configs[container_name]["ports"] = reader.getlist("ports")

        if reader.getstring("links"):
            container_configs[container_name]["links"] = dict(
                _validate_link_line(link_line, container_configs.keys())
                for link_line in reader.getlist("links")
                if link_line.strip()
            )

        if reader.getstring("volumes"):
            container_configs[container_name]["mounts"] = [
                _validate_volume_line(volume_line)
                for volume_line in reader.getlist("volumes")
                if volume_line.strip()
            ]

    config._docker_container_configs = container_configs


def _validate_port(port_line):
    host_port, _, container_port_proto = port_line.partition(":")
    host_port = int(host_port)

    container_port, _, protocol = container_port_proto.partition("/")
    container_port = int(container_port)

    if protocol.lower() not in ("tcp", "udp"):
        raise ValueError("protocol is not tcp or udp")

    return (host_port, container_port_proto)


def _validate_link_line(link_line, container_names):
    other_container_name, sep, alias = link_line.partition(":")
    if sep and not alias:
        raise ValueError(f"Link '{other_container_name}:' missing alias")
    if other_container_name not in container_names:
        raise ValueError(f"Container {other_container_name!r} not defined")
    return other_container_name, alias or other_container_name


def _validate_volume_line(volume_line):
    parts = volume_line.split(":")
    if len(parts) != 4:
        raise ValueError(f"Volume {volume_line!r} is malformed")
    if parts[0] != "bind":
        raise ValueError(f"Volume {volume_line!r} type must be 'bind:'")
    if parts[1] not in ("ro", "rw"):
        raise ValueError(f"Volume {volume_line!r} options must be 'ro' or 'rw'")

    volume_type, mode, outside, inside = parts
    if not os.path.exists(outside):
        raise ValueError(f"Volume source {outside!r} does not exist")
    if not os.path.isabs(outside):
        raise ValueError(f"Volume source {outside!r} must be an absolute path")
    if not os.path.isabs(inside):
        raise ValueError(f"Mount point {inside!r} must be an absolute path")

    return Mount(
        source=outside,
        target=inside,
        type=volume_type,
        read_only=bool(mode == "ro"),
    )


@hookimpl  # noqa: C901
def tox_runtest_pre(venv):  # noqa: C901
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    config = envconfig.config
    container_configs = config._docker_container_configs

    docker = docker_module.from_env(version="auto")
    action = _newaction(venv, "docker")

    seen = set()
    for container_name in envconfig.docker:
        if container_name not in container_configs:
            raise ValueError(f"Missing [docker:{container_name}] in tox.ini")
        if container_name in seen:
            raise ValueError(f"Container {container_name!r} specified more than once")
        seen.add(container_name)

        image = container_configs[container_name]["image"]
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
        hc_cmd = container_config.get("healthcheck_cmd")
        hc_interval = container_config.get("healthcheck_interval")
        hc_timeout = container_config.get("healthcheck_timeout")
        hc_retries = container_config.get("healthcheck_retries")
        hc_start_period = container_config.get("healthcheck_start_period")

        healthcheck = {}
        if hc_cmd:
            healthcheck["test"] = ["CMD-SHELL", hc_cmd]
        if hc_interval:
            healthcheck["interval"] = hc_interval
        if hc_timeout:
            healthcheck["timeout"] = hc_timeout
        if hc_start_period:
            healthcheck["start_period"] = hc_start_period
        if hc_retries:
            healthcheck["retries"] = hc_retries

        if healthcheck == {}:
            healthcheck = None

        ports = {}
        for port_mapping in container_config.get("ports", []):
            host_port, container_port_proto = _validate_port(port_mapping)
            existing_ports = set(ports.get(container_port_proto, []))
            existing_ports.add(host_port)
            ports[container_port_proto] = list(existing_ports)

        links = {}
        for other_container_name, alias in container_config.get("links", {}).items():
            other_container = envconfig._docker_containers[other_container_name]
            links[other_container.id] = alias

        image = container_config["image"]
        environment = container_config.get("environment", {})

        action.setactivity("docker", f"run {image!r} (from {container_name!r})")
        with action:
            container = docker.containers.run(
                image,
                detach=True,
                environment=environment,
                healthcheck=healthcheck,
                labels={"tox_docker_container_name": container_name},
                links=links,
                name=container_name,
                ports=ports,
                publish_all_ports=len(ports) == 0,
                mounts=container_config.get("mounts", []),
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

        gateway_ip = _get_gateway_ip(container)
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
def tox_runtest_post(venv):
    stop_containers(venv)


@hookimpl
def tox_cleanup(session):  # noqa: F841
    for venv in session.existing_venvs.values():
        stop_containers(venv)


def stop_containers(venv):
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    config = envconfig.config
    action = _newaction(venv, "docker")

    for container_name, container in envconfig._docker_containers.items():
        container_config = config._docker_container_configs[container_name]
        if container_config["stop"]:
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
def tox_addoption(parser):
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
