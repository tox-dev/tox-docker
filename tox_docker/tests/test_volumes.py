import os


def test_the_image_is_healthy() -> None:
    # the healthcheck creates a file "healthy" in the volume from within
    # the container; this test proves it's visible outside the container,
    # and thus the bind mount worked as expected
    volume = os.environ["VOLUME_DIR"]
    assert "healthy" in os.listdir(volume)
