"""Encryption utilities for sensitive data."""
import json
from functools import lru_cache
from cryptography.fernet import Fernet
from config import get_settings


@lru_cache
def get_fernet() -> Fernet:
    """Get Fernet instance using encryption key from settings."""
    settings = get_settings()
    return Fernet(settings.encryption_key)


def encrypt_string(value: str | None) -> str | None:
    """Encrypt a string value."""
    if not value:
        return None
    fernet = get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_string(encrypted_value: str | None) -> str | None:
    """Decrypt a string value."""
    if not encrypted_value:
        return None
    fernet = get_fernet()
    return fernet.decrypt(encrypted_value.encode()).decode()


def encrypt_json(data: list | dict | None) -> str:
    """Encrypt JSON-serializable data."""
    json_str = json.dumps(data or [])
    fernet = get_fernet()
    return fernet.encrypt(json_str.encode()).decode()


def decrypt_json(encrypted_value: str | None) -> list | dict:
    """Decrypt JSON data."""
    if not encrypted_value:
        return []
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode()).decode()
    return json.loads(decrypted)
