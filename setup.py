from setuptools import find_packages, setup

setup(
    name="tox-docker",
    description="Manage lifecycle of docker containers during Tox test runs",
    long_description=open("README.rst").read(),
    url="https://github.com/tox-dev/tox-docker",
    maintainer="Dan Crosta",
    maintainer_email="dcrosta@late.am",
    install_requires=[
        "docker>=4.0,<8.0",
        "tox>=4.0.0,<5.0",
    ],
    packages=find_packages(),
    entry_points={"tox": ["docker = tox_docker"]},
    vcversioner={"version_module_paths": ["_version.py"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
    ],
)
