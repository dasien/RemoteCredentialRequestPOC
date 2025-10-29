"""
Unit tests for PairingManager - session and pairing lifecycle management.

Tests validate:
- Pairing code generation
- Session lifecycle
- Vault unlock during pairing
- PAKE exchange coordination
"""
import pytest
import datetime
import base64
from unittest.mock import Mock, patch, MagicMock
from src.server.pairing_manager import PairingManager, PairingState, Session
from src.sdk.pake_handler import PAKEHandler


class TestPairingCreation:
    """Test pairing code generation and initialization."""

    def test_create_pairing_generates_6_digit_code(self):
        """Test that pairing codes are 6-digit numbers."""
        manager = PairingManager()
        pairing_code, expires_at = manager.create_pairing("test-agent", "Test Agent")

        # Verify code is 6 digits
        assert pairing_code.isdigit()
        assert len(pairing_code) == 6
        assert 100000 <= int(pairing_code) <= 999999

    def test_create_pairing_sets_expiration(self):
        """Test that pairing has correct expiration time (5 minutes)."""
        manager = PairingManager()
        before = datetime.datetime.utcnow()
        pairing_code, expires_at = manager.create_pairing("test-agent", "Test Agent")
        after = datetime.datetime.utcnow()

        # Expires in ~5 minutes from now
        expected_expiry = before + datetime.timedelta(minutes=5)
        assert abs((expires_at - expected_expiry).total_seconds()) < 2

    def test_create_pairing_stores_agent_info(self):
        """Test that pairing stores agent metadata."""
        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-001", "Test Agent")

        pairing = manager.pending_pairings[pairing_code]
        assert pairing.agent_id == "test-001"
        assert pairing.agent_name == "Test Agent"
        assert pairing.pairing_code == pairing_code
        assert not pairing.user_entered

    def test_create_pairing_calls_callback(self):
        """Test that callback handler is notified of new pairing."""
        manager = PairingManager()
        callback = Mock()
        manager.set_callback_handler(callback)

        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        callback.on_pairing_created.assert_called_once()
        call_args = callback.on_pairing_created.call_args[0][0]
        assert isinstance(call_args, PairingState)
        assert call_args.pairing_code == pairing_code


class TestVaultUnlock:
    """Test vault unlock during pairing phase."""

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_mark_user_entered_code_unlocks_vault(self, mock_cli_class):
        """Test that marking code as entered unlocks vault and stores token."""
        # Setup mock
        mock_cli = MagicMock()
        mock_cli.unlock.return_value = "test_session_token_12345"
        mock_cli_class.return_value = mock_cli

        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        # User enters code and password
        success = manager.mark_user_entered_code(pairing_code, "master_password")

        assert success
        mock_cli.unlock.assert_called_once_with("master_password")

        # Verify session token stored
        pairing = manager.pending_pairings[pairing_code]
        assert pairing.user_entered
        assert pairing.bitwarden_session_token == "test_session_token_12345"

    def test_mark_user_entered_code_invalid_code(self):
        """Test that invalid pairing code returns False."""
        manager = PairingManager()

        success = manager.mark_user_entered_code("999999", "password")

        assert not success

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_mark_user_entered_code_expired(self, mock_cli_class):
        """Test that expired pairing code is rejected."""
        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        # Manually expire the pairing
        pairing = manager.pending_pairings[pairing_code]
        pairing.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)

        success = manager.mark_user_entered_code(pairing_code, "password")

        assert not success
        # Expired pairing should be removed
        assert pairing_code not in manager.pending_pairings

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_mark_user_entered_code_vault_unlock_fails(self, mock_cli_class):
        """Test that vault unlock failure is handled gracefully."""
        mock_cli = MagicMock()
        mock_cli.unlock.side_effect = Exception("Incorrect master password")
        mock_cli_class.return_value = mock_cli

        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        success = manager.mark_user_entered_code(pairing_code, "wrong_password")

        assert not success


class TestPAKEExchange:
    """Test PAKE protocol message exchange."""

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_exchange_pake_message_waiting_for_user(self, mock_cli_class):
        """Test exchange returns waiting status when user hasn't entered code."""
        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        # Client sends PAKE message, but user hasn't entered code yet
        result = manager.exchange_pake_message(pairing_code, "fake_pake_message_b64")

        assert result['status'] == 'waiting'

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_exchange_pake_message_completes_exchange(self, mock_cli_class):
        """Test complete PAKE exchange and session creation."""
        # Setup vault mock
        mock_cli = MagicMock()
        mock_cli.unlock.return_value = "vault_token_123"
        mock_cli_class.return_value = mock_cli

        manager = PairingManager()
        password = "123456"

        # Create pairing
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        # User enters code (unlocks vault)
        manager.mark_user_entered_code(pairing_code, "master_password")

        # Agent starts PAKE exchange
        client = PAKEHandler(role="client")
        msg_out_a = client.start_exchange(password)
        msg_out_a_b64 = base64.b64encode(msg_out_a).decode('utf-8')

        # Server processes exchange
        result = manager.exchange_pake_message(pairing_code, msg_out_a_b64)

        assert result['status'] == 'success'
        assert 'session_id' in result
        assert result['session_id'].startswith('sess_')
        assert 'pake_message' in result
        assert result['agent_id'] == "test-agent"

        # Verify session created
        session_id = result['session_id']
        assert session_id in manager.active_sessions

        session = manager.active_sessions[session_id]
        assert session.agent_id == "test-agent"
        assert session.bitwarden_session_token == "vault_token_123"
        assert session.pake_handler.is_ready()

        # Pairing should be removed (one-time use)
        assert pairing_code not in manager.pending_pairings

    def test_exchange_pake_message_invalid_code(self):
        """Test exchange with invalid pairing code."""
        manager = PairingManager()

        result = manager.exchange_pake_message("999999", "fake_message")

        assert result['status'] == 'error'
        assert 'Invalid pairing code' in result['error']

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_exchange_pake_message_expired_code(self, mock_cli_class):
        """Test exchange with expired pairing code."""
        manager = PairingManager()
        pairing_code, _ = manager.create_pairing("test-agent", "Test Agent")

        # Expire the pairing
        pairing = manager.pending_pairings[pairing_code]
        pairing.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)

        result = manager.exchange_pake_message(pairing_code, "fake_message")

        assert result['status'] == 'error'
        assert 'expired' in result['error'].lower()


