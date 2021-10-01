from logging import getLogger


def log(line: str) -> None:
    getLogger().warning(f"docker> {line}")
