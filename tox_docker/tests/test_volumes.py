import os
import tempfile

from tox_docker.config import Volume


def test_the_image_is_healthy() -> None:
    # the healthcheck creates a file "healthy" in the volume from within
    # the container; this test proves it's visible outside the container,
    # and thus the bind mount worked as expected
    volume = os.environ["VOLUME_DIR"]
    assert "healthy" in os.listdir(volume)


def test_volume_creation() -> None:
    with tempfile.NamedTemporaryFile() as f:
        source = f"{f.name}/test"
        assert not os.path.exists(source)
        volume = Volume(f"bind:ro:{source}:/tmp/test")
        assert volume.docker_mount.source == source
        assert volume.docker_mount.target == "/tmp/test"
        assert volume.docker_mount.type == "bind"
        assert volume.docker_mount.readonly is True
        assert os.path.isfile(source)
