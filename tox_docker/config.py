from typing import Container, Mapping, Optional, Sequence, Tuple
import os.path

from docker.types import Mount


class ContainerConfig:
    def __init__(
        self,
        image: str,
        stop: bool,
        environment: Optional[Mapping[str, str]] = None,
        healthcheck_cmd: Optional[str] = None,
        healthcheck_interval: Optional[int] = None,
        healthcheck_timeout: Optional[int] = None,
        healthcheck_start_period: Optional[int] = None,
        healthcheck_retries: Optional[int] = None,
        ports: Optional[Mapping[str, int]] = None,
        links: Optional[Mapping[str, str]] = None,
        mounts: Optional[Sequence[Mount]] = None,
    ) -> None:
        self.image = image
        self.stop = stop
        self.environment: Mapping[str, str] = environment or {}
        self.ports: Mapping[str, int] = ports or {}
        self.links: Mapping[str, str] = links or {}
        self.mounts: Sequence[Mount] = mounts or []

        self.healthcheck_cmd = healthcheck_cmd
        self.healthcheck_interval = healthcheck_interval
        self.healthcheck_timeout = healthcheck_timeout
        self.healthcheck_start_period = healthcheck_start_period
        self.healthcheck_retries = healthcheck_retries


def validate_port(port_line: str) -> Tuple[int, str]:
    host_port, _, container_port_proto = port_line.partition(":")
    _, _, protocol = container_port_proto.partition("/")

    if protocol.lower() not in ("tcp", "udp"):
        raise ValueError("protocol is not tcp or udp")

    return (int(host_port), container_port_proto)


def validate_link(link_line: str, container_names: Container[str]) -> Tuple[str, str]:
    other_container_name, sep, alias = link_line.partition(":")
    if sep and not alias:
        raise ValueError(f"Link '{other_container_name}:' missing alias")
    if other_container_name not in container_names:
        raise ValueError(f"Container {other_container_name!r} not defined")
    return other_container_name, alias or other_container_name


def validate_volume(volume_line: str) -> Mount:
    parts = volume_line.split(":")
    if len(parts) != 4:
        raise ValueError(f"Volume {volume_line!r} is malformed")
    if parts[0] != "bind":
        raise ValueError(f"Volume {volume_line!r} type must be 'bind:'")
    if parts[1] not in ("ro", "rw"):
        raise ValueError(f"Volume {volume_line!r} options must be 'ro' or 'rw'")

    volume_type, mode, outside, inside = parts
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
