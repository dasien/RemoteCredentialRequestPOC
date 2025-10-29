"""
Pairing and session management for approval server.

This module manages the lifecycle of pairing requests and active sessions,
including PAKE protocol exchange, vault unlock, and credential retrieval.

CRITICAL DESIGN NOTE - Vault Unlock Timing:
- Vault is unlocked ONCE during pairing when user enters pairing code + master password
- Master password is used immediately to get session token, then discarded
- Session token is stored with the session (NOT the password)
- Credential requests use the stored session token (no password prompt)
- Session token never leaves this process (stays in Terminal 2)
"""
import secrets
import datetime
import logging
import json
import base64
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from src.sdk.pake_handler import PAKEHandler

logger = logging.getLogger(__name__)


@dataclass
class PairingState:
    """
    State of a pending pairing.

    This represents a pairing that has been initiated but not yet completed.
    It transitions to a Session once the PAKE exchange completes.
    """
    agent_id: str
    agent_name: str
    pairing_code: str
    created_at: datetime.datetime
    expires_at: datetime.datetime
    agent_pake_message: Optional[bytes] = None  # SPAKE2_A message from agent
    user_entered: bool = False
    bitwarden_session_token: Optional[str] = None  # Token from bw unlock


@dataclass
class Session:
    """
    Active session with PAKE-derived key AND vault access.

    CRITICAL: This session includes both the PAKE encryption key (for secure
    communication) and the Bitwarden session token (for vault access).

    The master password is NEVER stored. Only the session token is kept.
    """
    session_id: str
    agent_id: str
    agent_name: str
    pake_handler: PAKEHandler
    bitwarden_session_token: str  # Token from bw unlock (NOT master password)
    created_at: datetime.datetime
    last_access: datetime.datetime
    expires_at: datetime.datetime


