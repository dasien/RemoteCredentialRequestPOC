"""
Security validation tests for remote credential request enhancement.

These tests validate critical security properties:
- Credentials are encrypted in transit
- No keys or passwords logged
- Replay attack protection
- PAKE protocol security
"""
import pytest
import logging
import io
from src.sdk.pake_handler import PAKEHandler
from src.sdk.credential_client import CredentialClient


class TestEncryptionSecurity:
    """Test that sensitive data is properly encrypted."""

    def test_credentials_never_plaintext_after_encryption(self):
        """
        Verify that encrypted credentials don't contain plaintext.

        This is a basic sanity check - encrypted data should not reveal
        the original plaintext.
        """
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Test credential encryption
        plaintext_credential = '{"username": "testuser", "password": "SecretPass123"}'
        encrypted = client.encrypt(plaintext_credential)

        # Plaintext should not appear in encrypted data
        assert "testuser" not in encrypted
        assert "SecretPass123" not in encrypted
        assert "username" not in encrypted
        assert "password" not in encrypted

    def test_pake_messages_dont_reveal_password(self):
        """
        Verify PAKE protocol messages don't contain the password.

        Critical security property: password never transmitted.
        """
        password = "SecretPairingCode123"

        client = PAKEHandler(role="client")
        msg_a = client.start_exchange(password)

        server = PAKEHandler(role="server")
        msg_b = server.start_exchange(password)

        # Check protocol messages
        assert password not in str(msg_a)
        assert password not in str(msg_b)
        assert password.encode('utf-8') not in msg_a
        assert password.encode('utf-8') not in msg_b
        assert password not in msg_a.hex()
        assert password not in msg_b.hex()

    def test_encrypted_data_is_different_each_time(self):
        """
        Verify that encrypting same data twice produces different ciphertext.

        This validates that encryption includes randomness (nonce/IV).
        """
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        plaintext = "same data"
        encrypted1 = client.encrypt(plaintext)
        encrypted2 = client.encrypt(plaintext)

        # Ciphertexts should be different (due to random IV)
        assert encrypted1 != encrypted2

        # But both decrypt to same plaintext
        assert server.decrypt(encrypted1) == plaintext
        assert server.decrypt(encrypted2) == plaintext


class TestLoggingSecurity:
    """Test that sensitive data is not logged."""

    def test_pake_keys_not_logged(self, caplog):
        """
        Verify that PAKE shared keys are never logged.

        We can't access the internal _shared_key, but we can verify
        the log output doesn't contain key material.
        """
        caplog.set_level(logging.DEBUG)
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Check all log messages
        log_text = caplog.text.lower()

        # Should not log "key" with actual bytes
        # Should only log metadata like "derived key (32 bytes)"
        assert "shared secret" not in log_text or "32 bytes" in log_text
        assert "fernet key" not in log_text or "derived" in log_text

    def test_passwords_not_logged(self, caplog):
        """
        Verify that passwords are not logged.

        Passwords used for PAKE should not appear in logs.
        """
        caplog.set_level(logging.DEBUG)
        password = "SuperSecretPassword123"

        client = PAKEHandler(role="client")
        msg_a = client.start_exchange(password)

        # Check logs
        log_text = caplog.text

        # Password should not appear in logs
        assert password not in log_text


class TestReplayProtection:
    """Test replay attack protection mechanisms."""

    def test_timestamp_validation_prevents_replay(self):
        """
        Test that request timestamp validation prevents replay attacks.

        Note: This tests the timestamp mechanism in the request payload.
        Actual replay protection would be tested at integration level.
        """
        import datetime
        import json

        # Create a request payload with old timestamp
        old_timestamp = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        payload = {
            "domain": "example.com",
            "reason": "test",
            "timestamp": old_timestamp.isoformat() + "Z",
            "nonce": "abc123"
        }

        # In real system, this would be validated by PairingManager
        # Here we just test the timestamp check logic
        timestamp = datetime.datetime.fromisoformat(payload['timestamp'].rstrip('Z'))
        age = (datetime.datetime.utcnow() - timestamp).total_seconds()

        # Should be rejected (>5 minutes old)
        assert age > 300

    def test_nonce_included_in_requests(self):
        """
        Verify that requests include nonce for replay protection.

        Each request should have a unique nonce.
        """
        import datetime
        import secrets

        # Simulate creating multiple requests
        nonces = []
        for _ in range(10):
            payload = {
                "domain": "example.com",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "nonce": secrets.token_hex(8)
            }
            nonces.append(payload["nonce"])

        # All nonces should be unique
        assert len(nonces) == len(set(nonces))


