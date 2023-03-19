from tox_docker.config import User


def test_username_parsing() -> None:
    u = User("testuser")
    assert u.username == "testuser"
    assert u.uid == None


def test_uid_parsing() -> None:
    u = User("1234")
    assert u.username == "1234"
    assert u.uid == 1234
