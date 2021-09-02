from typing import List, Optional
import os
import socket
import sys

from docker.models.containers import Container


class HealthCheckFailed(Exception):
    pass


def get_gateway_ip(container: Container) -> str:
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


def escape_env_var(varname: str) -> str:
    """
    Convert a string to a form suitable for use as an environment variable.

    The result will be all uppercase, and will have all invalid characters
    replaced by an underscore.

    The result will match the following regex: [a-zA-Z_][a-zA-Z0-9_]*

    Example:
        "my.private.registry/cat/image" will become
        "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    """
    varletters = list(varname.upper())
    if not varletters[0].isalpha():
        varletters[0] = "_"
    for i, c in enumerate(varletters):
        if not c.isalnum() and c != "_":
            varletters[i] = "_"
    return "".join(varletters)
