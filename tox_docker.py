import socket
import sys
import time

from tox import hookimpl
from tox.config import SectionReader
from docker.errors import ImageNotFound
import docker as docker_module
import py


NANOSECONDS = 1000000000


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
        varname[0] = '_'
    for i, c in enumerate(varname):
        if not c.isalnum() and c != '_':
            varname[i] = '_'
    return "".join(varname)


def _newaction(venv, message):
    try:
        # tox 3.7 and later
        return venv.new_action(message)
    except AttributeError:
        return venv.session.newaction(venv, message)


def _get_gateway_ip(container):
    if sys.platform == "darwin":
        # per https://docs.docker.com/v17.12/docker-for-mac/networking/#use-cases-and-workarounds,
        # there is no bridge network available in Docker for Mac, and exposed ports are made
        # available on localhost (but 0.0.0.0 works just as well)
        return "0.0.0.0"
    else:
        return container.attrs["NetworkSettings"]["Gateway"] or "0.0.0.0"


@hookimpl
def tox_configure(config):
    def getfloat(reader, key):
        val = reader.getstring(key)
        if val is None:
            return None

        try:
            return float(val)
        except ValueError:
            msg = "{!r} is not a number (for {} in [{}])".format(
                val, key, reader.section_name
            )
            raise ValueError(msg)

    def gettime(reader, key):
        return int(getfloat(reader, key) * NANOSECONDS)

    def getint(reader, key):
        raw = getfloat(reader, key)
        val = int(raw)
        if val != raw:
            msg = "{!r} is not an int (for {} in [{}])".format(
                val, key, reader.section_name
            )
            raise ValueError(msg)
        return val

    inipath = str(config.toxinipath)
    iniparser = py.iniconfig.IniConfig(inipath)

    image_configs = {}
    for section in iniparser.sections:
        if not section.startswith("docker:"):
            continue
        reader = SectionReader(section, iniparser)

        _, _, image = section.partition(":")
        image_configs[image] = {
            "healthcheck_cmd": reader.getargv("healthcheck_cmd"),
            "healthcheck_interval": gettime(reader, "healthcheck_interval"),
            "healthcheck_timeout": gettime(reader, "healthcheck_timeout"),
            "healthcheck_retries": getint(reader, "healthcheck_retries"),
            "healthcheck_start_period": gettime(reader, "healthcheck_start_period"),
        }

    config._docker_image_configs = image_configs


@hookimpl
def tox_runtest_pre(venv):
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    config = envconfig.config
    image_configs = config._docker_image_configs

    docker = docker_module.from_env(version="auto")
    action = _newaction(venv, "docker")

    environment = {}
    for value in envconfig.dockerenv:
        envvar, _, value = value.partition("=")
        environment[envvar] = value
        venv.envconfig.setenv[envvar] = value

    seen = set()
    for image in envconfig.docker:
        name, _, tag = image.partition(":")
        if name in seen:
            raise ValueError(
                "Docker image {!r} is specified more than once".format(name)
            )
        seen.add(name)

        try:
            docker.images.get(image)
        except ImageNotFound:
            action.setactivity("docker", "pull {!r}".format(image))
            with action:
                docker.images.pull(name, tag=tag or None)

    envconfig._docker_containers = []
    for image in envconfig.docker:
        image_config = image_configs.get(image, {})
        hc_cmd = image_config.get("healthcheck_cmd")
        hc_interval = image_config.get("healthcheck_interval")
        hc_timeout = image_config.get("healthcheck_timeout")
        hc_retries = image_config.get("healthcheck_retries")
        hc_start_period = image_config.get("healthcheck_start_period")

        if hc_cmd is not None \
           and hc_interval is not None \
           and hc_timeout is not None \
           and hc_retries is not None \
           and hc_start_period is not None:
            healthcheck = {
                "test": ["CMD-SHELL"] + hc_cmd,
                "interval": hc_interval,
                "timeout": hc_timeout,
                "retries": hc_retries,
                "start_period": hc_start_period,
            }
        else:
            healthcheck = None

        action.setactivity("docker", "run {!r}".format(image))
        with action:
            container = docker.containers.run(
                image,
                detach=True,
                publish_all_ports=True,
                environment=environment,
                healthcheck=healthcheck,
            )

        envconfig._docker_containers.append(container)
        container.reload()

    for container in envconfig._docker_containers:
        image = container.attrs["Config"]["Image"]
        if "Health" in container.attrs["State"]:
            action.setactivity("docker", "health check: {!r}".format(image))
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
                        raise HealthCheckFailed("{!r} failed health check".format(image))

        name, _, tag = image.partition(":")
        gateway_ip = _get_gateway_ip(container)
        for containerport, hostports in container.attrs["NetworkSettings"]["Ports"].items():
            for spec in hostports:
                if spec["HostIp"] == "0.0.0.0":
                    hostport = spec["HostPort"]
                    break
            else:
                continue

            envvar = escape_env_var("{}_HOST".format(
                name,
            ))
            venv.envconfig.setenv[envvar] = gateway_ip

            envvar = escape_env_var("{}_{}_PORT".format(
                name,
                containerport,
            ))
            venv.envconfig.setenv[envvar] = hostport

            # TODO: remove in 2.0
            _, proto = containerport.split("/")
            envvar = escape_env_var("{}_{}".format(
                name,
                containerport,
            ))
            venv.envconfig.setenv[envvar] = hostport

            _, proto = containerport.split("/")
            if proto == "udp":
                continue

            # mostly-busy-loop until we can connect to that port; that
            # will be our signal that the container is ready (meh)
            start = time.time()
            while (time.time() - start) < 30:
                try:
                    sock = socket.create_connection(
                        address=(gateway_ip, int(hostport)),
                        timeout=0.1,
                    )
                except socket.error:
                    time.sleep(0.1)
                else:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                    break
            else:
                raise Exception(
                    "Never got answer on port {} from {}".format(containerport, name)
                )


@hookimpl
def tox_runtest_post(venv):
    envconfig = venv.envconfig
    if not envconfig.docker:
        return

    action = _newaction(venv, "docker")

    for container in envconfig._docker_containers:
        action.setactivity("docker", "remove '{}' (forced)".format(container.short_id))
        with action:
            container.remove(v=True, force=True)


@hookimpl
def tox_addoption(parser):
    parser.add_testenv_attribute(
        name="docker",
        type="line-list",
        help="Name of docker images, including tag, to start before the test run",
        default=[],
    )
    parser.add_testenv_attribute(
        name="dockerenv",
        type="line-list",
        help="List of ENVVAR=VALUE pairs that will be passed to all containers",
        default=[],
    )