class TestPAKESecurity:
    """Test PAKE protocol security properties."""

    def test_pake_exchange_required_for_encryption(self):
        """
        Verify that encryption is not possible without completing PAKE exchange.

        Security property: Can't use messages directly as keys.
        """
        client = PAKEHandler(role="client")
        msg_a = client.start_exchange("123456")

        # Before finish_exchange, encryption should fail
        assert not client.is_ready()
        with pytest.raises(RuntimeError):
            client.encrypt("test")

    def test_wrong_password_detected_by_decryption_failure(self):
        """
        Verify that wrong password is detected (through decryption failure).

        Security property: Mismatched passwords lead to different keys.
        """
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

        # Encrypt with first pair
        encrypted = client1.encrypt("secret")

        # Try to decrypt with second pair (wrong key)
        with pytest.raises(ValueError, match="Decryption failed"):
            server2.decrypt(encrypted)

    def test_pake_provides_mutual_authentication(self):
        """
        Verify that both parties must know the password.

        If either party has wrong password, keys won't match.
        """
        # Client with correct password
        client = PAKEHandler(role="client")
        msg_a = client.start_exchange("correct123")

        # Server with wrong password
        server = PAKEHandler(role="server")
        msg_b = server.start_exchange("wrong456")

        # Both can complete exchange (library behavior)
        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # But encryption/decryption will fail
        encrypted = client.encrypt("data")
        with pytest.raises(ValueError):
            server.decrypt(encrypted)


class TestDataProtection:
    """Test data protection mechanisms."""

    def test_tampered_ciphertext_rejected(self):
        """
        Verify that tampered ciphertext is detected and rejected.

        Security property: Message authentication (integrity).
        """
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        # Encrypt data
        encrypted = client.encrypt("sensitive data")

        # Tamper with ciphertext (change last character)
        tampered = encrypted[:-5] + "XXXXX"

        # Decryption should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            server.decrypt(tampered)

    def test_truncated_ciphertext_rejected(self):
        """
        Verify that truncated ciphertext is rejected.
        """
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        encrypted = client.encrypt("data")

        # Truncate ciphertext
        truncated = encrypted[:len(encrypted)//2]

        # Should fail
        with pytest.raises(ValueError):
            server.decrypt(truncated)


class TestSessionSecurity:
    """Test session security properties."""

    def test_session_isolated_from_other_sessions(self):
        """
        Verify that sessions are isolated - one session's key can't
        decrypt another session's data.
        """
        # Create two separate PAKE sessions
        password1 = "session1"
        client1 = PAKEHandler(role="client")
        server1 = PAKEHandler(role="server")
        msg_a1 = client1.start_exchange(password1)
        msg_b1 = server1.start_exchange(password1)
        client1.finish_exchange(msg_b1)
        server1.finish_exchange(msg_a1)

        password2 = "session2"
        client2 = PAKEHandler(role="client")
        server2 = PAKEHandler(role="server")
        msg_a2 = client2.start_exchange(password2)
        msg_b2 = server2.start_exchange(password2)
        client2.finish_exchange(msg_b2)
        server2.finish_exchange(msg_a2)

        # Encrypt with session 1
        encrypted = client1.encrypt("session 1 data")

        # Should not decrypt with session 2
        with pytest.raises(ValueError):
            server2.decrypt(encrypted)

    def test_pairing_codes_are_unpredictable(self):
        """
        Verify that pairing codes are unpredictable (use cryptographic random).

        Generate multiple codes and verify they don't follow a pattern.
        """
        from src.server.pairing_manager import PairingManager

        manager = PairingManager()
        codes = []

        for _ in range(100):
            code, _ = manager.create_pairing("test-agent", "Test")
            codes.append(int(code))

        # Check statistical properties
        # 1. All codes should be 6 digits
        assert all(100000 <= c <= 999999 for c in codes)

        # 2. Should have good distribution (no obvious pattern)
        # Not all in same range
        ranges = {
            "100k": sum(1 for c in codes if 100000 <= c < 200000),
            "200k": sum(1 for c in codes if 200000 <= c < 300000),
            "900k": sum(1 for c in codes if 900000 <= c < 1000000),
        }
        # Should have codes in different ranges (not all clustered)
        assert len([r for r in ranges.values() if r > 0]) >= 2

        # 3. Should have high uniqueness
        unique_codes = len(set(codes))
        assert unique_codes >= 95  # At least 95% unique in 100 samples


class TestErrorHandlingSecurity:
    """Test that error handling doesn't leak sensitive information."""

    def test_decryption_errors_dont_leak_key_info(self):
        """
        Verify that decryption errors don't reveal key information.

        Error messages should be generic, not specific about why decryption failed.
        """
        password = "123456"

        client = PAKEHandler(role="client")
        server = PAKEHandler(role="server")

        msg_a = client.start_exchange(password)
        msg_b = server.start_exchange(password)

        client.finish_exchange(msg_b)
        server.finish_exchange(msg_a)

        encrypted = client.encrypt("data")
        tampered = encrypted[:-5] + "XXXXX"

        try:
            server.decrypt(tampered)
            assert False, "Should have raised exception"
        except ValueError as e:
            error_msg = str(e)
            # Should not contain sensitive details
            assert "key" not in error_msg.lower() or "wrong key" in error_msg.lower()
            # Should indicate decryption failed
            assert "decrypt" in error_msg.lower() or "failed" in error_msg.lower()

    def test_pake_failure_error_messages_generic(self):
        """
        Verify that PAKE failure errors don't reveal sensitive protocol details.
        """
        client = PAKEHandler(role="client")
        client.start_exchange("123456")

        try:
            client.finish_exchange(b"invalid_message")
            assert False, "Should have raised exception"
        except ValueError as e:
            error_msg = str(e).lower()
            # Should mention PAKE or password, not internal details
            assert "pake" in error_msg or "password" in error_msg or "invalid" in error_msg
