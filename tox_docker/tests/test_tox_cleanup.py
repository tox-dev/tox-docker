from tox.action import Action
from tox import hookspecs

from tox_docker import tox_cleanup, tox_runtest_post


class Session:
    def __init__(self, config):
        self.config = config
        self.existing_venvs = {}


class Config:
    def __init__(self):
        self._docker_container_configs = {}


class Container:
    def __init__(self, short_id, virtual_env):
        self.running = True
        self.short_id = short_id
        env_config = virtual_env.envconfig
        env_config._docker_containers[short_id] = self
        env_config.config._docker_container_configs[short_id] = {"stop": True}

    # noinspection PyUnusedLocal
    def remove(self, v=False, force=False):
        if not self.running:
            raise ValueError("Container is not running")
        self.running = False


class EnvConfig:
    def __init__(self, config):
        self._docker_containers = {}
        self.docker = True
        self.config = config


class VEnv:
    def __init__(self, config):
        self.envconfig = EnvConfig(config)

    @classmethod
    def new_action(cls, message):
        return Action(
            "docker", message, [], ".", False, False, None, None, 100, 100, 100
        )


def test_tox_emergency_cleanup():
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


def test_tox_normal_cleanup():
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
