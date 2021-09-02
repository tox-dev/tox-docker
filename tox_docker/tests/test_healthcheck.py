from urllib.request import urlopen
import os

import pytest


@pytest.mark.parametrize("instance", ["HEALTHCHECK_BUILTIN", "HEALTHCHECK_CUSTOM"])
def test_the_image_is_healthy(instance: str) -> None:
    host = os.environ[f"{instance}_HOST"]
    port = os.environ[f"{instance}_8000_TCP_PORT"]
    url = f"http://{host}:{port}/healthy"

    response = urlopen(url)
    assert response.getcode() == 200, f"GET {url} => {response.getcode()}"
