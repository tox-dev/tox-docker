from tox.venv import VirtualEnv

from tox_docker.log import LogFunc


def make_logger(venv: VirtualEnv) -> LogFunc:
    def logger(line: str) -> None:
        try:
            # tox 3.7 and later
            action = venv.new_action(line)
        except AttributeError:
            action = venv.session.newaction(venv, line)

        action.setactivity("docker", line)
        with action:
            pass

    return logger
