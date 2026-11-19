"""
Encryption service for file encryption at rest.
"""

import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet

from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting files."""

    def __init__(self):
        # Derive key from settings
        key = settings.ENCRYPTION_KEY.encode()
        # Create a 32-byte key for Fernet
        key_hash = hashlib.sha256(key).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key_hash))

    def encrypt_bytes(self, content: bytes) -> bytes:
        return self.cipher.encrypt(content)

    def decrypt_bytes(self, content: bytes) -> bytes:
        return self.cipher.decrypt(content)

    async def encrypt_file(self, file_path: str) -> str:
        """Encrypt a file and return path to encrypted file."""
        path = Path(file_path)
        encrypted_path = path.with_suffix(path.suffix + ".encrypted")

        # Read, encrypt, write
        content = path.read_bytes()
        encrypted_content = self.cipher.encrypt(content)
        encrypted_path.write_bytes(encrypted_content)

        # Optionally delete original
        # path.unlink()

        return str(encrypted_path)

    async def decrypt_file(self, encrypted_path: str) -> bytes:
        """Decrypt a file and return content."""
        path = Path(encrypted_path)
        encrypted_content = path.read_bytes()
        decrypted_content = self.cipher.decrypt(encrypted_content)
        return decrypted_content
