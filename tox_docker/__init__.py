import packaging.version
import tox

tox_version = packaging.version.parse(tox.__version__)
if tox_version.major == 3:
    from tox_docker.plugin_tox3 import *
elif tox_version.major == 4:
    # from tox_docker.plugin_tox4 import *
    pass
else:
    raise RuntimeError(f"tox_docker is incomptabile with tox {tox.__version__}")
