from setuptools import find_packages, setup

setup(
    name="tox-docker",
    description="Launch a docker instance around test runs",
    long_description=open("README.rst").read(),
    url="https://github.com/tox-dev/tox-docker",
    maintainer="Dan Crosta",
    maintainer_email="dcrosta@late.am",
    install_requires=[
        "docker>=2.3.0,<6.0",
        "packaging",
        "tox>=3.0.0,<5.0",
    ],
    packages=find_packages(),
    entry_points={"tox": ["docker = tox_docker"]},
    vcversioner={"version_module_paths": ["_version.py"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Testing",
    ],
)
