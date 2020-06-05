#!/bin/bash
set -e
set -x

tox_version=$1
docker_version=$2

pip install --constraint $tox_version --constraint $docker_version .
pip show tox tox-docker docker
tox
echo "testing health check failure handling, an ERROR is expected:"
tox -e healthcheck-failing 2>&1 | egrep "tox_docker.HealthCheckFailed: 'alpine:3.12' failed health check"
