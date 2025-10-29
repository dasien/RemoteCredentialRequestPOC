---
enhancement: remote-credential-request
agent: architect
task_id: task_1761747164_46752
timestamp: 2025-10-29T00:00:00Z
status: READY_FOR_IMPLEMENTATION
---

# Implementation Plan: Remote Credential Access with PAKE

## Executive Summary

This document provides comprehensive technical architecture and implementation guidance for extending the existing credential-request POC to support remote/distributed architecture with actual PAKE (Password-Authenticated Key Exchange) protocol implementation.

**Project Context:** Educational project focused on learning PAKE protocols through proper implementation. Quality and correctness are prioritized over speed.

**Architecture Decisions Made:**
- ✅ PAKE Library: **python-spake2** (simple, pure Python, excellent for learning)
- ✅ HTTP Framework: **Flask** (synchronous, simple, sufficient for POC)
- ✅ Session Storage: **In-memory** (simplifies MVP, no persistence required)
- ✅ Transport: **HTTP with short polling** (2-second intervals, WebSocket deferred to post-MVP)
- ✅ Pairing Code: **6-digit numeric** (100000-999999, user-friendly)
- ✅ Error Recovery: **3 retries with exponential backoff** for transient errors

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [PAKE Protocol Integration](#pake-protocol-integration)
4. [Component Design](#component-design)
5. [API Specification](#api-specification)
6. [Message Format Specification](#message-format-specification)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Session Management](#session-management)
9. [Testing Strategy](#testing-strategy)
10. [Implementation Phases](#implementation-phases)
11. [File Structure](#file-structure)
12. [Acceptance Criteria](#acceptance-criteria)

---

## System Architecture

### High-Level Architecture

The system operates in two modes:

**Local Mode (Existing):** Direct in-process communication
```
┌─────────────────┐
│ FlightAgent     │
└────────┬────────┘
         │ (direct call)
┌────────▼────────┐
│ BitwardenAgent  │
└────────┬────────┘
         │ (subprocess)
┌────────▼────────┐
│ BitwardenCLI    │
└─────────────────┘
```

**Remote Mode (New):** Two-process architecture with PAKE-secured communication
```
Terminal 1: Agent Process              Terminal 2: Approval Server Process
┌─────────────────────┐               ┌──────────────────────┐
│   FlightAgent       │               │   ApprovalClient     │
│   (Playwright)      │               │   (Terminal UI)      │
└──────────┬──────────┘               └──────────┬───────────┘
           │                                     │
┌──────────▼──────────┐               ┌─────────▼────────────┐
│  CredentialClient   │◄────HTTP─────►│  ApprovalServer      │
│  (SDK)              │   (localhost)  │  (Flask)             │
│  - SPAKE2_A         │               │  - SPAKE2_B          │
└──────────┬──────────┘               └─────────┬────────────┘
           │                                     │
┌──────────▼──────────┐               ┌─────────▼────────────┐
│   PAKEHandler       │               │  PairingManager      │
│   - Key derivation  │               │  - Session storage   │
│   - Encryption      │               │  - Key derivation    │
└─────────────────────┘               └─────────┬────────────┘
                                                 │
                                        ┌────────▼─────────────┐
                                        │  BitwardenCLI        │
                                        │  (vault access)      │
                                        └──────────────────────┘
```

### Architecture Principles

1. **PAKE First:** Design around PAKE protocol requirements
2. **Code Isolation:** Remote mode code separate from local mode (no modifications to existing code)
3. **Reuse Existing:** Maximize reuse of BitwardenCLI, SecureCredential, AuditLogger
4. **Educational Value:** Code structure teaches PAKE concepts
5. **Test-Driven:** Design with testing in mind (especially two-process testing)
6. **Clear Errors:** Every error suggests corrective action

---

## Technology Stack

### Selected Technologies

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **PAKE Protocol** | python-spake2 | >= 0.9 | Pure Python, simple API, excellent for learning PAKE concepts |
| **HTTP Server** | Flask | >= 3.0.0 | Synchronous model, simple setup, sufficient for POC |
| **Encryption** | cryptography (Fernet) | >= 41.0.0 | Already in use, symmetric encryption with PAKE-derived keys |
| **Terminal UI** | Rich | >= 13.7.0 | Already in use, consistent UI experience |
| **Testing** | pytest | >= 7.4.0 | Standard Python testing framework |

### New Dependencies

Add to `requirements.txt`:
```
spake2>=0.9
Flask>=3.0.0
pytest>=7.4.0
```

### Technology Selection Rationale

#### Why python-spake2?

**Advantages:**
- Pure Python implementation (easier to understand and debug)
- Simple, clean API with separate client/server classes (SPAKE2_A, SPAKE2_B)
- Excellent educational value - code is readable and demonstrates PAKE concepts
- Based on Ed25519 elliptic curve (128-bit security, fast, small messages)
- Active maintenance and well-documented
- Security guarantee: passive attacker learns nothing, active attacker gets exactly one password guess

**Alternatives Considered:**
- **pysrp:** More complex API, older protocol (though mature and proven)
- **opaque-cloudflare:** More complex, asymmetric PAKE (too advanced for initial learning)

**Decision:** python-spake2 provides the best balance of simplicity and educational value.

#### Why Flask?

**Advantages:**
- Extremely simple setup (minimal boilerplate)
- Synchronous model easier to reason about for POC
- No async complexity for localhost-only communication
- Built-in development server (no need for uvicorn/gunicorn)
- Smaller learning curve for team

**Alternatives Considered:**
- **FastAPI:** More modern, better performance, but adds async complexity unnecessary for localhost POC

**Decision:** Flask's simplicity aligns with educational POC goals.

---

## PAKE Protocol Integration

### SPAKE2 Protocol Overview

SPAKE2 (Simple Password-Authenticated Key Exchange) allows two parties sharing a weak password (pairing code) to derive a strong shared secret without ever transmitting the password or derived key.

**Security Properties:**
- Passive eavesdropper learns nothing about password or shared secret
- Active MITM attacker gets exactly one password guess
- Forward secrecy: session keys are ephemeral
- Mutual authentication: both sides prove knowledge of password

### SPAKE2 Protocol Flow

```
Agent (SPAKE2_A)                    Server (SPAKE2_B)
     │                                    │
     │ 1. Both sides initialize with     │
     │    pairing code as password       │
     │                                    │
     │ 2. Agent generates SPAKE2_A       │
     │    message (public element)       │
     ├──────── msg_out_a ─────────────►  │
     │                                    │
     │                                    │ 3. Server generates SPAKE2_B
     │                                    │    message (public element)
     │  ◄─────── msg_out_b ──────────────┤
     │                                    │
     │ 4. Agent processes msg_in_b       │
     │    and derives shared key         │
     │                                    │ 5. Server processes msg_in_a
     │                                    │    and derives shared key
     │                                    │
     ▼                                    ▼
[Shared Key A]  <──── MATCH ────►  [Shared Key B]
```

**Critical:** At no point is the pairing code or derived key transmitted over the network. Only protocol messages (public elements) are exchanged.

### SPAKE2 Implementation Details

#### Client-Side (Agent)

```python
from spake2 import SPAKE2_A

# Initialize with pairing code as password
pairing_code = "847293"
spake_a = SPAKE2_A(pairing_code.encode('utf-8'))

# Generate outbound message
msg_out_a = spake_a.start()

# Send msg_out_a to server, receive msg_in_b
# ... HTTP request/response ...

# Process inbound message and derive key
shared_key = spake_a.finish(msg_in_b)
# shared_key is now a bytes object (e.g., 32 bytes)
```

#### Server-Side (Approval Server)

```python
from spake2 import SPAKE2_B

# Initialize with pairing code as password (user entered)
pairing_code = "847293"  # User typed this
spake_b = SPAKE2_B(pairing_code.encode('utf-8'))

# Generate outbound message
msg_out_b = spake_b.start()

# Receive msg_in_a from agent
# ... HTTP request ...

# Process inbound message and derive key
shared_key = spake_b.finish(msg_in_a)
# shared_key is now identical to agent's shared_key
```

### Key Derivation for Encryption

SPAKE2 returns a shared secret (bytes). We need to convert this to a Fernet-compatible key:

```python
import base64
from cryptography.fernet import Fernet

def derive_fernet_key(spake2_shared_key: bytes) -> bytes:
    """
    Convert SPAKE2 shared key to Fernet-compatible key.

    Fernet requires a 32-byte key, base64-urlsafe encoded.
    SPAKE2 with Ed25519 returns a 32-byte shared secret.

    Args:
        spake2_shared_key: Raw bytes from spake2.finish()

    Returns:
        Fernet-compatible key (base64-urlsafe encoded)
    """
    # Take first 32 bytes (SPAKE2 Ed25519 returns 32 bytes)
    key_bytes = spake2_shared_key[:32]

    # Encode as base64-urlsafe for Fernet
    fernet_key = base64.urlsafe_b64encode(key_bytes)

    return fernet_key
```

### PAKE Message Exchange API Flow

**1. Agent initiates pairing:**
```
POST /pairing/initiate
Request: {"agent_id": "flight-001", "agent_name": "Flight Agent"}
Response: {"pairing_code": "847293", "expires_at": "..."}
```

**2. User enters pairing code in approval client (Terminal 2)**

**3. Agent sends SPAKE2_A message:**
```
POST /pairing/exchange
Request: {
    "pairing_code": "847293",
    "pake_message": "<base64-encoded msg_out_a>"
}
Response: {
    "session_id": "sess_abc123",
    "pake_message": "<base64-encoded msg_out_b>",
    "agent_id": "flight-001"
}
```

**4. Both sides call finish() and derive identical keys**

**5. Session established with PAKE-derived encryption key**

---

## Component Design

### Component Overview

| Component | File Path | Responsibilities | PAKE Role |
|-----------|-----------|------------------|-----------|
| PAKEHandler | `src/sdk/pake_handler.py` | SPAKE2 wrapper, key derivation, encryption | Both (A & B) |
| CredentialClient | `src/sdk/credential_client.py` | Agent-side SDK, HTTP client | SPAKE2_A |
| ApprovalServer | `src/server/approval_server.py` | Flask HTTP server, API endpoints | SPAKE2_B |
| PairingManager | `src/server/pairing_manager.py` | Session storage, pairing lifecycle | SPAKE2_B |
| ApprovalClient | `src/approval_client.py` | Terminal UI for user approval | None |

### Component 1: PAKEHandler

**Purpose:** Encapsulate SPAKE2 protocol operations and provide encryption/decryption using PAKE-derived keys.

**File:** `src/sdk/pake_handler.py`

**Interface:**
```python
from typing import Tuple, Optional
import base64
from spake2 import SPAKE2_A, SPAKE2_B
from cryptography.fernet import Fernet

class PAKEHandler:
    """
    Wrapper for SPAKE2 protocol operations and encryption.

    Supports both client (SPAKE2_A) and server (SPAKE2_B) roles.
    """

    def __init__(self, role: str):
        """
        Initialize PAKE handler.

        Args:
            role: Either "client" (SPAKE2_A) or "server" (SPAKE2_B)
        """
        self.role = role
        self._spake_instance = None
        self._shared_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None

    def start_exchange(self, password: str) -> bytes:
        """
        Start PAKE protocol exchange.

        Args:
            password: Pairing code as string

        Returns:
            Outbound PAKE message (to send to other party)
        """
        password_bytes = password.encode('utf-8')

        if self.role == "client":
            self._spake_instance = SPAKE2_A(password_bytes)
        else:  # server
            self._spake_instance = SPAKE2_B(password_bytes)

        msg_out = self._spake_instance.start()
        return msg_out

    def finish_exchange(self, msg_in: bytes) -> None:
        """
        Complete PAKE protocol exchange and derive shared key.

        Args:
            msg_in: Inbound PAKE message from other party

        Raises:
            ValueError: If exchange fails (wrong password)
        """
        if not self._spake_instance:
            raise RuntimeError("Must call start_exchange() first")

        try:
            self._shared_key = self._spake_instance.finish(msg_in)

            # Derive Fernet key from shared secret
            key_bytes = self._shared_key[:32]
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)

        except Exception as e:
            raise ValueError(f"PAKE exchange failed: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt data using PAKE-derived key.

        Args:
            plaintext: JSON string to encrypt

        Returns:
            Base64-encoded encrypted data
        """
        if not self._fernet:
            raise RuntimeError("PAKE exchange not completed")

        plaintext_bytes = plaintext.encode('utf-8')
        encrypted = self._fernet.encrypt(plaintext_bytes)
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt data using PAKE-derived key.

        Args:
            ciphertext: Base64-encoded encrypted data

        Returns:
            Decrypted JSON string

        Raises:
            ValueError: If decryption fails (wrong key, tampered data)
        """
        if not self._fernet:
            raise RuntimeError("PAKE exchange not completed")

        try:
            encrypted = base64.b64decode(ciphertext)
            plaintext_bytes = self._fernet.decrypt(encrypted)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def is_ready(self) -> bool:
        """Check if PAKE exchange completed and encryption ready."""
        return self._fernet is not None
```

**Key Design Decisions:**
- Single class supports both client and server roles (avoids code duplication)
- Encapsulates all SPAKE2 complexity (implementer doesn't need to understand internals)
- Provides simple encrypt/decrypt interface (handles base64 encoding)
- Clear error messages for common failure modes

### Component 2: CredentialClient (SDK)

**Purpose:** Agent-side SDK for requesting credentials from remote approval server.

**File:** `src/sdk/credential_client.py`

**Interface:**
```python
from typing import Optional
import requests
import json
import time
import logging
from src.models.credential_response import CredentialResponse, CredentialStatus
from src.utils.credential_handler import SecureCredential
from src.sdk.pake_handler import PAKEHandler

logger = logging.getLogger(__name__)

class CredentialClient:
    """
    SDK for agents to request credentials from remote approval server.

    Handles PAKE pairing, encrypted requests, and session management.
    """

    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        Initialize credential client.

        Args:
            server_url: Base URL of approval server
        """
        self.server_url = server_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.pake_handler: Optional[PAKEHandler] = None

    def pair(self, agent_id: str, agent_name: str) -> str:
        """
        Initiate pairing with approval server.

        Returns pairing code for user to enter in approval client.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name

        Returns:
            6-digit pairing code

        Raises:
            ConnectionError: If server unreachable
        """
        # Step 1: Request pairing code
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
            raise ConnectionError(f"Failed to connect to approval server: {e}")

        # Step 2: Start PAKE exchange on client side
        self.pake_handler = PAKEHandler(role="client")
        msg_out_a = self.pake_handler.start_exchange(pairing_code)

        # Step 3: Send SPAKE2_A message, receive SPAKE2_B message
        logger.info("Waiting for user to enter pairing code...")
        max_attempts = 30  # 30 attempts = 60 seconds at 2s intervals

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

                if response.status_code == 202:  # Waiting for user
                    time.sleep(2)
                    continue

                response.raise_for_status()
                data = response.json()

                # Step 4: Complete PAKE exchange
                msg_in_b = base64.b64decode(data['pake_message'])
                self.pake_handler.finish_exchange(msg_in_b)

                self.session_id = data['session_id']
                logger.info("Pairing successful! Session established.")

                return pairing_code

            except requests.exceptions.RequestException as e:
                if attempt == max_attempts - 1:
                    raise TimeoutError("Pairing timed out - user did not enter code")
                time.sleep(2)

        raise TimeoutError("Pairing timed out")

    def request_credential(
        self,
        domain: str,
        reason: str,
        agent_id: str,
        agent_name: str
    ) -> CredentialResponse:
        """
        Request credential for domain.

        Args:
            domain: Domain name (e.g., "aa.com")
            reason: Human-readable reason
            agent_id: Agent identifier
            agent_name: Agent display name

        Returns:
            CredentialResponse with status and credential
        """
        if not self.session_id or not self.pake_handler:
            raise RuntimeError("Must call pair() first")

        # Build request payload
        import secrets
        import datetime

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

        # Send request
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

            if data['status'] == 'approved':
                # Decrypt credential
                encrypted_cred = data['encrypted_payload']
                decrypted = self.pake_handler.decrypt(encrypted_cred)
                cred_data = json.loads(decrypted)

                credential = SecureCredential(
                    username=cred_data['username'],
                    password=cred_data['password']
                )

                return CredentialResponse(
                    status=CredentialStatus.APPROVED,
                    credential=credential,
                    error_message=None
                )

            elif data['status'] == 'denied':
                return CredentialResponse(
                    status=CredentialStatus.DENIED,
                    credential=None,
                    error_message="User denied credential access"
                )

            else:
                return CredentialResponse(
                    status=CredentialStatus.ERROR,
                    credential=None,
                    error_message=data.get('error', 'Unknown error')
                )

        except requests.exceptions.RequestException as e:
            return CredentialResponse(
                status=CredentialStatus.ERROR,
                credential=None,
                error_message=f"Request failed: {e}"
            )
```

**Key Design Decisions:**
- Polling-based pairing (2-second intervals, 60-second timeout)
- Automatic PAKE exchange during pairing (no manual key management)
- Returns same CredentialResponse as local mode (API compatibility)
- Clear error messages for connection failures

### Component 3: ApprovalServer

**Purpose:** Flask HTTP server handling API endpoints and routing requests to approval UI.

**File:** `src/server/approval_server.py`

**Interface:**
```python
from flask import Flask, request, jsonify
import logging
from src.server.pairing_manager import PairingManager

logger = logging.getLogger(__name__)

app = Flask(__name__)
pairing_manager = PairingManager()

@app.route('/health', methods=['GET'])
def health():
    """Server health check."""
    return jsonify({
        "status": "ok",
        "active_sessions": pairing_manager.active_session_count()
    })

@app.route('/pairing/initiate', methods=['POST'])
def pairing_initiate():
    """
    Initiate pairing - generate pairing code.

    Request: {"agent_id": "...", "agent_name": "..."}
    Response: {"pairing_code": "847293", "expires_at": "..."}
    """
    data = request.get_json()
    agent_id = data.get('agent_id')
    agent_name = data.get('agent_name')

    if not agent_id or not agent_name:
        return jsonify({"error": "Missing agent_id or agent_name"}), 400

    pairing_code, expires_at = pairing_manager.create_pairing(agent_id, agent_name)

    logger.info(f"Pairing initiated for {agent_name} ({agent_id}): {pairing_code}")

    return jsonify({
        "pairing_code": pairing_code,
        "expires_at": expires_at.isoformat() + "Z"
    })

@app.route('/pairing/exchange', methods=['POST'])
def pairing_exchange():
    """
    Execute PAKE protocol message exchange.

    Request: {"pairing_code": "847293", "pake_message": "<base64>"}
    Response: {"session_id": "...", "pake_message": "<base64>", "agent_id": "..."}
    Or: 202 Accepted (waiting for user to enter code)
    """
    data = request.get_json()
    pairing_code = data.get('pairing_code')
    msg_in_a = data.get('pake_message')  # base64-encoded

    if not pairing_code or not msg_in_a:
        return jsonify({"error": "Missing pairing_code or pake_message"}), 400

    # Check if user has entered pairing code yet
    result = pairing_manager.exchange_pake_message(pairing_code, msg_in_a)

    if result['status'] == 'waiting':
        # User hasn't entered code yet
        return jsonify({"status": "waiting"}), 202

    elif result['status'] == 'success':
        # PAKE exchange complete
        return jsonify({
            "session_id": result['session_id'],
            "pake_message": result['pake_message'],  # base64-encoded msg_out_b
            "agent_id": result['agent_id']
        })

    else:
        # Error (expired, invalid, etc.)
        return jsonify({"error": result['error']}), 400

@app.route('/credential/request', methods=['POST'])
def credential_request():
    """
    Request credential (encrypted).

    Request: {"session_id": "...", "encrypted_payload": "<base64>"}
    Response: {"status": "approved", "encrypted_payload": "<base64>"}
    Or: {"status": "denied", "error": "..."}
    """
    data = request.get_json()
    session_id = data.get('session_id')
    encrypted_payload = data.get('encrypted_payload')

    if not session_id or not encrypted_payload:
        return jsonify({"error": "Missing session_id or encrypted_payload"}), 400

    # Delegate to pairing manager (which will prompt user)
    result = pairing_manager.handle_credential_request(session_id, encrypted_payload)

    return jsonify(result)

@app.route('/session/revoke', methods=['POST'])
def session_revoke():
    """
    Revoke session.

    Request: {"session_id": "..."}
    Response: {"revoked": true, "session_id": "..."}
    """
    data = request.get_json()
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    pairing_manager.revoke_session(session_id)

    return jsonify({"revoked": True, "session_id": session_id})

@app.route('/session/status', methods=['GET'])
def session_status():
    """
    Check session status.

    Query: ?session_id=...
    Response: {"active": true, "last_access": "...", "expires_at": "..."}
    """
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400

    status = pairing_manager.get_session_status(session_id)

    if not status:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(status)

def run_server(host='127.0.0.1', port=5000):
    """Run approval server."""
    logger.info(f"Starting approval server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
```

**Key Design Decisions:**
- Standard Flask application structure
- RESTful API design (POST for mutations, GET for queries)
- Delegates business logic to PairingManager (separation of concerns)
- 202 Accepted for polling-based pairing (user hasn't entered code yet)

### Component 4: PairingManager

**Purpose:** Manage pairing lifecycle, session storage, and PAKE server-side operations.

**File:** `src/server/pairing_manager.py`

**Interface:**
```python
import secrets
import datetime
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from src.sdk.pake_handler import PAKEHandler

logger = logging.getLogger(__name__)

@dataclass
class PairingState:
    """State of a pending pairing."""
    agent_id: str
    agent_name: str
    pairing_code: str
    created_at: datetime.datetime
    expires_at: datetime.datetime
    agent_pake_message: Optional[bytes] = None  # SPAKE2_A message
    user_entered: bool = False

@dataclass
class Session:
    """Active session with PAKE-derived key."""
    session_id: str
    agent_id: str
    agent_name: str
    pake_handler: PAKEHandler
    created_at: datetime.datetime
    last_access: datetime.datetime
    expires_at: datetime.datetime

class PairingManager:
    """
    Manage pairing lifecycle and sessions.

    Stores:
    - Pending pairings (waiting for user to enter code)
    - Active sessions (PAKE exchange complete)
    """

    def __init__(self):
        self.pending_pairings: Dict[str, PairingState] = {}
        self.active_sessions: Dict[str, Session] = {}
        self._callback_handler = None  # For UI notifications

    def set_callback_handler(self, handler):
        """Set callback handler for UI notifications."""
        self._callback_handler = handler

    def create_pairing(self, agent_id: str, agent_name: str) -> Tuple[str, datetime.datetime]:
        """
        Create new pairing.

        Returns:
            (pairing_code, expires_at)
        """
        # Generate 6-digit pairing code
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

        # Notify UI (if callback registered)
        if self._callback_handler:
            self._callback_handler.on_pairing_created(pairing_state)

        return pairing_code, expires_at

    def mark_user_entered_code(self, pairing_code: str) -> bool:
        """
        Mark that user entered pairing code in UI.

        Returns:
            True if pairing found and valid
        """
        pairing = self.pending_pairings.get(pairing_code)

        if not pairing:
            logger.warning(f"Invalid pairing code: {pairing_code}")
            return False

        if datetime.datetime.utcnow() > pairing.expires_at:
            logger.warning(f"Expired pairing code: {pairing_code}")
            del self.pending_pairings[pairing_code]
            return False

        pairing.user_entered = True
        logger.info(f"User entered pairing code: {pairing_code}")
        return True

    def exchange_pake_message(self, pairing_code: str, msg_in_a: str) -> Dict:
        """
        Handle PAKE message exchange.

        Args:
            pairing_code: 6-digit code
            msg_in_a: Base64-encoded SPAKE2_A message from agent

        Returns:
            Dict with status and data
        """
        pairing = self.pending_pairings.get(pairing_code)

        if not pairing:
            return {"status": "error", "error": "Invalid pairing code"}

        if datetime.datetime.utcnow() > pairing.expires_at:
            del self.pending_pairings[pairing_code]
            return {"status": "error", "error": "Pairing code expired"}

        # Store agent's PAKE message
        import base64
        pairing.agent_pake_message = base64.b64decode(msg_in_a)

        # Check if user has entered code yet
        if not pairing.user_entered:
            return {"status": "waiting"}

        # User has entered code - complete PAKE exchange
        pake_handler = PAKEHandler(role="server")
        msg_out_b = pake_handler.start_exchange(pairing_code)

        try:
            pake_handler.finish_exchange(pairing.agent_pake_message)
        except ValueError as e:
            logger.error(f"PAKE exchange failed: {e}")
            return {"status": "error", "error": "PAKE exchange failed"}

        # Create session
        session_id = f"sess_{secrets.token_hex(16)}"
        now = datetime.datetime.utcnow()

        session = Session(
            session_id=session_id,
            agent_id=pairing.agent_id,
            agent_name=pairing.agent_name,
            pake_handler=pake_handler,
            created_at=now,
            last_access=now,
            expires_at=now + datetime.timedelta(minutes=30)
        )

        self.active_sessions[session_id] = session

        # Remove pairing (one-time use)
        del self.pending_pairings[pairing_code]

        logger.info(f"Session established: {session_id} for {pairing.agent_name}")

        return {
            "status": "success",
            "session_id": session_id,
            "pake_message": base64.b64encode(msg_out_b).decode('utf-8'),
            "agent_id": pairing.agent_id
        }

    def handle_credential_request(self, session_id: str, encrypted_payload: str) -> Dict:
        """
        Handle credential request (prompt user, retrieve from vault).

        Returns:
            Dict with status and encrypted credential or error
        """
        session = self.active_sessions.get(session_id)

        if not session:
            return {"status": "error", "error": "Invalid or expired session"}

        # Update last access
        session.last_access = datetime.datetime.utcnow()

        # Check timeout
        if datetime.datetime.utcnow() > session.expires_at:
            del self.active_sessions[session_id]
            return {"status": "error", "error": "Session expired"}

        # Decrypt request
        try:
            plaintext = session.pake_handler.decrypt(encrypted_payload)
            request_data = json.loads(plaintext)
        except Exception as e:
            logger.error(f"Failed to decrypt request: {e}")
            return {"status": "error", "error": "Decryption failed"}

        # Validate timestamp (prevent replay)
        timestamp = datetime.datetime.fromisoformat(request_data['timestamp'].rstrip('Z'))
        age = (datetime.datetime.utcnow() - timestamp).total_seconds()
        if age > 300:  # 5 minutes
            return {"status": "error", "error": "Request too old"}

        # Delegate to callback handler (approval UI)
        if self._callback_handler:
            result = self._callback_handler.handle_credential_request(
                session=session,
                domain=request_data['domain'],
                reason=request_data['reason']
            )

            if result['approved']:
                # Encrypt credential
                import secrets
                cred_payload = {
                    "username": result['username'],
                    "password": result['password'],
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "nonce": secrets.token_hex(8)
                }

                encrypted_cred = session.pake_handler.encrypt(json.dumps(cred_payload))

                return {
                    "status": "approved",
                    "encrypted_payload": encrypted_cred
                }
            else:
                return {
                    "status": "denied",
                    "error": result.get('error', 'User denied')
                }
        else:
            return {"status": "error", "error": "No approval handler registered"}

    def revoke_session(self, session_id: str):
        """Revoke session immediately."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Session revoked: {session_id}")

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get session status."""
        session = self.active_sessions.get(session_id)

        if not session:
            return None

        return {
            "active": True,
            "last_access": session.last_access.isoformat() + "Z",
            "expires_at": session.expires_at.isoformat() + "Z"
        }

    def active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)
```

**Key Design Decisions:**
- Separation of pairing (pending) vs. session (active) state
- Callback pattern for UI integration (decouples server from UI)
- Automatic cleanup of expired pairings/sessions
- One-time use pairing codes (deleted after session creation)

### Component 5: ApprovalClient

**Purpose:** Terminal UI for user to enter pairing codes and approve credential requests.

**File:** `src/approval_client.py`

**Interface:**
```python
import logging
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from src.server.approval_server import run_server, pairing_manager
from src.agents.bitwarden_agent import BitwardenAgent
from src.utils.bitwarden_cli import BitwardenCLI
from src.utils.credential_handler import SecureCredential
import threading

logger = logging.getLogger(__name__)

class ApprovalCallbackHandler:
    """Callback handler for PairingManager to interact with UI."""

    def __init__(self, bitwarden_agent: BitwardenAgent):
        self.bitwarden_agent = bitwarden_agent
        self.console = Console()

    def on_pairing_created(self, pairing_state):
        """Notify user of new pairing request."""
        self.console.print()
        panel = Panel(
            f"[bold cyan]Agent:[/bold cyan] {pairing_state.agent_name}\n"
            f"[bold cyan]Agent ID:[/bold cyan] {pairing_state.agent_id}\n\n"
            f"[bold yellow]Pairing code:[/bold yellow] [bold green]{pairing_state.pairing_code}[/bold green]\n\n"
            f"Enter this code in approval client to approve pairing.",
            title="🔗 New Pairing Request",
            border_style="blue"
        )
        self.console.print(panel)

    def handle_credential_request(self, session, domain, reason):
        """
        Prompt user for approval and retrieve credential.

        Returns:
            Dict with 'approved' bool and credential data if approved
        """
        self.console.print()
        panel = Panel(
            f"[bold cyan]Agent:[/bold cyan] {session.agent_name}\n"
            f"[bold cyan]Domain:[/bold cyan] {domain}\n"
            f"[bold cyan]Reason:[/bold cyan] {reason}\n\n"
            f"[bold yellow]Allow this agent to access your credentials?[/bold yellow]\n\n"
            f"[green]\\[Y][/green] Approve    [red]\\[N][/red] Deny",
            title="🔐 Credential Access Request",
            border_style="blue"
        )
        self.console.print(panel)

        response = Prompt.ask(
            "Decision",
            choices=["Y", "y", "N", "n"],
            default="N"
        )

        if response.upper() != "Y":
            return {"approved": False, "error": "User denied"}

        # User approved - get credential from vault
        # Reuse BitwardenAgent logic
        import getpass
        password = getpass.getpass("Enter Bitwarden vault password: ")

        try:
            cli = BitwardenCLI()
            session_key = cli.unlock(password)
            items = cli.list_items(domain, session_key)

            login_item = next(
                (item for item in items if item.get("type") == 1),
                None
            )

            if not login_item:
                return {"approved": False, "error": f"No credential found for {domain}"}

            username = login_item.get("login", {}).get("username")
            password_value = login_item.get("login", {}).get("password")

            cli.lock()

            return {
                "approved": True,
                "username": username,
                "password": password_value
            }

        except Exception as e:
            logger.error(f"Failed to retrieve credential: {e}")
            return {"approved": False, "error": str(e)}

class ApprovalClient:
    """Terminal-based approval client."""

    def __init__(self):
        self.console = Console()
        self.bitwarden_agent = BitwardenAgent()
        self.callback_handler = ApprovalCallbackHandler(self.bitwarden_agent)

    def run(self, host='127.0.0.1', port=5000):
        """
        Run approval client.

        Starts Flask server in background thread and runs UI loop.
        """
        # Register callback handler
        pairing_manager.set_callback_handler(self.callback_handler)

        # Start Flask server in background thread
        server_thread = threading.Thread(
            target=run_server,
            args=(host, port),
            daemon=True
        )
        server_thread.start()

        # Display welcome
        self.console.print()
        self.console.print("[bold cyan]Approval Client Started[/bold cyan]")
        self.console.print(f"Listening on {host}:{port}")
        self.console.print()
        self.console.print("Commands:")
        self.console.print("  [bold]pair[/bold] <code>  - Enter pairing code from agent")
        self.console.print("  [bold]sessions[/bold]     - List active sessions")
        self.console.print("  [bold]revoke[/bold] <id>  - Revoke session")
        self.console.print("  [bold]quit[/bold]         - Exit")
        self.console.print()

        # Run command loop
        while True:
            try:
                command = Prompt.ask("[bold cyan]approval>[/bold cyan]").strip()

                if command == "quit":
                    break
                elif command.startswith("pair "):
                    code = command.split()[1]
                    self._handle_pair_command(code)
                elif command == "sessions":
                    self._handle_sessions_command()
                elif command.startswith("revoke "):
                    session_id = command.split()[1]
                    self._handle_revoke_command(session_id)
                else:
                    self.console.print("[red]Unknown command[/red]")

            except KeyboardInterrupt:
                break

    def _handle_pair_command(self, code: str):
        """Handle user entering pairing code."""
        success = pairing_manager.mark_user_entered_code(code)
        if success:
            self.console.print(f"[green]✓[/green] Pairing code accepted: {code}")
        else:
            self.console.print(f"[red]✗[/red] Invalid or expired pairing code")

    def _handle_sessions_command(self):
        """Display active sessions."""
        sessions = pairing_manager.active_sessions

        if not sessions:
            self.console.print("[yellow]No active sessions[/yellow]")
            return

        table = Table(title="Active Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Agent Name", style="green")
        table.add_column("Created", style="yellow")

        for session in sessions.values():
            table.add_row(
                session.session_id,
                session.agent_name,
                session.created_at.strftime("%H:%M:%S")
            )

        self.console.print(table)

    def _handle_revoke_command(self, session_id: str):
        """Revoke session."""
        pairing_manager.revoke_session(session_id)
        self.console.print(f"[green]✓[/green] Session revoked: {session_id}")

def main():
    """Main entry point for approval client."""
    import sys
    from src.utils.logging_config import setup_logging

    setup_logging(level="INFO")

    client = ApprovalClient()
    client.run()

if __name__ == '__main__':
    main()
```

**Key Design Decisions:**
- Interactive command-line interface (not fully automated)
- Rich library for consistent UI with existing POC
- Callback pattern integrates with PairingManager
- Reuses BitwardenAgent vault access logic

---

## API Specification

### Endpoint Summary

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/health` | Health check | None |
| POST | `/pairing/initiate` | Generate pairing code | None |
| POST | `/pairing/exchange` | PAKE message exchange | Pairing code |
| POST | `/credential/request` | Request credential | Session |
| POST | `/session/revoke` | Revoke session | None |
| GET | `/session/status` | Check session | Session |

### Detailed Endpoint Specifications

See Component 3 (ApprovalServer) above for complete implementation details. All endpoints follow RESTful conventions:

- **Success:** 200 OK (or 202 Accepted for pending operations)
- **Client Error:** 400 Bad Request (invalid input)
- **Not Found:** 404 Not Found (session/pairing not found)
- **Server Error:** 500 Internal Server Error

---

## Message Format Specification

### Encrypted Message Structure

All credential data encrypted with PAKE-derived keys uses this envelope:

```python
{
    "data": { ... },  # Actual payload (credential or request)
    "timestamp": "2025-10-29T00:00:00Z",  # ISO 8601 UTC
    "nonce": "a1b2c3d4e5f6"  # 16-character hex (8 bytes)
}
```

**Encryption Process:**
1. Serialize to JSON
2. Encrypt with Fernet (using PAKE-derived key)
3. Base64-encode encrypted bytes
4. Transmit as string in API

**Decryption Process:**
1. Base64-decode
2. Decrypt with Fernet (using PAKE-derived key)
3. Parse JSON
4. Validate timestamp (<5 minutes old)
5. Check nonce uniqueness (prevent replay)

---

## Error Handling Strategy

### Error Categories

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| **Connection Errors** | Server unreachable, timeout | Retry with exponential backoff (3 attempts) |
| **PAKE Errors** | Wrong pairing code, exchange failed | No retry - clear error message to user |
| **Session Errors** | Expired, revoked, not found | Prompt user to pair again |
| **Vault Errors** | Wrong password, credential not found | Retry vault password (3 attempts) |
| **Encryption Errors** | Decryption failed, tampered message | Log and return generic error (security) |

### Retry Logic

**Transient Errors (Auto-Retry):**
- Connection refused
- Timeout
- 5xx server errors

**Retry Configuration:**
```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 2.0

for attempt in range(MAX_RETRIES):
    try:
        # ... make request ...
        break
    except TransientError as e:
        if attempt == MAX_RETRIES - 1:
            raise
        backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt)
        time.sleep(backoff)
```

**Permanent Errors (No Retry):**
- 4xx client errors (bad request, not found)
- PAKE exchange failure
- Authentication failure

### Error Messages

All error messages should:
1. Explain what went wrong
2. Suggest corrective action
3. Avoid exposing sensitive details

**Examples:**
- ❌ "PAKE exchange failed: invalid MAC"
- ✅ "Pairing failed. Please verify the pairing code and try again."

- ❌ "Session key mismatch in decrypt()"
- ✅ "Unable to decrypt message. Session may have expired. Please pair again."

---

## Session Management

### Session Lifecycle

```
1. Pairing Created    → pending_pairings (5 min TTL)
2. User Enters Code   → pairing.user_entered = True
3. PAKE Exchange      → active_sessions (30 min TTL)
4. Credential Request → session.last_access updated
5. Timeout/Revoke     → session deleted
```

### Timeout Behavior

| Timeout Type | Duration | Action |
|--------------|----------|--------|
| Pairing Code | 5 minutes | Delete pairing, agent gets timeout error |
| Session Inactivity | 30 minutes | Delete session, next request fails |
| Request Age | 5 minutes | Reject request (replay protection) |

### Session Storage

**In-Memory Storage (MVP):**
```python
pending_pairings: Dict[str, PairingState]  # key: pairing_code
active_sessions: Dict[str, Session]         # key: session_id
```

**Post-MVP (File-Based):**
- Persist sessions to JSON file
- Survive server restart
- Load sessions on startup
- Requires careful key serialization (security concern)

---

## Testing Strategy

### Test Levels

| Level | Scope | Framework | Key Tests |
|-------|-------|-----------|-----------|
| **Unit** | Individual components | pytest | PAKE key derivation, encryption, API endpoints |
| **Integration** | Two-process communication | pytest + subprocess | Full pairing flow, credential request |
| **End-to-End** | Complete user flow | pytest + Playwright | Agent logs in using remote credential |
| **Security** | Crypto validation | pytest | Keys not logged, credentials encrypted |

### Unit Tests

**PAKEHandler Tests:**
```python
def test_pake_key_derivation_match():
    """Test that client and server derive identical keys."""
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

    # Encrypt/decrypt test
    plaintext = "test message"
    encrypted = client_handler.encrypt(plaintext)
    decrypted = server_handler.decrypt(encrypted)

    assert decrypted == plaintext

def test_pake_wrong_password_fails():
    """Test that wrong password causes PAKE to fail."""
    client_handler = PAKEHandler(role="client")
    msg_out_a = client_handler.start_exchange("123456")

    server_handler = PAKEHandler(role="server")
    msg_out_b = server_handler.start_exchange("999999")  # Wrong!

    client_handler.finish_exchange(msg_out_b)

    with pytest.raises(ValueError):
        server_handler.finish_exchange(msg_out_a)
```

**CredentialClient Tests:**
```python
def test_credential_client_pair_success(mock_server):
    """Test successful pairing with mock server."""
    client = CredentialClient("http://localhost:5000")
    pairing_code = client.pair("test-agent", "Test Agent")

    assert client.session_id is not None
    assert client.pake_handler is not None
    assert client.pake_handler.is_ready()

def test_credential_client_request_credential(mock_server):
    """Test credential request after pairing."""
    client = CredentialClient("http://localhost:5000")
    client.pair("test-agent", "Test Agent")

    response = client.request_credential(
        domain="example.com",
        reason="Testing",
        agent_id="test-agent",
        agent_name="Test Agent"
    )

    assert response.status == CredentialStatus.APPROVED
    assert response.credential is not None
```

### Integration Tests (Two-Process)

**Test Infrastructure:**
```python
import subprocess
import time
import pytest

@pytest.fixture
def approval_server():
    """Start approval server in subprocess."""
    proc = subprocess.Popen(
        ["python", "-m", "src.approval_client"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(2)

    yield proc

    # Cleanup
    proc.terminate()
    proc.wait()

def test_full_pairing_flow(approval_server):
    """Test complete pairing flow across processes."""
    # ... test implementation ...
```

### Security Tests

**Encryption Validation:**
```python
def test_credentials_never_plaintext_in_network():
    """Verify credentials are encrypted in all network messages."""
    # ... capture network traffic ...
    # ... assert no plaintext credentials ...

def test_session_keys_never_logged():
    """Verify session keys never appear in logs."""
    # ... capture log output ...
    # ... assert no key material in logs ...

def test_replay_attack_rejected():
    """Verify old messages rejected (timestamp validation)."""
    # ... send request, capture encrypted payload ...
    # ... replay same payload 10 minutes later ...
    # ... assert rejected ...
```

### Test Coverage Goals

- PAKEHandler: 100% (critical crypto code)
- CredentialClient: 90%
- ApprovalServer: 85%
- PairingManager: 90%
- Integration tests: All happy paths + major error paths

---

## Implementation Phases

### Phase 1: Foundation (Days 1-2)

**Goal:** PAKE protocol working, keys derived correctly

**Tasks:**
1. Install dependencies (spake2, Flask)
2. Implement PAKEHandler (src/sdk/pake_handler.py)
3. Write unit tests for PAKE key derivation
4. Verify client and server derive identical keys
5. Implement basic encryption/decryption with PAKE keys

**Acceptance:**
- [ ] PAKEHandler unit tests pass
- [ ] Client and server derive matching keys
- [ ] Encrypt/decrypt works with PAKE-derived keys

**Critical:** DO NOT move to Phase 2 until PAKE is working correctly. This is the educational foundation.

### Phase 2: Pairing Flow (Days 3-4)

**Goal:** Agent can pair with approval server

**Tasks:**
1. Implement ApprovalServer Flask app (src/server/approval_server.py)
2. Implement PairingManager (src/server/pairing_manager.py)
3. Implement CredentialClient.pair() (src/sdk/credential_client.py)
4. Implement /pairing/initiate endpoint
5. Implement /pairing/exchange endpoint (PAKE exchange)
6. Write integration tests for pairing flow

**Acceptance:**
- [ ] Agent generates pairing code
- [ ] Server receives SPAKE2_A message
- [ ] Server sends SPAKE2_B message
- [ ] Both sides derive identical session keys
- [ ] Session created with session_id

### Phase 3: Credential Flow (Days 5-6)

**Goal:** Agent can request credentials, user can approve

**Tasks:**
1. Implement ApprovalClient UI (src/approval_client.py)
2. Implement /credential/request endpoint
3. Implement CredentialClient.request_credential()
4. Implement PairingManager.handle_credential_request()
5. Integrate with BitwardenCLI for vault access
6. Write end-to-end tests

**Acceptance:**
- [ ] Agent sends encrypted credential request
- [ ] Server decrypts request using PAKE key
- [ ] User sees approval prompt with agent details
- [ ] User approves, vault unlocked, credential retrieved
- [ ] Credential encrypted with PAKE key
- [ ] Agent decrypts and receives credential
- [ ] FlightAgent logs into aa.com successfully

### Phase 4: Dual-Mode Integration (Day 7)

**Goal:** Both local and remote modes work

**Tasks:**
1. Modify main.py to add --mode flag
2. Modify FlightBookingAgent to accept credential source
3. Implement conditional initialization based on mode
4. Write regression tests for local mode
5. Document both modes in README

**Acceptance:**
- [ ] `python -m src.main --mode local` works (existing behavior)
- [ ] `python -m src.main --mode remote` works (new behavior)
- [ ] All existing tests pass
- [ ] No modifications to existing local mode code

### Phase 5: Polish & Documentation (Day 8+)

**Goal:** Production-ready POC

**Tasks:**
1. Implement session management (/session/revoke, /session/status)
2. Implement timeout handling
3. Error handling and user-friendly error messages
4. Logging and audit trail for remote mode
5. Two-terminal setup documentation
6. Architecture diagrams
7. Troubleshooting guide
8. PAKE educational documentation

**Acceptance:**
- [ ] All error paths handled gracefully
- [ ] Clear error messages with corrective actions
- [ ] README explains both modes
- [ ] Troubleshooting guide for common issues
- [ ] PAKE concepts explained in documentation

---

## File Structure

### New Files to Create

```
src/
├── sdk/                          # NEW: Agent-side SDK
│   ├── __init__.py
│   ├── pake_handler.py          # PAKE wrapper (client & server)
│   └── credential_client.py     # Agent SDK for remote requests
│
├── server/                       # NEW: Approval server
│   ├── __init__.py
│   ├── approval_server.py       # Flask HTTP server
│   └── pairing_manager.py       # Session management
│
├── approval_client.py            # NEW: Terminal UI for approval
│
└── main.py                       # MODIFY: Add --mode flag

tests/
├── test_pake_handler.py          # NEW: PAKE unit tests
├── test_credential_client.py     # NEW: SDK unit tests
├── test_approval_server.py       # NEW: Server API tests
├── test_pairing_manager.py       # NEW: Session management tests
└── test_integration_remote.py    # NEW: Two-process integration tests
```

### Modified Files

**src/main.py:**
```python
# Add --mode argument
parser.add_argument(
    '--mode',
    choices=['local', 'remote'],
    default='local',
    help='Credential access mode (default: local)'
)

# Conditional initialization
if args.mode == 'local':
    # Existing path (no changes)
    bitwarden_agent = BitwardenAgent()
    flight_agent = FlightBookingAgent(bitwarden_agent=bitwarden_agent, ...)
else:
    # New remote path
    credential_client = CredentialClient(server_url="http://localhost:5000")
    flight_agent = FlightBookingAgent(credential_client=credential_client, ...)
```

**src/agents/flight_booking_agent.py:**
```python
# Accept either Bitwarden agent or credential client
def __init__(
    self,
    bitwarden_agent: Optional[BitwardenAgent] = None,
    credential_client: Optional[CredentialClient] = None,
    headless: bool = False
):
    if bitwarden_agent:
        self.credential_source = bitwarden_agent
    elif credential_client:
        self.credential_source = credential_client
    else:
        raise ValueError("Must provide bitwarden_agent or credential_client")

    # ... rest of init ...

# Use credential source (polymorphic)
def _request_credentials(self, domain, reason):
    return self.credential_source.request_credential(
        domain=domain,
        reason=reason,
        agent_id=self.agent_id,
        agent_name="Flight Booking Agent"
    )
```

---

## Acceptance Criteria

### Functional Acceptance

- [ ] **Local mode unchanged:** `python -m src.main --mode local` works exactly as before
- [ ] **Remote mode works:** `python -m src.main --mode remote` successfully pairs and retrieves credentials
- [ ] **PAKE protocol executes:** Both sides exchange SPAKE2 messages and derive identical keys
- [ ] **Credentials encrypted:** All credential data encrypted with PAKE-derived keys
- [ ] **Pairing flow:** User enters pairing code in approval client, pairing succeeds
- [ ] **Approval flow:** User sees request, approves, credential delivered
- [ ] **Login succeeds:** Agent logs into aa.com using remotely-retrieved credentials
- [ ] **Session management:** Timeout and revocation work correctly

### PAKE-Specific Acceptance (Critical)

- [ ] **Protocol messages exchanged:** SPAKE2_A and SPAKE2_B messages transmitted (not keys)
- [ ] **Keys derived locally:** Both sides call `finish()` and derive keys independently
- [ ] **Pairing code never transmitted:** Code used only for PAKE initialization
- [ ] **Keys match:** Unit tests verify client and server keys are identical
- [ ] **Mutual authentication:** Wrong pairing code causes PAKE to fail
- [ ] **Established library used:** python-spake2 library used (not custom crypto)
- [ ] **Tests validate PAKE:** Unit tests specifically test PAKE correctness

### Educational Acceptance

- [ ] **Team understands PAKE:** Code review confirms team grasps PAKE concepts
- [ ] **Code is educational:** Comments explain PAKE protocol steps
- [ ] **Documentation teaches:** README explains PAKE concepts
- [ ] **Implementation is correct:** Not simplified or simulated

### Security Acceptance

- [ ] **No plaintext credentials:** Network traffic inspection shows no plaintext
- [ ] **No logged keys:** Log inspection shows no session keys
- [ ] **One-time codes:** Pairing codes cannot be reused
- [ ] **Replay protection:** Old messages rejected (timestamp validation)

### Testing Acceptance

- [ ] **All tests pass:** Local mode tests unchanged, new remote tests pass
- [ ] **PAKE unit tests:** 100% coverage of PAKEHandler
- [ ] **Integration tests:** Two-process pairing and credential flow tested
- [ ] **Security tests:** Encryption and key management validated

### Documentation Acceptance

- [ ] **README updated:** Both modes documented with examples
- [ ] **Two-terminal setup:** Clear instructions for starting approval server and agent
- [ ] **Troubleshooting:** Common issues and solutions documented
- [ ] **PAKE explained:** Educational content about PAKE protocol included
- [ ] **Architecture diagrams:** Component and sequence diagrams provided

---

## Risk Mitigation

### High-Priority Risks (from Requirements Analysis)

**RISK-T1: PAKE Implementation Complexity**
- **Mitigation:** Use python-spake2 (simplest library), allocate extra time for Phase 1, write comprehensive unit tests
- **Contingency:** If python-spake2 too complex, try pysrp (more mature but similar API)

**RISK-T3: Backward Compatibility Breakage**
- **Mitigation:** Conditional imports, no modifications to existing code, regression tests run continuously
- **Contingency:** Revert changes and isolate remote mode in separate module

**RISK-T4: Two-Process Testing**
- **Mitigation:** Build test infrastructure early (Phase 2), use pytest fixtures for subprocess management
- **Contingency:** Manual testing with documented procedures if automation too complex

### Medium-Priority Risks

**RISK-S1/S2: Credential/Key Exposure**
- **Mitigation:** Code review checklist, search codebase for logging statements, encrypt all network traffic
- **Testing:** Security tests validate no plaintext in logs or network traffic

**RISK-I2: Network Reliability**
- **Mitigation:** Retry logic with exponential backoff, clear timeout messages
- **Testing:** Integration tests with simulated network failures

---

## Next Steps for Implementer

1. **Read this document thoroughly** - Understand all architectural decisions and rationale
2. **Review requirements documents** - Read requirements_breakdown.md for complete requirements
3. **Set up development environment** - Install dependencies (spake2, Flask, pytest)
4. **Start with Phase 1** - Implement PAKEHandler and get PAKE working correctly
5. **Do NOT skip PAKE validation** - Verify keys match before moving to Phase 2
6. **Follow implementation phases** - Complete each phase before moving to next
7. **Write tests continuously** - Test each component as you build it
8. **Ask questions** - If PAKE behavior is unclear, research and document findings

## Summary of Architectural Decisions

| Decision | Selection | Rationale |
|----------|-----------|-----------|
| **PAKE Library** | python-spake2 | Pure Python, simple API, excellent for learning |
| **HTTP Framework** | Flask | Synchronous model, minimal complexity |
| **Session Storage** | In-memory (dict) | Simplifies MVP, no persistence needed |
| **Transport** | HTTP polling | Simpler than WebSocket, sufficient for localhost |
| **Pairing Code** | 6-digit numeric | User-friendly for POC |
| **Error Recovery** | 3 retries, exp backoff | Balance reliability with simplicity |
| **Encryption** | Fernet (PAKE keys) | Already in use, symmetric encryption |

---

**Status:** READY_FOR_IMPLEMENTATION

**Implementer:** Proceed to Phase 1 - Foundation

**Remember:** This is an educational project. Take time to understand PAKE correctly. Quality over speed.