class PairingManager:
    """
    Manage pairing lifecycle and sessions.

    This class handles:
    - Creating pairing codes
    - PAKE message exchange
    - Vault unlock during pairing
    - Session management
    - Credential retrieval using stored vault tokens

    Stores:
    - Pending pairings (waiting for user to enter code)
    - Active sessions (PAKE exchange complete, vault unlocked)
    """

    def __init__(self):
        """Initialize pairing manager."""
        self.pending_pairings: Dict[str, PairingState] = {}
        self.active_sessions: Dict[str, Session] = {}
        self._callback_handler = None  # For UI notifications
        logger.info("PairingManager initialized")

    def set_callback_handler(self, handler):
        """
        Set callback handler for UI notifications.

        The callback handler is used to notify the UI of events like new pairing
        requests and credential approval prompts.

        Args:
            handler: Object with methods: on_pairing_created(), handle_credential_request()
        """
        self._callback_handler = handler
        logger.debug("Callback handler registered")

    def create_pairing(self, agent_id: str, agent_name: str) -> Tuple[str, datetime.datetime]:
        """
        Create new pairing.

        Generates a 6-digit pairing code and stores pending pairing state.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name

        Returns:
            (pairing_code, expires_at)
        """
        # Generate 6-digit pairing code (100000-999999)
        pairing_code = str(secrets.randbelow(900000) + 100000)

        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(minutes=5)

        pairing_state = PairingState(
            agent_id=agent_id,
            agent_name=agent_name,
            pairing_code=pairing_code,
            created_at=now,
            expires_at=expires_at
        )

        self.pending_pairings[pairing_code] = pairing_state
        logger.info(f"Pairing created: {pairing_code} for {agent_name} ({agent_id}), expires {expires_at}")

        # Notify UI (if callback registered)
        if self._callback_handler:
            self._callback_handler.on_pairing_created(pairing_state)

        return pairing_code, expires_at

    def mark_user_entered_code(self, pairing_code: str, master_password: str) -> bool:
        """
        Mark that user entered pairing code AND unlock vault for session.

        CRITICAL: This is where the user enters their master password ONCE.
        The vault is unlocked here and the session token is stored for the
        entire session duration. User will NOT be prompted again for password
        during credential requests.

        Flow:
        1. User enters pairing code + master password in approval client
        2. Vault is unlocked using master password
        3. Session token is obtained and stored
        4. Master password is discarded (never stored)
        5. Future credential requests use the session token

        Args:
            pairing_code: 6-digit pairing code
            master_password: Bitwarden master password (used once to unlock vault)

        Returns:
            True if pairing found, valid, and vault unlocked successfully
        """
        pairing = self.pending_pairings.get(pairing_code)

        if not pairing:
            logger.warning(f"Invalid pairing code: {pairing_code}")
            return False

        if datetime.datetime.utcnow() > pairing.expires_at:
            logger.warning(f"Expired pairing code: {pairing_code}")
            del self.pending_pairings[pairing_code]
            return False

        # Unlock vault with master password
        try:
            from src.utils.bitwarden_cli import BitwardenCLI
            cli = BitwardenCLI()
            session_token = cli.unlock(master_password)

            # Store session token with pairing (NOT the password!)
            pairing.bitwarden_session_token = session_token
            pairing.user_entered = True

            logger.info(f"Vault unlocked for pairing: {pairing_code}")
            logger.debug("Master password discarded, session token stored")
            return True

        except Exception as e:
            logger.error(f"Failed to unlock vault: {e}")
            return False

    def exchange_pake_message(self, pairing_code: str, msg_in_a: str) -> Dict:
        """
        Handle PAKE message exchange.

        This completes the PAKE protocol exchange and creates an active session
        if the user has already entered the pairing code.

        Flow:
        1. Agent sends SPAKE2_A message
        2. If user hasn't entered code yet, return 'waiting'
        3. If user entered code, complete PAKE exchange (SPAKE2_B)
        4. Create session with PAKE key + vault token
        5. Return session_id and SPAKE2_B message

        Args:
            pairing_code: 6-digit code
            msg_in_a: Base64-encoded SPAKE2_A message from agent

        Returns:
            Dict with status and data:
            - {"status": "waiting"} if user hasn't entered code
            - {"status": "success", "session_id": "...", "pake_message": "...", "agent_id": "..."}
            - {"status": "error", "error": "..."}
        """
        pairing = self.pending_pairings.get(pairing_code)

        if not pairing:
            logger.warning(f"PAKE exchange failed: Invalid pairing code {pairing_code}")
            return {"status": "error", "error": "Invalid pairing code"}

        if datetime.datetime.utcnow() > pairing.expires_at:
            logger.warning(f"PAKE exchange failed: Expired pairing code {pairing_code}")
            del self.pending_pairings[pairing_code]
            return {"status": "error", "error": "Pairing code expired"}

        # Store agent's PAKE message
        pairing.agent_pake_message = base64.b64decode(msg_in_a)
        logger.debug(f"Stored SPAKE2_A message for pairing {pairing_code}")

        # Check if user has entered code yet
        if not pairing.user_entered:
            logger.debug(f"User hasn't entered pairing code {pairing_code} yet, returning waiting status")
            return {"status": "waiting"}

        # User has entered code and vault is unlocked - complete PAKE exchange
        logger.info(f"Completing PAKE exchange for pairing {pairing_code}")

        pake_handler = PAKEHandler(role="server")
        msg_out_b = pake_handler.start_exchange(pairing_code)

        try:
            pake_handler.finish_exchange(pairing.agent_pake_message)
            logger.debug("PAKE exchange completed successfully (SPAKE2_B)")
        except ValueError as e:
            logger.error(f"PAKE exchange failed: {e}")
            return {"status": "error", "error": "PAKE exchange failed"}

        # Create session with PAKE key AND vault access
        session_id = f"sess_{secrets.token_hex(16)}"
        now = datetime.datetime.utcnow()

        session = Session(
            session_id=session_id,
            agent_id=pairing.agent_id,
            agent_name=pairing.agent_name,
            pake_handler=pake_handler,
            bitwarden_session_token=pairing.bitwarden_session_token,  # Transfer from pairing
            created_at=now,
            last_access=now,
            expires_at=now + datetime.timedelta(minutes=30)
        )

        self.active_sessions[session_id] = session

        # Remove pairing (one-time use)
        del self.pending_pairings[pairing_code]

        logger.info(f"Session established: {session_id} for {pairing.agent_name}, expires {session.expires_at}")

        return {
            "status": "success",
            "session_id": session_id,
            "pake_message": base64.b64encode(msg_out_b).decode('utf-8'),
            "agent_id": pairing.agent_id
        }

    def handle_credential_request(self, session_id: str, encrypted_payload: str) -> Dict:
        """
        Handle credential request (prompt user, retrieve from vault).

        FLOW:
        1. Validate session and decrypt request
        2. Prompt user for approval (via callback handler)
        3. If approved, retrieve credential from vault using stored session token
        4. Encrypt credential and return

        CRITICAL: Vault access uses session.bitwarden_session_token (stored during
        pairing). No password prompt needed here.

        Args:
            session_id: Session identifier
            encrypted_payload: Base64-encoded encrypted request

        Returns:
            Dict with status and encrypted credential or error:
            - {"status": "approved", "encrypted_payload": "..."}
            - {"status": "denied", "error": "..."}
            - {"status": "error", "error": "..."}
        """
        session = self.active_sessions.get(session_id)

        if not session:
            logger.warning(f"Invalid or expired session: {session_id}")
            return {"status": "error", "error": "Invalid or expired session"}

        # Update last access
        session.last_access = datetime.datetime.utcnow()

        # Check timeout
        if datetime.datetime.utcnow() > session.expires_at:
            logger.warning(f"Session expired: {session_id}")
            del self.active_sessions[session_id]
            return {"status": "error", "error": "Session expired"}

        # Decrypt request
        try:
            plaintext = session.pake_handler.decrypt(encrypted_payload)
            request_data = json.loads(plaintext)
            logger.debug(f"Decrypted credential request for domain: {request_data.get('domain')}")
        except Exception as e:
            logger.error(f"Failed to decrypt request: {e}")
            return {"status": "error", "error": "Decryption failed"}

        # Validate timestamp (prevent replay attacks)
        timestamp = datetime.datetime.fromisoformat(request_data['timestamp'].rstrip('Z'))
        age = (datetime.datetime.utcnow() - timestamp).total_seconds()
        if age > 300:  # 5 minutes
            logger.warning(f"Request too old: {age} seconds")
            return {"status": "error", "error": "Request too old (possible replay attack)"}

        # Prompt user for approval (callback returns approval decision)
        if self._callback_handler:
            result = self._callback_handler.handle_credential_request(
                session=session,
                domain=request_data['domain'],
                reason=request_data['reason']
            )

            if result['approved']:
                # Retrieve credential using stored vault token (no unlock needed!)
                logger.info(f"User approved credential request for: {request_data['domain']}")
                try:
                    from src.utils.bitwarden_cli import BitwardenCLI
                    cli = BitwardenCLI()

                    # Use stored session token (NOT password!)
                    items = cli.list_items(
                        request_data['domain'],
                        session.bitwarden_session_token
                    )

                    # Find login item
                    login_item = next(
                        (item for item in items if item.get("type") == 1),
                        None
                    )

                    if not login_item:
                        logger.warning(f"No credential found for: {request_data['domain']}")
                        return {
                            "status": "error",
                            "error": f"No credential found for {request_data['domain']}"
                        }

                    # Extract credentials
                    username = login_item.get("login", {}).get("username")
                    password = login_item.get("login", {}).get("password")

                    if not username or not password:
                        logger.error(f"Incomplete credential for: {request_data['domain']}")
                        return {
                            "status": "error",
                            "error": "Incomplete credential (missing username or password)"
                        }

                    # Encrypt and return credential
                    cred_payload = {
                        "username": username,
                        "password": password,
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                        "nonce": secrets.token_hex(8)
                    }

                    encrypted_cred = session.pake_handler.encrypt(json.dumps(cred_payload))
                    logger.info(f"Credential retrieved and encrypted for: {request_data['domain']}")

                    return {
                        "status": "approved",
                        "encrypted_payload": encrypted_cred
                    }

                except Exception as e:
                    logger.error(f"Failed to retrieve credential: {e}")
                    return {
                        "status": "error",
                        "error": f"Vault access failed: {e}"
                    }
            else:
                logger.info(f"User denied credential request for: {request_data['domain']}")
                return {
                    "status": "denied",
                    "error": result.get('error', 'User denied')
                }
        else:
            logger.error("No approval handler registered")
            return {"status": "error", "error": "No approval handler registered"}

    def revoke_session(self, session_id: str):
        """
        Revoke session and lock vault.

        Args:
            session_id: Session to revoke
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]

            # Lock vault when revoking session
            try:
                from src.utils.bitwarden_cli import BitwardenCLI
                cli = BitwardenCLI()
                cli.lock()
                logger.info(f"Vault locked for session: {session_id}")
            except Exception as e:
                logger.warning(f"Failed to lock vault: {e}")

            del self.active_sessions[session_id]
            logger.info(f"Session revoked: {session_id}")

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """
        Get session status.

        Args:
            session_id: Session identifier

        Returns:
            Status dict or None if session not found
        """
        session = self.active_sessions.get(session_id)

        if not session:
            return None

        return {
            "active": True,
            "agent_name": session.agent_name,
            "last_access": session.last_access.isoformat() + "Z",
            "expires_at": session.expires_at.isoformat() + "Z"
        }

    def active_session_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            Number of active sessions
        """
        return len(self.active_sessions)

    def cleanup_expired(self):
        """Clean up expired pairings and sessions."""
        now = datetime.datetime.utcnow()

        # Cleanup expired pairings
        expired_pairings = [
            code for code, pairing in self.pending_pairings.items()
            if now > pairing.expires_at
        ]
        for code in expired_pairings:
            del self.pending_pairings[code]
            logger.debug(f"Cleaned up expired pairing: {code}")

        # Cleanup expired sessions
        expired_sessions = [
            sid for sid, session in self.active_sessions.items()
            if now > session.expires_at
        ]
        for sid in expired_sessions:
            self.revoke_session(sid)
            logger.debug(f"Cleaned up expired session: {sid}")
