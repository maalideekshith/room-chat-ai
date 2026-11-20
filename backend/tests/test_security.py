from app.core.security import hash_password, verify_password


def test_hash_uses_argon2id() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")


def test_verify_correct_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash) is True


def test_verify_incorrect_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong password", password_hash) is False


def test_verify_invalid_hash_returns_false() -> None:
    assert verify_password("password", "not-a-valid-hash") is False
