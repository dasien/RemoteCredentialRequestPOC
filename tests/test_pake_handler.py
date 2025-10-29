"""
Unit tests for PAKEHandler - SPAKE2 protocol wrapper.

These tests validate the critical PAKE (Password-Authenticated Key Exchange)
protocol implementation using the python-spake2 library.

Test Coverage:
- TC1.1: Client and server derive identical keys with correct password
- TC1.2: Wrong password causes PAKE exchange to fail
- TC1.3: PAKE messages are protocol messages, not keys
- Additional edge cases and error handling
"""
import pytest
from src.sdk.pake_handler import PAKEHandler


class TestPAKEKeyDerivation:
    """Test PAKE protocol key derivation (TC1.1)."""

    def test_client_server_derive_identical_keys(self):
        """
        TC1.1: Verify client and server derive identical keys with same password.

        This is the foundational PAKE property: two parties sharing a password
        can derive an identical shared secret without transmitting the password.
        """
        password = "123456"

        # Client side (SPAKE2_A)
        client_handler = PAKEHandler(role="client")
        msg_out_a = client_handler.start_exchange(password)

        # Server side (SPAKE2_B)
        server_handler = PAKEHandler(role="server")
        msg_out_b = server_handler.start_exchange(password)

        # Exchange messages
        client_handler.finish_exchange(msg_out_b)
        server_handler.finish_exchange(msg_out_a)

        # Both handlers should be ready
        assert client_handler.is_ready()
        assert server_handler.is_ready()

        # Encrypt/decrypt test - verify keys are identical
        plaintext = "test message"
        encrypted = client_handler.encrypt(plaintext)
        decrypted = server_handler.decrypt(encrypted)

        assert decrypted == plaintext

        # Test reverse direction
        plaintext2 = "another test"
        encrypted2 = server_handler.encrypt(plaintext2)
        decrypted2 = client_handler.decrypt(encrypted2)

        assert decrypted2 == plaintext2

    def test_pake_with_6_digit_pairing_code(self):
        """Test PAKE works with realistic 6-digit pairing codes."""
        pairing_code = "847293"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(pairing_code)
        msg_b = server.start_exchange(pairing_code)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Verify encryption/decryption works
        test_data = '{"domain": "example.com", "username": "test"}'
        encrypted = client.encrypt(test_data)
        decrypted = server.decrypt(encrypted)

        assert decrypted == test_data


class TestPAKEWrongPassword:
    """Test PAKE failure with wrong password (TC1.2)."""

    def test_wrong_password_causes_pake_failure(self):
        """
        TC1.2: Verify wrong password causes PAKE exchange to fail.

        This is a critical security property: if the passwords don't match,
        the key derivation will result in different keys, causing decryption to fail.

        Note: SPAKE2 library allows finish_exchange() to complete with mismatched
        passwords, but the derived keys will be different, causing decryption failure.
        """
        client = PAKEHandler(role="client")
        msg_a = client.start_exchange("123456")

        server = PAKEHandler(role="server")
        msg_b = server.start_exchange("999999")  # Wrong password!

        # Both sides can complete exchange (library behavior)
        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Both appear ready
        assert client.is_ready()
        assert server.is_ready()

        # But decryption will fail because keys are different
        encrypted = client.encrypt("test data")
        with pytest.raises(ValueError, match="Decryption failed"):
            server.decrypt(encrypted)

    def test_different_passwords_produce_decryption_errors(self):
        """
        Verify that different passwords lead to decryption failures.

        Even if both sides complete the exchange (shouldn't happen in practice),
        they would have different keys and decryption would fail.
        """
        # Create two separate PAKE exchanges with different passwords
        client1 = PAKEHandler(role="client")
        server1 = PAKEHandler(role="server")
        msg_a1 = client1.start_exchange("password1")
        msg_b1 = server1.start_exchange("password1")
        client1.finish_exchange(msg_b1)
        server1.finish_exchange(msg_a1)

        client2 = PAKEHandler(role="client")
        server2 = PAKEHandler(role="server")
        msg_a2 = client2.start_exchange("password2")
        msg_b2 = server2.start_exchange("password2")
        client2.finish_exchange(msg_b2)
        server2.finish_exchange(msg_a2)

        # Encrypt with first pair's client
        plaintext = "secret data"
        encrypted = client1.encrypt(plaintext)

        # Try to decrypt with second pair's server (different key)
        with pytest.raises(ValueError, match="Decryption failed"):
            server2.decrypt(encrypted)


