"""
Token encryption and management.

Handles secure storage and retrieval of OAuth tokens using Fernet symmetric encryption.
Tokens are encrypted at the application layer before storing in the database.
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages encryption/decryption of OAuth tokens.

    Uses Fernet symmetric encryption with a key from environment variables.
    The same key must be used for encryption and decryption.

    Environment:
        INTEGRATION_ENCRYPTION_KEY: Base64-encoded 32-byte Fernet key
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize TokenManager.

        Args:
            encryption_key: Fernet key (base64). If not provided, reads from
                           INTEGRATION_ENCRYPTION_KEY environment variable.
        """
        key = encryption_key or os.getenv("INTEGRATION_ENCRYPTION_KEY")

        if not key:
            raise ValueError(
                "INTEGRATION_ENCRYPTION_KEY environment variable is required. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token for storage.

        Args:
            plaintext: The token to encrypt

        Returns:
            Base64-encoded encrypted token
        """
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a stored token.

        Args:
            ciphertext: The encrypted token (base64)

        Returns:
            The original plaintext token

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Use this to generate a key for INTEGRATION_ENCRYPTION_KEY.

        Returns:
            Base64-encoded 32-byte key
        """
        return Fernet.generate_key().decode()


# Singleton instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get the global TokenManager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
