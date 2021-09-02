#!/bin/bash
set -e
set -x

tox_version=$1
docker_version=$2

# our tox.ini sets up volumes within .tox, so make sure it exists
# before trying to run tox...
mkdir -p .tox

pip install --constraint $tox_version --constraint $docker_version -r dev-requirements.txt
pip install --constraint $tox_version --constraint $docker_version .
pip show tox tox-docker docker
tox -e integration,mypy
echo "testing health check failure handling, an ERROR is expected:"
tox -e healthcheck-failing 2>&1 | egrep "tox_docker.HealthCheckFailed: .* failed health check"
