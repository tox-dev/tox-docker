import os

import docker


client = docker.from_env(version="auto")
envdir = os.environ["TOX_ENV_DIR"]

container_ids = [
    container.attrs["Id"]
    for container in client.containers.list()
]
volume_ids = [
    volume.attrs["Name"]
    for volume in client.volumes.list()
]

with open(envdir + "/containers.list", "w") as fp:
    fp.writelines(container_ids)
    fp.write("\n")
with open(envdir + "/volumes.list", "w") as fp:
    fp.writelines(volume_ids)
    fp.write("\n")
