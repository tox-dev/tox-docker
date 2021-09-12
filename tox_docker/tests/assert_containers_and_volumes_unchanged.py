import sys

import docker

client = docker.from_env(version="auto")
envdir = sys.argv[1]

container_ids = set(
    [container.attrs["Id"].strip() for container in client.containers.list()]
)
volume_ids = set([volume.attrs["Name"].strip() for volume in client.volumes.list()])

with open(envdir + "/containers.list", "r") as fp:
    old_container_ids = set([line.strip() for line in fp if line.strip()])
with open(envdir + "/volumes.list", "r") as fp:
    old_volume_ids = set([line.strip() for line in fp if line.strip()])

# check if any new containers exist that didn't exist before we
# started; we can't check for identity, since the start script is
# run after tox-docker launches its containers. note also that
# this is imperfect, in case the user has started a container
# while the tests were running, but at least it'll work in CI
different = []
if container_ids - old_container_ids:
    different.append("containers")
if volume_ids - old_volume_ids:
    different.append("volumes")

if different:
    sys.exit(f"FAIL: {', '.join(different)} are different from before tox-docker ran")
