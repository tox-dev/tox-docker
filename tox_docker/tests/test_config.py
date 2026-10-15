"""Unit tests for tox-docker configuration parsing."""

import ntpath
import os
import posixpath

import pytest

from tox_docker import config


def _allow_both_path_styles_in_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model host absolute-path checks for parser tests on any OS."""
    posix_isabs = posixpath.isabs
    windows_isabs = ntpath.isabs

    def isabs(path: str) -> bool:
        return posix_isabs(path) or windows_isabs(path)

    monkeypatch.setattr(
        config.os.path,
        "isabs",
        isabs,
    )


def test_volume_with_windows_drive_path_preserves_drive_colon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = r"C:\work\project\data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:{source}:/var/lib/mysql").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == "/var/lib/mysql"
    assert mount["ReadOnly"] is False


@pytest.mark.skipif(os.name != "nt", reason="requires a native Windows host")
def test_native_windows_source_with_linux_target() -> None:
    source = r"C:\work\project\data"

    mount = config.Volume(f"bind:rw:{source}:/var/lib/mysql").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == "/var/lib/mysql"


def test_volume_with_windows_target_preserves_drive_colon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "/tmp/project/volume-name"
    target = r"C:\data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:{source}:{target}").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == target


@pytest.mark.parametrize("target", [r"\data", r"C:data"])
def test_volume_rejects_non_absolute_windows_target(
    target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_both_path_styles_in_test(monkeypatch)

    with pytest.raises(ValueError, match="must be an absolute path"):
        config.Volume(f"bind:rw:/tmp/project/volume-name:{target}")


def test_volume_with_windows_source_and_target_preserves_both_drive_colons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = r"C:\work\project\data"
    target = r"D:\data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:{source}:{target}").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == target


def test_volume_with_unc_source_preserves_path(monkeypatch: pytest.MonkeyPatch) -> None:
    source = r"\\server\share\project\data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:ro:{source}:/var/lib/mysql").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == "/var/lib/mysql"
    assert mount["ReadOnly"] is True


def test_volume_with_unc_target_preserves_path(monkeypatch: pytest.MonkeyPatch) -> None:
    target = r"\\server\share\data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:/tmp/project/data:{target}").docker_mount

    assert mount["Source"] == "/tmp/project/data"
    assert mount["Target"] == target


def test_volume_with_unix_source_preserves_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "/tmp/project/data"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:{source}:/var/lib/mysql").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == "/var/lib/mysql"
    assert mount["ReadOnly"] is False


def test_volume_with_named_unix_source_preserves_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "/tmp/project/volume-name"
    _allow_both_path_styles_in_test(monkeypatch)

    mount = config.Volume(f"bind:rw:{source}:/var/lib/mysql").docker_mount

    assert mount["Source"] == source
    assert mount["Target"] == "/var/lib/mysql"


def test_volume_requires_source_and_target() -> None:
    with pytest.raises(ValueError, match="malformed"):
        config.Volume("bind:rw:/tmp/project/data")


@pytest.mark.parametrize(
    ("config_line", "error"),
    [
        ("bind:rw:/tmp/source:extra:/target", "malformed"),
        ("volume:rw:/tmp/source:/target", "type must be 'bind:'"),
        ("bind:rx:/tmp/source:/target", "options must be 'ro' or 'rw'"),
        ("bind:rw:relative:/target", "must be an absolute path"),
        ("bind:rw:/tmp/source:relative", "must be an absolute path"),
    ],
)
def test_volume_rejects_invalid_config(
    config_line: str, error: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _allow_both_path_styles_in_test(monkeypatch)

    with pytest.raises(ValueError, match=error):
        config.Volume(config_line)
