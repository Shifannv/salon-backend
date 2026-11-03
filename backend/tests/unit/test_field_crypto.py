"""Bank details at rest: round trip, wrong key, wrong row, rotation, plaintext passthrough."""

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.core import field_crypto
from app.core.config import settings

SALON = "22222222-2222-4222-8222-222222222222"
NUMBER = "123456789012"


def use_key(monkeypatch, *keys):
    monkeypatch.setattr(settings, "payout_encryption_key", SecretStr(",".join(keys)) if keys else None)


def test_without_a_key_values_are_written_as_before(monkeypatch):
    use_key(monkeypatch)
    assert field_crypto.encrypt_field(NUMBER, SALON) == NUMBER
    assert not field_crypto.encryption_enabled()


def test_round_trip_hides_the_number_and_never_repeats(monkeypatch):
    use_key(monkeypatch, Fernet.generate_key().decode())
    first = field_crypto.encrypt_field(NUMBER, SALON)
    second = field_crypto.encrypt_field(NUMBER, SALON)
    assert first.startswith("enc:v1:") and NUMBER not in first and first != second
    assert field_crypto.decrypt_field(first, SALON) == NUMBER


def test_none_and_legacy_plaintext_pass_through(monkeypatch):
    use_key(monkeypatch, Fernet.generate_key().decode())
    assert field_crypto.encrypt_field(None, SALON) is None
    assert field_crypto.decrypt_field(None, SALON) is None
    assert field_crypto.decrypt_field(NUMBER, SALON) == NUMBER


def test_a_ciphertext_moved_to_another_salon_does_not_open(monkeypatch):
    use_key(monkeypatch, Fernet.generate_key().decode())
    token = field_crypto.encrypt_field(NUMBER, SALON)
    with pytest.raises(field_crypto.FieldDecryptionError):
        field_crypto.decrypt_field(token, "33333333-3333-4333-8333-333333333333")


def test_wrong_or_missing_key_fails_instead_of_returning_garbage(monkeypatch):
    use_key(monkeypatch, Fernet.generate_key().decode())
    token = field_crypto.encrypt_field(NUMBER, SALON)
    use_key(monkeypatch, Fernet.generate_key().decode())
    with pytest.raises(field_crypto.FieldDecryptionError):
        field_crypto.decrypt_field(token, SALON)
    use_key(monkeypatch)
    with pytest.raises(field_crypto.FieldDecryptionError):
        field_crypto.decrypt_field(token, SALON)


def test_rotation_new_key_encrypts_and_old_key_still_opens(monkeypatch):
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    use_key(monkeypatch, old)
    token = field_crypto.encrypt_field(NUMBER, SALON)
    use_key(monkeypatch, new, old)
    assert field_crypto.decrypt_field(token, SALON) == NUMBER
    fresh = field_crypto.encrypt_field(NUMBER, SALON)
    use_key(monkeypatch, new)
    assert field_crypto.decrypt_field(fresh, SALON) == NUMBER