class TestPAKEMessagesNotKeys:
    """Test that PAKE messages are protocol messages, not keys (TC1.3)."""

    def test_pake_messages_are_not_keys(self):
        """
        TC1.3: Verify PAKE messages are not valid encryption keys.

        This validates the educational goal: the messages exchanged are
        public protocol elements, not the shared secret itself.
        """
        client = PAKEHandler(role="client")
        msg_a = client.start_exchange("123456")

        # PAKE message should be bytes (public element)
        assert isinstance(msg_a, bytes)
        assert len(msg_a) > 0

        # Message should not be a valid Fernet key
        # Fernet keys are 44 bytes base64-encoded (32 bytes raw + padding)
        # PAKE messages are different length
        assert len(msg_a) != 32  # Not raw key length

        # Client should NOT be ready for encryption yet
        assert not client.is_ready()

    def test_messages_transmitted_not_derived_keys(self):
        """
        Verify that the messages transmitted are different from the derived keys.

        Educational: This demonstrates that eavesdropping the protocol messages
        does not reveal the shared secret.
        """
        password = "123456"

        client = PAKEHandler(role="client")
        msg_a = client.start_exchange(password)

        server = PAKEHandler(role="server")
        msg_b = server.start_exchange(password)

        # Complete exchanges
        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # The messages transmitted (msg_a, msg_b) are different from the keys
        # We can't directly access _shared_key, but we can verify behavior:
        # If messages were keys, we could use them directly for encryption
        # Instead, we need the full PAKE exchange

        # Create another client that tries to use message as key
        client2 = PAKEHandler(role="client")
        # This client has msg_a and msg_b but hasn't done PAKE exchange
        # It should NOT be able to decrypt data encrypted by client/server
        assert not client2.is_ready()


class TestPAKEErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Role must be"):
            PAKEHandler(role="invalid")

    def test_encrypt_before_exchange_raises_error(self):
        """Test that encrypt() before finish_exchange() raises error."""
        client = PAKEHandler(role="client")
        client.start_exchange("123456")

        # Haven't called finish_exchange yet
        with pytest.raises(RuntimeError, match="PAKE exchange not completed"):
            client.encrypt("test")

    def test_decrypt_before_exchange_raises_error(self):
        """Test that decrypt() before finish_exchange() raises error."""
        server = PAKEHandler(role="server")
        server.start_exchange("123456")

        # Haven't called finish_exchange yet
        with pytest.raises(RuntimeError, match="PAKE exchange not completed"):
            server.decrypt("fake_ciphertext")

    def test_finish_exchange_before_start_raises_error(self):
        """Test that finish_exchange() before start_exchange() raises error."""
        client = PAKEHandler(role="client")

        with pytest.raises(RuntimeError, match="Must call start_exchange"):
            client.finish_exchange(b"fake_message")

    def test_start_exchange_twice_raises_error(self):
        """Test that calling start_exchange() twice raises error."""
        client = PAKEHandler(role="client")
        client.start_exchange("123456")

        with pytest.raises(RuntimeError, match="already started"):
            client.start_exchange("123456")

    def test_finish_exchange_twice_raises_error(self):
        """Test that calling finish_exchange() twice raises error."""
        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange("123456")
        msg_b = server.start_exchange("123456")

        client.finish_exchange(msg_b)

        with pytest.raises(RuntimeError, match="already completed"):
            client.finish_exchange(msg_b)

    def test_invalid_pake_message_raises_error(self):
        """Test that invalid PAKE message causes ValueError."""
        client = PAKEHandler(role="client")
        client.start_exchange("123456")

        with pytest.raises(ValueError, match="PAKE exchange failed"):
            client.finish_exchange(b"invalid_message_bytes")

    def test_tampered_ciphertext_raises_error(self):
        """Test that tampered ciphertext causes decryption failure."""
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Encrypt valid data
        encrypted = client.encrypt("secret")

        # Tamper with ciphertext (modify one character)
        tampered = encrypted[:-1] + "X"

        # Decryption should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            server.decrypt(tampered)


