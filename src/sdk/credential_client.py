"""
Client SDK for requesting credentials from remote approval server.

This module provides the agent-side SDK for requesting credentials from a remote
approval server. It handles PAKE pairing, encrypted requests, and session management.

Workflow:
1. Agent calls pair() to initiate pairing with server
2. User enters pairing code in approval client (Terminal 2)
3. PAKE exchange completes, session established
4. Agent calls request_credential() to get credentials
5. Credentials are encrypted with PAKE-derived key during transmission
"""
from typing import Optional
import requests
import json
import time
import logging
import base64
import secrets
import datetime
from src.models.credential_response import CredentialResponse, CredentialStatus
from src.utils.credential_handler import SecureCredential
from src.sdk.pake_handler import PAKEHandler

logger = logging.getLogger(__name__)


class CredentialClient:
    """
    SDK for agents to request credentials from remote approval server.

    Handles PAKE pairing, encrypted requests, and session management.

    Example:
        client = CredentialClient("http://localhost:5000")

        # Pair with approval server (user enters code in Terminal 2)
        pairing_code = client.pair("flight-001", "Flight Agent")
        print(f"Enter this code in approval client: {pairing_code}")

        # Request credential (after pairing complete)
        response = client.request_credential(
            domain="aa.com",
            reason="Login to American Airlines",
            agent_id="flight-001",
            agent_name="Flight Agent"
        )

        if response.status == CredentialStatus.APPROVED:
            with response.credential as cred:
                # Use cred.username and cred.password
                pass
    """

    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        Initialize credential client.

        Args:
            server_url: Base URL of approval server (default: http://localhost:5000)
        """
        self.server_url = server_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.pake_handler: Optional[PAKEHandler] = None
        logger.info(f"Initialized CredentialClient for server: {self.server_url}")

    def pair(self, agent_id: str, agent_name: str, timeout: int = 60) -> str:
        """
        Initiate pairing with approval server.

        This method performs the complete PAKE pairing flow:
        1. Request pairing code from server
        2. Start PAKE exchange on client side
        3. Poll server until user enters code
        4. Complete PAKE exchange and establish session

        Returns pairing code for user to enter in approval client.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            timeout: Maximum time to wait for user to enter code (seconds)

        Returns:
            6-digit pairing code

        Raises:
            ConnectionError: If server unreachable
            TimeoutError: If user doesn't enter code within timeout
        """
        logger.info(f"Starting pairing for agent: {agent_name} ({agent_id})")

        # Step 1: Request pairing code from server
        try:
            response = requests.post(
                f"{self.server_url}/pairing/initiate",
                json={"agent_id": agent_id, "agent_name": agent_name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            pairing_code = data['pairing_code']

            logger.info(f"Pairing code generated: {pairing_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to approval server: {e}")
            raise ConnectionError(
                f"Failed to connect to approval server at {self.server_url}. "
                f"Is the approval client running? Error: {e}"
            )

        # Step 2: Start PAKE exchange on client side (SPAKE2_A)
        self.pake_handler = PAKEHandler(role="client")
        msg_out_a = self.pake_handler.start_exchange(pairing_code)
        logger.debug("Started PAKE exchange (SPAKE2_A)")

        # Step 3: Poll server until user enters code
        logger.info("Waiting for user to enter pairing code in approval client...")
        max_attempts = timeout // 2  # Poll every 2 seconds

        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    f"{self.server_url}/pairing/exchange",
                    json={
                        "pairing_code": pairing_code,
                        "pake_message": base64.b64encode(msg_out_a).decode('utf-8')
                    },
                    timeout=10
                )

                # 202 Accepted = user hasn't entered code yet
                if response.status_code == 202:
                    logger.debug(f"Waiting for user (attempt {attempt + 1}/{max_attempts})...")
                    time.sleep(2)
                    continue

                response.raise_for_status()
                data = response.json()

                # Step 4: Complete PAKE exchange
                msg_in_b = base64.b64decode(data['pake_message'])
                self.pake_handler.finish_exchange(msg_in_b)

                self.session_id = data['session_id']
                logger.info(f"Pairing successful! Session established: {self.session_id}")

                return pairing_code

            except requests.exceptions.RequestException as e:
                if attempt == max_attempts - 1:
                    logger.error("Pairing timed out - user did not enter code")
                    raise TimeoutError(
                        f"Pairing timed out after {timeout} seconds. "
                        "User did not enter the pairing code in approval client."
                    )
                logger.debug(f"Request failed (attempt {attempt + 1}), retrying: {e}")
                time.sleep(2)

        raise TimeoutError(f"Pairing timed out after {timeout} seconds")

    def request_credential(
        self,
        domain: str,
        reason: str,
        agent_id: str,
        agent_name: str
    ) -> CredentialResponse:
        """
        Request credential for domain.

        This method sends an encrypted credential request to the approval server.
        The request payload includes domain, reason, and metadata, all encrypted
        with the PAKE-derived key.

        Args:
            domain: Domain name (e.g., "aa.com")
            reason: Human-readable reason for request
            agent_id: Agent identifier
            agent_name: Agent display name

        Returns:
            CredentialResponse with status and credential (if approved)

        Raises:
            RuntimeError: If pair() not called first
        """
        if not self.session_id or not self.pake_handler:
            raise RuntimeError(
                "Must call pair() first to establish session before requesting credentials"
            )

        logger.info(f"Requesting credential for domain: {domain}")

        # Build request payload with timestamp and nonce (replay protection)
        payload = {
            "domain": domain,
            "reason": reason,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "nonce": secrets.token_hex(8)
        }

        # Encrypt payload with PAKE-derived key
        plaintext = json.dumps(payload)
        encrypted_payload = self.pake_handler.encrypt(plaintext)
        logger.debug("Encrypted credential request payload")

        # Send request to server
        try:
            response = requests.post(
                f"{self.server_url}/credential/request",
                json={
                    "session_id": self.session_id,
                    "encrypted_payload": encrypted_payload
                },
                timeout=120  # Allow time for user approval
            )
            response.raise_for_status()
            data = response.json()

            # Handle different response statuses
            if data['status'] == 'approved':
                # Decrypt credential
                encrypted_cred = data['encrypted_payload']
                decrypted = self.pake_handler.decrypt(encrypted_cred)
                cred_data = json.loads(decrypted)

                credential = SecureCredential(
                    username=cred_data['username'],
                    password=cred_data['password']
                )

                logger.info(f"Credential approved for domain: {domain}")
                return CredentialResponse(
                    status=CredentialStatus.APPROVED,
                    credential=credential,
                    error_message=None
                )

            elif data['status'] == 'denied':
                logger.warning(f"Credential request denied for domain: {domain}")
                return CredentialResponse(
                    status=CredentialStatus.DENIED,
                    credential=None,
                    error_message="User denied credential access"
                )

            else:
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"Credential request failed: {error_msg}")
                return CredentialResponse(
                    status=CredentialStatus.ERROR,
                    credential=None,
                    error_message=error_msg
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return CredentialResponse(
                status=CredentialStatus.ERROR,
                credential=None,
                error_message=f"Request failed: {e}"
            )

    def revoke_session(self) -> bool:
        """
        Revoke current session.

        Returns:
            True if session revoked successfully

        Raises:
            RuntimeError: If no active session
        """
        if not self.session_id:
            raise RuntimeError("No active session to revoke")

        try:
            response = requests.post(
                f"{self.server_url}/session/revoke",
                json={"session_id": self.session_id},
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Session revoked: {self.session_id}")
            self.session_id = None
            self.pake_handler = None
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to revoke session: {e}")
            return False

    def get_session_status(self) -> Optional[dict]:
        """
        Get current session status.

        Returns:
            Session status dict or None if no active session

        Raises:
            RuntimeError: If no active session
        """
        if not self.session_id:
            raise RuntimeError("No active session")

        try:
            response = requests.get(
                f"{self.server_url}/session/status",
                params={"session_id": self.session_id},
                timeout=10
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get session status: {e}")
            return None
