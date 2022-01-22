from packaging.version import parse, Version
import tox

tox_version = parse(tox.__version__)
assert isinstance(tox_version, Version)

if tox_version.major == 3:
    from tox_docker.tox3.plugin import *
elif tox_version.major == 4:
    from tox_docker.tox4.plugin import *
else:
    raise RuntimeError(f"tox_docker is incomptabile with tox {tox.__version__}")
