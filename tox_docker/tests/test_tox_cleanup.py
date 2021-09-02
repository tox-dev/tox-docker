from typing import Any, Dict

from tox import hookspecs
from tox.action import Action

from tox_docker import tox_cleanup, tox_runtest_post


class Container:
    def __init__(self, short_id: str, virtual_env: "VEnv") -> None:
        self.running = True
        self.short_id = short_id
        env_config = virtual_env.envconfig
        env_config._docker_containers[short_id] = self
        env_config.config._docker_container_configs[short_id] = {"stop": True}

    # noinspection PyUnusedLocal
    def remove(self, v: bool = False, force: bool = False) -> None:
        if not self.running:
            raise ValueError("Container is not running")
        self.running = False


class Config:
    def __init__(self) -> None:
        self._docker_container_configs: Dict[str, Any] = {}


class EnvConfig:
    def __init__(self, config: Config) -> None:
        self._docker_containers: Dict[str, Container] = {}
        self.docker = True
        self.config = config


class VEnv:
    def __init__(self, config: Config) -> None:
        self.envconfig = EnvConfig(config)

    @classmethod
    def new_action(cls, message: str) -> Action:
        return Action(
            "docker", message, [], ".", False, False, None, None, 100, 100, 100
        )


class Session:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.existing_venvs: Dict[str, VEnv] = {}


def test_tox_emergency_cleanup() -> None:
    """check if the container is stopped even if tox_runtest_post has not been called"""
    config = Config()
    session = Session(config)
    virtual_env = VEnv(config)
    session.existing_venvs["test_venv"] = virtual_env
    container = Container("test_container", virtual_env)
    assert container.running
    tox_cleanup(session)
    if hasattr(hookspecs, "tox_cleanup"):
        assert not container.running
    else:
        assert container.running


def test_tox_normal_cleanup() -> None:
    """normal situation: tox_runtest_post has been called before tox_cleanup"""
    config = Config()
    session = Session(config)
    virtual_env = VEnv(config)
    session.existing_venvs["test_venv"] = virtual_env
    container = Container("test_container", virtual_env)
    assert container.running
    tox_runtest_post(virtual_env)
    assert not container.running
    tox_cleanup(session)
    assert not container.running
