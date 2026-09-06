import base64
from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet():
    """Derives a Fernet-compatible key from the project's FIELD_ENCRYPTION_KEY."""
    key = base64.urlsafe_b64encode(settings.FIELD_ENCRYPTION_KEY.ljust(32, b'0')[:32])
    return Fernet(key)


class SecurityCryptoService:
    """Provides two-way encryption and decryption for sensitive candidate fields."""

    @classmethod
    def encrypt_data(cls, raw_text: str) -> str:
        """Encrypts plaintext using Fernet (AES-128-CBC + HMAC-SHA256)."""
        if not raw_text:
            return ""
        fernet = _get_fernet()
        return fernet.encrypt(raw_text.encode('utf-8')).decode('utf-8')

    @classmethod
    def decrypt_data(cls, cipher_text: str) -> str:
        """Decrypts Fernet-encrypted ciphertext back to plaintext."""
        if not cipher_text:
            return ""
        try:
            fernet = _get_fernet()
            return fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return "[Decryption Failed / Invalid Token]"
