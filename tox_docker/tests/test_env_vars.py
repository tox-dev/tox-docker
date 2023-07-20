from tox_docker.config import ContainerConfig, ExposedPort, Image
from tox_docker.plugin import escape_env_var, get_port_env_var


def test_escape_env_var() -> None:
    assert (
        escape_env_var("my.private.registry/cat/image")
        == "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    )


def test_get_port_env_var() -> None:
    config = ContainerConfig(
        name="foobar",
        image=Image("foobar"),
        dockerfile=None,
        dockerfile_target="",
        stop=True,
        expose=[
            ExposedPort("CUSTOM_ENV_VAR=1234/tcp"),
        ],
    )

    assert "CUSTOM_ENV_VAR" == get_port_env_var(config, "1234/tcp")

    # fall back to the default name if the port isn't specifically mapped
    assert "FOOBAR_5678_TCP_PORT" == get_port_env_var(config, "5678/tcp")
