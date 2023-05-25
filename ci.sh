#!/bin/bash
set -e
set -x

docker_version=$1


# our tox.ini sets up volumes within .tox, so make sure it exists
# before trying to run tox...
mkdir -p .tox

pip install --constraint $docker_version -r dev-requirements.txt
pip install --constraint $docker_version .
pip show tox tox-docker docker

python tox_docker/tests/capture_containers_and_volumes.py .
tox -e integration
python tox_docker/tests/assert_containers_and_volumes_unchanged.py .

tox -e mypy

echo "testing health check failure handling, an ERROR is expected:"
tox -e healthcheck-failing 2>&1 | grep "'toxdocker/healthcheck' (from 'healthcheck-failing') failed health check"