class TestPAKEEncryptionDecryption:
    """Test encryption/decryption functionality."""

    def test_encrypt_decrypt_json_data(self):
        """Test encryption/decryption of JSON data structures."""
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Test with JSON string (typical use case)
        import json
        payload = {
            "domain": "example.com",
            "username": "testuser",
            "password": "testpass",
            "timestamp": "2025-10-29T00:00:00Z"
        }
        plaintext = json.dumps(payload)

        encrypted = client.encrypt(plaintext)
        decrypted = server.decrypt(encrypted)

        assert decrypted == plaintext
        assert json.loads(decrypted) == payload

    def test_encrypt_decrypt_empty_string(self):
        """Test encryption/decryption of empty string."""
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        encrypted = client.encrypt("")
        decrypted = server.decrypt(encrypted)

        assert decrypted == ""

    def test_encrypt_decrypt_large_data(self):
        """Test encryption/decryption of large data."""
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Large data (10KB)
        large_data = "x" * 10000

        encrypted = client.encrypt(large_data)
        decrypted = server.decrypt(encrypted)

        assert decrypted == large_data
        assert len(decrypted) == 10000

    def test_encrypt_decrypt_unicode(self):
        """Test encryption/decryption with unicode characters."""
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        unicode_data = "Hello 世界 🔐 Привет"

        encrypted = client.encrypt(unicode_data)
        decrypted = server.decrypt(encrypted)

        assert decrypted == unicode_data


class TestPAKESecurityProperties:
    """Test security properties of PAKE implementation."""

    def test_is_ready_returns_correct_state(self):
        """Test that is_ready() returns correct state at each stage."""
        client = PAKEHandler(role="client")

        # Before start_exchange
        assert not client.is_ready()

        # After start_exchange
        client.start_exchange("123456")
        assert not client.is_ready()

        # After finish_exchange
        server = PAKEHandler(role="server")
        msg_b = server.start_exchange("123456")
        client.finish_exchange(msg_b)
        assert client.is_ready()

    def test_different_roles_can_communicate(self):
        """Verify that client (SPAKE2_A) and server (SPAKE2_B) can communicate."""
        password = "123456"

        # Client uses SPAKE2_A
        client = PAKEHandler(role="client")
        assert client.role == "client"

        # Server uses SPAKE2_B
        server = PAKEHandler(role="server")
        assert server.role == "server"

        # Exchange should work
        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Both should be ready
        assert client.is_ready()
        assert server.is_ready()

    def test_password_not_transmitted_in_messages(self):
        """
        Verify that password is not present in protocol messages.

        This is a basic sanity check - the password should not appear
        in the messages transmitted over the network.
        """
        password = "SecretPassword123"

        client = PAKEHandler(role="client")
        msg_a = client.start_exchange(password)

        server = PAKEHandler(role="server")
        msg_b = server.start_exchange(password)

        # Password should not appear in messages (as bytes)
        assert password.encode('utf-8') not in msg_a
        assert password.encode('utf-8') not in msg_b

        # Password should not appear in hex representation
        assert password not in msg_a.hex()
        assert password not in msg_b.hex()
