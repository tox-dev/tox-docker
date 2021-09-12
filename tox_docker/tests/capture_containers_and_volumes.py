import sys

import docker

client = docker.from_env(version="auto")
envdir = sys.argv[1]

container_ids = [
    container.attrs["Id"].strip() for container in client.containers.list()
]
volume_ids = [volume.attrs["Name"].strip() for volume in client.volumes.list()]

with open(envdir + "/containers.list", "w") as fp:
    for container in container_ids:
        fp.write(container + "\n")
    fp.write("\n")
with open(envdir + "/volumes.list", "w") as fp:
    for volume in volume_ids:
        fp.write(volume + "\n")
    fp.write("\n")
