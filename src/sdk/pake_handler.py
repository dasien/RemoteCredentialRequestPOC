"""
PAKE protocol handler for secure key exchange.

This module encapsulates SPAKE2 protocol operations and provides encryption/decryption
using PAKE-derived keys. Supports both client (SPAKE2_A) and server (SPAKE2_B) roles.

Educational Note:
SPAKE2 (Simple Password-Authenticated Key Exchange) allows two parties sharing a weak
password (pairing code) to derive a strong shared secret without ever transmitting the
password or derived key over the network.

Security Properties:
- Passive eavesdropper learns nothing about password or shared secret
- Active MITM attacker gets exactly one password guess
- Forward secrecy: session keys are ephemeral
- Mutual authentication: both sides prove knowledge of password
"""
from typing import Optional
import base64
import logging
from spake2 import SPAKE2_A, SPAKE2_B
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class PAKEHandler:
    """
    Wrapper for SPAKE2 protocol operations and encryption.

    This class handles the SPAKE2 key exchange protocol and provides
    simple encrypt/decrypt methods using the PAKE-derived shared key.

    Supports both client (SPAKE2_A) and server (SPAKE2_B) roles.

    Example:
        # Client side
        client = PAKEHandler(role="client")
        msg_out = client.start_exchange("123456")
        # ... send msg_out to server, receive msg_in ...
        client.finish_exchange(msg_in)
        encrypted = client.encrypt("secret data")

        # Server side
        server = PAKEHandler(role="server")
        msg_out = server.start_exchange("123456")
        # ... send msg_out to client, receive msg_in ...
        server.finish_exchange(msg_in)
        decrypted = server.decrypt(encrypted)
    """

    def __init__(self, role: str):
        """
        Initialize PAKE handler.

        Args:
            role: Either "client" (SPAKE2_A) or "server" (SPAKE2_B)

        Raises:
            ValueError: If role is not "client" or "server"
        """
        if role not in ("client", "server"):
            raise ValueError(f"Role must be 'client' or 'server', got: {role}")

        self.role = role
        self._spake_instance = None
        self._shared_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        logger.debug(f"Initialized PAKEHandler with role: {role}")

    def start_exchange(self, password: str) -> bytes:
        """
        Start PAKE protocol exchange.

        This creates a SPAKE2 instance (A or B based on role) and generates
        the outbound message to send to the other party.

        CRITICAL: The password is never transmitted. Only the protocol message
        (public element) is sent.

        Args:
            password: Pairing code as string (e.g., "123456")

        Returns:
            Outbound PAKE message (to send to other party)

        Raises:
            RuntimeError: If start_exchange already called
        """
        if self._spake_instance is not None:
            raise RuntimeError("PAKE exchange already started")

        password_bytes = password.encode('utf-8')

        # Create appropriate SPAKE2 instance based on role
        if self.role == "client":
            self._spake_instance = SPAKE2_A(password_bytes)
            logger.debug("Created SPAKE2_A instance (client)")
        else:  # server
            self._spake_instance = SPAKE2_B(password_bytes)
            logger.debug("Created SPAKE2_B instance (server)")

        # Generate outbound message
        msg_out = self._spake_instance.start()
        logger.debug(f"Generated SPAKE2 outbound message ({len(msg_out)} bytes)")

        return msg_out

    def finish_exchange(self, msg_in: bytes) -> None:
        """
        Complete PAKE protocol exchange and derive shared key.

        This processes the inbound message from the other party and derives
        the shared secret. Both parties will derive identical keys if they
        used the same password.

        After this completes, encrypt() and decrypt() methods are available.

        Args:
            msg_in: Inbound PAKE message from other party

        Raises:
            RuntimeError: If start_exchange not called first
            ValueError: If exchange fails (wrong password, invalid message)
        """
        if not self._spake_instance:
            raise RuntimeError("Must call start_exchange() first")

        if self._shared_key is not None:
            raise RuntimeError("PAKE exchange already completed")

        try:
            # Complete PAKE protocol and derive shared secret
            self._shared_key = self._spake_instance.finish(msg_in)
            logger.debug(f"PAKE exchange completed, derived key ({len(self._shared_key)} bytes)")

            # Derive Fernet key from shared secret
            # SPAKE2 with Ed25519 returns 32-byte shared secret
            # Fernet requires 32-byte key, base64-urlsafe encoded
            key_bytes = self._shared_key[:32]
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)
            logger.debug("Derived Fernet encryption key from SPAKE2 shared secret")

        except Exception as e:
            logger.error(f"PAKE exchange failed: {e}")
            raise ValueError(f"PAKE exchange failed (wrong password or invalid message): {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt data using PAKE-derived key.

        Args:
            plaintext: JSON string to encrypt

        Returns:
            Base64-encoded encrypted data

        Raises:
            RuntimeError: If PAKE exchange not completed
        """
        if not self._fernet:
            raise RuntimeError("PAKE exchange not completed - call finish_exchange() first")

        plaintext_bytes = plaintext.encode('utf-8')
        encrypted = self._fernet.encrypt(plaintext_bytes)
        encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
        logger.debug(f"Encrypted {len(plaintext)} chars to {len(encrypted_b64)} chars")
        return encrypted_b64

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt data using PAKE-derived key.

        Args:
            ciphertext: Base64-encoded encrypted data

        Returns:
            Decrypted JSON string

        Raises:
            RuntimeError: If PAKE exchange not completed
            ValueError: If decryption fails (wrong key, tampered data)
        """
        if not self._fernet:
            raise RuntimeError("PAKE exchange not completed - call finish_exchange() first")

        try:
            encrypted = base64.b64decode(ciphertext)
            plaintext_bytes = self._fernet.decrypt(encrypted)
            plaintext = plaintext_bytes.decode('utf-8')
            logger.debug(f"Decrypted {len(ciphertext)} chars to {len(plaintext)} chars")
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed (wrong key or tampered data): {e}")

    def is_ready(self) -> bool:
        """
        Check if PAKE exchange completed and encryption ready.

        Returns:
            True if encrypt() and decrypt() can be called
        """
        return self._fernet is not None
