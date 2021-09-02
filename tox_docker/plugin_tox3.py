import time

from docker.errors import ImageNotFound
from tox import hookimpl
import docker as docker_module

from tox_docker.config_tox3 import (
    discover_container_configs,
    parse_container_config,
)
from tox_docker.plugin import escape_env_var, get_gateway_ip, HealthCheckFailed


def _newaction(venv, message):
    try:
        # tox 3.7 and later
        return venv.new_action(message)
    except AttributeError:
        return venv.session.newaction(venv, message)


@hookimpl
def tox_configure(config):
    container_config_names = discover_container_configs(config)

    # validate command line options
    for container_name in config.option.docker_dont_stop:
        if container_name not in container_config_names:
            raise ValueError(
                f"Container {container_name!r} not found (from --docker-dont-stop)"
            )

    container_configs = {}
    for container_name in container_config_names:
        container_configs[container_name] = parse_container_config(
            config, container_name, container_config_names
        )

    config._docker_container_configs = container_configs


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

        ports = container_config.get("ports", [])

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

        gateway_ip = get_gateway_ip(container)
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
