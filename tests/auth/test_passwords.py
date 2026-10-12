"""Password hashing (ADR-0017, TC-0188, TC-0189)."""

from app.auth.passwords import dummy_hash, hash_password, verify_password


# TC-0188
def test_tc0188_a_hash_verifies_only_its_own_password_and_each_hash_is_salted() -> None:
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")

    assert verify_password("correct horse battery", first)
    assert not verify_password("correct horse batterY", first)
    assert first != second
    assert "correct horse" not in first


# TC-0189
def test_tc0189_a_malformed_stored_hash_never_matches() -> None:
    for stored in ("", "plain", "scrypt$1$2", "bcrypt$1$2$3$4$5", "scrypt$x$8$1$AAAA$AAAA"):
        assert not verify_password("anything", stored)


def test_the_dummy_hash_is_a_real_hash_that_matches_no_ordinary_password() -> None:
    assert dummy_hash().startswith("scrypt$")
    assert not verify_password("password", dummy_hash())
