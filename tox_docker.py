import socket
import time

from tox import hookimpl
from tox.config import Config
import docker as docker_module


@hookimpl
def tox_runtest_pre(venv):
    conf = venv.envconfig
    docker = docker_module.from_env(version="auto")

    seen = set()
    for image in conf.docker:
        baseimage = image.split(":", 1)[0]
        if baseimage in seen:
            raise ValueError("Docker image %r is specified more than once" % baseimage)
        seen.add(baseimage)

    environment = {}
    for value in conf.dockerenv:
        envvar, _, value = value.partition("=")
        environment[envvar] = value
        venv.envconfig.setenv[envvar] = value

    conf._docker = {}
    for image in conf.docker:
        container = docker.containers.run(
            image,
            detach=True,
            publish_all_ports=True,
            environment=environment,
        )

        baseimage = image.split(":", 1)[0]
        conf._docker[baseimage] = container

        # >>> container.attrs["NetworkSettings"]["Ports"]
        # {u'5432/tcp': [{u'HostPort': u'32782', u'HostIp': u'0.0.0.0'}]}
        container.reload()
        for containerport, hostports in container.attrs["NetworkSettings"]["Ports"].items():
            hostport = None
            for spec in hostports:
                if spec["HostIp"] == "0.0.0.0":
                    hostport = spec["HostPort"]
                    break

            if not hostport:
                continue

            envvar = "{}_{}".format(
                baseimage.upper(),
                containerport.replace("/", "_").upper(),
            )
            venv.envconfig.setenv[envvar] = hostport

            # mostly-busy-loop until we can connect to that port; that
            # will be our signal that the container is ready (meh)
            start = time.time()
            while (time.time() - start) < 30:
                try:
                    sock = socket.create_connection(
                        address=("0.0.0.0", int(hostport)),
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
                    "Never got answer on port {} from {}".format(containerport, baseimage)
                )



@hookimpl
def tox_runtest_post(venv):
    conf = venv.envconfig

    for container in conf._docker.values():
        container.remove(force=True)


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
