"""
A plugin for tox_ which runs one or more Docker_ containers during the test
run.

See full documentation in the README_.

.. _tox: https://tox.readthedocs.io/en/latest/
.. _Docker: https://www.docker.com/
.. _README: https://github.com/tox-dev/tox-docker/blob/master/README.md
"""
from setuptools import setup


setup(
    name="tox-docker",
    description="Launch a docker instance around test runs",
    long_description=__doc__,
    url="https://github.com/tox-dev/tox-docker",
    maintainer="Dan Crosta",
    maintainer_email="dcrosta@late.am",
    install_requires=[
        "docker>=2.3.0,<4.0",
        "tox>=2.7.0,<4.0",
    ],
    py_modules=["tox_docker"],
    entry_points={"tox": ["docker = tox_docker"]},
    setup_requires=["vcversioner"],
    vcversioner={"version_module_paths" : ["_version.py"]},
)
