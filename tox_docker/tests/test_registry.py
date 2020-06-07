from tox_docker import escape_env_var


def test_escape_env_var():
    assert (
        escape_env_var("my.private.registry/cat/image")
        == "MY_PRIVATE_REGISTRY_CAT_IMAGE"
    )
