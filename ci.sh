#!/bin/bash
set -e
set -x

tox_version=$1
docker_version=$2

if [ "$tox_version" -eq "tox-4.x" ]; then
    tox=tox4
    mypy_target=mypy-tox4
else
    tox=tox
    mypy_target=mypy-tox3
fi


# our tox.ini sets up volumes within .tox, so make sure it exists
# before trying to run tox...
mkdir -p .tox

pip install --constraint $tox_version --constraint $docker_version -r dev-requirements.txt
pip install --constraint $tox_version --constraint $docker_version .
pip show tox tox-docker docker

python tox_docker/tests/capture_containers_and_volumes.py .
$tox -e integration
python tox_docker/tests/assert_containers_and_volumes_unchanged.py .

$tox -e $mypy_target

echo "testing health check failure handling, an ERROR is expected:"
$tox -e healthcheck-failing 2>&1 | egrep "tox_docker.plugin.HealthCheckFailed: .* failed health check"
