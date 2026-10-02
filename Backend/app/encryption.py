from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        # Dev fallback only — always set FIELD_ENCRYPTION_KEY in production.
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedString(TypeDecorator):
    """Transparently AES-encrypts (Fernet) a string column at rest."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value