class TestSessionManagement:
    """Test session lifecycle and management."""

    def test_active_session_count(self):
        """Test session count tracking."""
        manager = PairingManager()

        assert manager.active_session_count() == 0

        # Manually create sessions for testing
        session1 = Session(
            session_id="sess_001",
            agent_id="agent-1",
            agent_name="Agent 1",
            pake_handler=Mock(),
            bitwarden_session_token="token1",
            created_at=datetime.datetime.utcnow(),
            last_access=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        )
        manager.active_sessions["sess_001"] = session1

        assert manager.active_session_count() == 1

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_revoke_session_locks_vault(self, mock_cli_class):
        """Test that revoking session locks the vault."""
        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli

        manager = PairingManager()

        # Create a session
        session = Session(
            session_id="sess_001",
            agent_id="agent-1",
            agent_name="Agent 1",
            pake_handler=Mock(),
            bitwarden_session_token="token1",
            created_at=datetime.datetime.utcnow(),
            last_access=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        )
        manager.active_sessions["sess_001"] = session

        # Revoke session
        manager.revoke_session("sess_001")

        # Verify vault locked
        mock_cli.lock.assert_called_once()

        # Session should be removed
        assert "sess_001" not in manager.active_sessions

    def test_revoke_nonexistent_session(self):
        """Test revoking nonexistent session doesn't crash."""
        manager = PairingManager()

        # Should not raise exception
        manager.revoke_session("nonexistent")

    def test_get_session_status(self):
        """Test getting session status."""
        manager = PairingManager()

        now = datetime.datetime.utcnow()
        session = Session(
            session_id="sess_001",
            agent_id="agent-1",
            agent_name="Agent 1",
            pake_handler=Mock(),
            bitwarden_session_token="token1",
            created_at=now,
            last_access=now,
            expires_at=now + datetime.timedelta(minutes=30)
        )
        manager.active_sessions["sess_001"] = session

        status = manager.get_session_status("sess_001")

        assert status is not None
        assert status['active'] is True
        assert 'last_access' in status
        assert 'expires_at' in status

    def test_get_session_status_nonexistent(self):
        """Test getting status of nonexistent session."""
        manager = PairingManager()

        status = manager.get_session_status("nonexistent")

        assert status is None


class TestCredentialRequest:
    """Test credential request handling."""

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_handle_credential_request_invalid_session(self, mock_cli_class):
        """Test credential request with invalid session."""
        manager = PairingManager()

        result = manager.handle_credential_request("nonexistent", "encrypted_payload")

        assert result['status'] == 'error'
        assert 'Invalid or expired session' in result['error']

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_handle_credential_request_expired_session(self, mock_cli_class):
        """Test credential request with expired session."""
        manager = PairingManager()

        # Create expired session
        session = Session(
            session_id="sess_001",
            agent_id="agent-1",
            agent_name="Agent 1",
            pake_handler=Mock(spec=PAKEHandler),
            bitwarden_session_token="token1",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            last_access=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        )
        manager.active_sessions["sess_001"] = session

        result = manager.handle_credential_request("sess_001", "encrypted_payload")

        assert result['status'] == 'error'
        assert 'Session expired' in result['error']
        # Expired session should be removed
        assert "sess_001" not in manager.active_sessions

    @patch('src.server.pairing_manager.BitwardenCLI')
    def test_handle_credential_request_decryption_fails(self, mock_cli_class):
        """Test credential request with invalid encrypted payload."""
        manager = PairingManager()

        # Create valid session with mock PAKE handler
        mock_pake = Mock(spec=PAKEHandler)
        mock_pake.decrypt.side_effect = ValueError("Decryption failed")

        session = Session(
            session_id="sess_001",
            agent_id="agent-1",
            agent_name="Agent 1",
            pake_handler=mock_pake,
            bitwarden_session_token="token1",
            created_at=datetime.datetime.utcnow(),
            last_access=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        )
        manager.active_sessions["sess_001"] = session

        result = manager.handle_credential_request("sess_001", "bad_encrypted_payload")

        assert result['status'] == 'error'
        assert 'Decryption failed' in result['error']
