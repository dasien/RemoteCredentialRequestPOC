---
enhancement: remote-credential-request
agent: requirements-analyst
task_id: task_1761746010_46076
timestamp: 2025-10-29T00:00:00Z
status: READY_FOR_DEVELOPMENT
---

# Requirements Breakdown: Remote Credential Access with PAKE Implementation

## Executive Summary

This document provides a detailed breakdown of requirements for extending the existing credential-request POC to support a remote/distributed architecture with actual PAKE (Password-Authenticated Key Exchange) protocol implementation.

**Critical Context:** This is an **educational project** with the primary goal of learning and understanding PAKE protocols through implementation. Quality and correctness take absolute priority over speed.

## Functional Requirements

### FR-1: Dual-Mode Operation
**Description:** System must support both existing local mode and new remote mode without breaking existing functionality.

**Acceptance Criteria:**
- [ ] `--mode local` flag runs existing POC without any changes
- [ ] `--mode remote` flag activates new remote architecture
- [ ] Local mode continues to pass all existing tests
- [ ] Mode selection is explicit via command-line flag
- [ ] Default mode behavior is documented clearly

**Priority:** MUST HAVE
**Complexity:** Low (conditional initialization)

### FR-2: Agent Pairing with PAKE Protocol
**Description:** Agent must establish secure pairing with approval client using an actual PAKE protocol (SPAKE2, OPAQUE, SRP, or CPace).

**Acceptance Criteria:**
- [ ] Agent generates cryptographically random 6-digit pairing code (100000-999999)
- [ ] Pairing code displayed clearly to user in agent terminal
- [ ] User enters pairing code in approval client terminal
- [ ] **CRITICAL:** PAKE protocol messages exchanged between agent and server
- [ ] Both agent and approval server independently derive identical session key
- [ ] Session key NEVER transmitted over network (derived locally by PAKE protocol)
- [ ] Pairing code is one-time use only (cannot be reused)
- [ ] Pairing code expires after 5 minutes if unused
- [ ] Invalid pairing codes are rejected with clear error messages
- [ ] Session established with PAKE-derived encryption key

**Priority:** MUST HAVE
**Complexity:** HIGH (cryptographic protocol implementation)
**Educational Value:** HIGHEST (core learning objective)

**Technical Notes:**
- Must use established PAKE library (python-spake2, pysrp, opaque-cloudflare)
- NOT acceptable: PBKDF2 alone, scrypt alone, Argon2 alone (these are password hashing, not PAKE)
- Must demonstrate mutual authentication property of PAKE
- Must show password/code never transmitted

### FR-3: Approval Server
**Description:** Separate process runs HTTP/WebSocket server that handles credential requests from remote agents.

**Acceptance Criteria:**
- [ ] Server starts on configurable port (default: 5000)
- [ ] Server implements required API endpoints (see API specification)
- [ ] Server executes server-side PAKE protocol during pairing
- [ ] Server manages active sessions with PAKE-derived keys
- [ ] Server encrypts/decrypts messages using PAKE-derived session keys
- [ ] Server routes credential requests to approval UI
- [ ] Server handles multiple concurrent sessions (SHOULD HAVE)
- [ ] Server implements health check endpoint
- [ ] Server logs audit events (pairing, requests, approvals)

**Priority:** MUST HAVE
**Complexity:** Medium

### FR-4: Encrypted Communication
**Description:** All credential requests and responses must be encrypted using session keys derived from PAKE protocol execution.

**Acceptance Criteria:**
- [ ] Credential request payload encrypted before transmission
- [ ] Encryption uses PAKE-derived session key (not a transmitted key)
- [ ] Encrypted payload includes timestamp and nonce (prevent replay)
- [ ] Server decrypts request using same PAKE-derived session key
- [ ] Response payload encrypted before returning to agent
- [ ] Agent decrypts response using same PAKE-derived session key
- [ ] Credentials NEVER appear in plaintext in network messages
- [ ] Message format supports versioning for future extensions
- [ ] Encryption failure results in clear error (not silent failure)

**Priority:** MUST HAVE
**Complexity:** Medium (depends on PAKE implementation)

### FR-5: User Approval UI
**Description:** Approval client must present credential requests to user and collect approval/denial decisions.

**Acceptance Criteria:**
- [ ] Terminal-based UI displays credential request details
- [ ] User sees: agent name, domain, reason for request
- [ ] User can approve (Y), deny (N), or revoke session (R)
- [ ] Approval prompts for Bitwarden vault password
- [ ] Vault unlocked only for duration of credential retrieval
- [ ] Vault automatically locked after retrieval
- [ ] Denial returns clear error message to agent
- [ ] UI shows list of active sessions
- [ ] UI provides session management controls
- [ ] UI formatting matches existing POC style (Rich library)

**Priority:** MUST HAVE
**Complexity:** Low (reuses existing BitwardenAgent UI patterns)

### FR-6: Credential Delivery
**Description:** Approved credentials must be securely delivered to agent over network using PAKE-derived encryption.

**Acceptance Criteria:**
- [ ] Credentials retrieved from Bitwarden vault via CLI
- [ ] Credentials encrypted with PAKE-derived session key
- [ ] Encrypted credentials transmitted to agent
- [ ] Agent receives and decrypts credentials
- [ ] Decrypted credentials wrapped in SecureCredential object
- [ ] Credentials used successfully for login (aa.com test)
- [ ] Roundtrip time < 5 seconds (local network)
- [ ] Network failures handled gracefully with retry logic

**Priority:** MUST HAVE
**Complexity:** Medium

### FR-7: Session Management
**Description:** PAKE pairing establishes a session that can be monitored and revoked by user.

**Acceptance Criteria:**
- [ ] Successful pairing creates session with unique ID
- [ ] Session tracks: agent_id, agent_name, PAKE-derived key, created_at, last_access
- [ ] Session timeout after 30 minutes of inactivity
- [ ] User can revoke active sessions from approval UI
- [ ] Revoked session immediately rejects credential requests
- [ ] Session status queryable by agent
- [ ] Multiple sessions supported (one per paired agent)
- [ ] Session data structure supports future extensions

**Priority:** MUST HAVE
**Complexity:** Medium

### FR-8: Backward Compatibility
**Description:** Existing local mode POC must continue to work unchanged.

**Acceptance Criteria:**
- [ ] All existing unit tests pass without modification
- [ ] All existing integration tests pass without modification
- [ ] Local mode uses same components (BitwardenAgent, BitwardenCLI)
- [ ] No new dependencies required for local mode
- [ ] Local mode performance unchanged
- [ ] Local mode code paths isolated from remote mode code
- [ ] Documentation clearly explains both modes

**Priority:** MUST HAVE
**Complexity:** Low (proper conditional architecture)

## Non-Functional Requirements

### NFR-1: Security

**PAKE Protocol Security:**
- Implement actual PAKE protocol (SPAKE2, OPAQUE, SRP, or CPace)
- Pairing code used only for PAKE protocol authentication
- Session keys derived through PAKE protocol execution (not transmitted)
- Mutual authentication demonstrated (both sides prove knowledge of code)
- Resistance to passive eavesdropping (protocol messages safe to transmit)

**Data Security:**
- Pairing codes must be one-time use
- Session keys (derived from PAKE) never logged or transmitted
- Credentials encrypted in transit using PAKE-derived keys
- Credentials never visible in plaintext in logs or network traffic
- Vault password never logged or stored

**Session Security:**
- Session timeout enforced (30 minutes inactivity)
- Session revocation immediate (<1 second)
- Nonces and timestamps prevent replay attacks
- Stale messages rejected (>5 minutes old)

**Acceptable Simplifications (for POC/educational purposes):**
- Localhost deployment (no TLS required)
- Simplified error recovery
- No production-grade attack resistance
- Focus on demonstrating PAKE concepts correctly

### NFR-2: Performance

**Latency:**
- Credential request roundtrip: < 5 seconds (local network)
- PAKE protocol execution: < 2 seconds
- Encryption/decryption overhead: < 100ms per message
- Session revocation propagation: < 1 second

**Resource Usage:**
- Minimal memory footprint for session storage
- No memory leaks in long-running approval server
- Efficient PAKE library usage (no unnecessary re-computation)

**Scalability (SHOULD HAVE):**
- Support multiple concurrent agent sessions
- Handle multiple credential requests per session
- Graceful performance degradation under load

### NFR-3: Reliability

**Error Handling:**
- Network failures detected and reported clearly
- Timeout handling for all network operations
- Connection failures suggest corrective actions to user
- Approval server crashes don't corrupt session state
- Agent crashes can reconnect with new pairing

**Recovery:**
- Failed credential requests can be retried
- Transient network errors trigger automatic retry (3 attempts)
- Permanent errors reported clearly without retry loop
- Session state survives minor disruptions

**Validation:**
- All incoming messages validated before processing
- Malformed messages rejected with clear error
- Type checking on all data structures
- Encryption verification before decryption attempts

### NFR-4: Usability

**Terminal UI:**
- Clear visual separation between agent and approval terminals
- Pairing code prominently displayed with formatting
- Status updates in real-time (waiting, approved, denied)
- Error messages actionable ("Start approval server first")
- Progress indicators for long operations (vault unlock)

**Documentation:**
- README includes setup instructions for both modes
- Two-terminal startup process clearly documented
- Troubleshooting guide for common issues
- Architecture diagrams showing local vs. remote mode
- PAKE protocol explanation for learning purposes

**Developer Experience:**
- Clear code comments explaining PAKE protocol steps
- Unit tests demonstrate PAKE correctness
- Example scripts for testing two-process setup
- Error messages include context for debugging

### NFR-5: Compatibility

**Platform Support:**
- Works on macOS, Linux, Windows (localhost networking)
- Python 3.8+ compatibility
- No platform-specific dependencies for core functionality

**Dependency Management:**
- PAKE library added as new dependency (python-spake2 or similar)
- Flask/FastAPI for HTTP server (architect choice)
- All existing dependencies remain (Playwright, Bitwarden CLI, Rich)
- Dependencies clearly documented in requirements.txt

**Integration:**
- Works with existing Bitwarden CLI wrapper
- Compatible with existing SecureCredential model
- Integrates with existing AuditLogger
- Reuses existing terminal UI components (Rich)

### NFR-6: Maintainability

**Code Organization:**
- Clear separation between local and remote mode code
- Remote mode components in dedicated directories
- Minimal modifications to existing codebase
- Conditional imports avoid loading unused code
- Shared components properly abstracted

**Testing:**
- Unit tests for PAKE protocol correctness
- Unit tests for encryption/decryption with PAKE-derived keys
- Integration tests for two-process communication
- End-to-end tests for complete flow
- Security tests validating encryption
- All tests automated and repeatable

**Documentation:**
- Inline code comments explain PAKE protocol steps
- API endpoint documentation with examples
- Message format specification documented
- Architecture decisions recorded with rationale
- Learning resources for PAKE concepts included

## API Endpoints Specification

### POST /pairing/initiate
**Purpose:** Agent requests pairing code generation

**Request:**
```json
{
  "agent_id": "flight-booking-001",
  "agent_name": "Flight Booking Agent"
}
```

**Response:**
```json
{
  "pairing_code": "847293",
  "expires_at": "2025-10-29T00:05:00Z"
}
```

**Notes:**
- Pairing code generated with `secrets.randbelow(900000) + 100000`
- Code expires after 5 minutes
- Code stored server-side awaiting user entry

### POST /pairing/exchange
**Purpose:** Execute PAKE protocol message exchange

**Request (Agent → Server):**
```json
{
  "pairing_code": "847293",
  "pake_message": "<PAKE protocol message from agent>"
}
```

**Response (Server → Agent):**
```json
{
  "session_id": "sess_abc123",
  "pake_message": "<PAKE protocol response from server>",
  "agent_id": "flight-booking-001"
}
```

**Notes:**
- CRITICAL: This endpoint executes actual PAKE protocol
- Agent and server exchange PAKE protocol messages
- Both sides independently derive session key from PAKE
- Session key never appears in request or response
- After this exchange, both sides have identical PAKE-derived key

### POST /credential/request
**Purpose:** Agent requests credential for specific domain

**Request:**
```json
{
  "session_id": "sess_abc123",
  "encrypted_payload": "<encrypted JSON with PAKE-derived key>"
}
```

**Encrypted Payload Structure (before encryption):**
```json
{
  "domain": "aa.com",
  "reason": "Logging in to search and book flights",
  "timestamp": "2025-10-29T00:00:00Z",
  "nonce": "a1b2c3d4e5f6"
}
```

**Response (Approved):**
```json
{
  "status": "approved",
  "encrypted_payload": "<encrypted credential JSON with PAKE-derived key>"
}
```

**Encrypted Response Payload (before encryption):**
```json
{
  "username": "user@example.com",
  "password": "secretpass",
  "timestamp": "2025-10-29T00:00:05Z",
  "nonce": "f6e5d4c3b2a1"
}
```

**Response (Denied):**
```json
{
  "status": "denied",
  "error": "User denied credential access"
}
```

**Notes:**
- All credentials encrypted with PAKE-derived session key
- Timestamps prevent replay attacks (reject if >5 min old)
- Nonces must be unique per request/response

### POST /session/revoke
**Purpose:** User revokes agent session

**Request:**
```json
{
  "session_id": "sess_abc123"
}
```

**Response:**
```json
{
  "revoked": true,
  "session_id": "sess_abc123"
}
```

**Notes:**
- Immediate effect (next request from agent fails)
- Session data deleted from server

### GET /session/status
**Purpose:** Agent checks session validity

**Request:**
```
GET /session/status?session_id=sess_abc123
```

**Response:**
```json
{
  "active": true,
  "last_access": "2025-10-29T00:00:00Z",
  "expires_at": "2025-10-29T00:30:00Z"
}
```

**Notes:**
- Used by agent for health checking
- Returns 404 if session not found or expired

### GET /health
**Purpose:** Server health check

**Request:**
```
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "active_sessions": 2
}
```

## Message Encryption Specification

**Encryption Method:**
- Use PAKE-derived session key for all encryption
- Symmetric encryption (Fernet recommended for simplicity)
- Session key derived from PAKE protocol execution (never transmitted)

**Encrypted Message Structure:**
```python
# Plaintext structure
plaintext = {
    "data": {...},  # Actual payload
    "timestamp": "ISO-8601 timestamp",
    "nonce": "unique random value"
}

# Encryption process
import json
from cryptography.fernet import Fernet

# PAKE-derived key converted to Fernet key format
fernet_key = base64.urlsafe_b64encode(pake_derived_key[:32])
cipher = Fernet(fernet_key)

# Encrypt
plaintext_bytes = json.dumps(plaintext).encode('utf-8')
encrypted = cipher.encrypt(plaintext_bytes)
encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
```

**Decryption Process:**
```python
# Decrypt
encrypted_bytes = base64.b64decode(encrypted_b64)
plaintext_bytes = cipher.decrypt(encrypted_bytes)
plaintext = json.loads(plaintext_bytes.decode('utf-8'))

# Validate
assert time_difference(plaintext['timestamp'], now()) < 5 * 60  # 5 min
assert plaintext['nonce'] not in seen_nonces
```

## Component Breakdown

### New Components (Remote Mode)

1. **PAKEHandler** (`src/sdk/pake_handler.py`)
   - Wraps chosen PAKE library (python-spake2 recommended)
   - Generates pairing codes (6-digit random)
   - Executes client-side PAKE protocol
   - Executes server-side PAKE protocol
   - Derives session keys from PAKE protocol
   - Provides encryption/decryption using PAKE-derived keys

2. **ApprovalServer** (`src/server/approval_server.py`)
   - HTTP/WebSocket server (Flask or FastAPI)
   - Implements API endpoints
   - Executes server-side PAKE protocol during pairing
   - Manages active sessions with PAKE-derived keys
   - Routes credential requests to approval UI
   - Encrypts/decrypts messages with PAKE-derived keys

3. **ApprovalClient** (`src/approval_client.py`)
   - Terminal UI for user interaction
   - Collects pairing codes from user
   - Displays credential request details
   - Handles approval/denial decisions
   - Accesses Bitwarden vault (reuses BitwardenAgent logic)
   - Manages session revocation

4. **CredentialSDK** (`src/sdk/credential_client.py`)
   - Agent-side client library
   - Initiates pairing (executes client-side PAKE)
   - Sends encrypted credential requests
   - Receives and decrypts responses
   - Handles session lifecycle
   - Provides simple API for agents

5. **PairingManager** (`src/server/pairing_manager.py`)
   - Tracks active pairings and sessions
   - Validates pairing codes
   - Executes server-side PAKE protocol
   - Manages PAKE-derived session keys
   - Handles session timeouts and revocation

### Modified Components

6. **main.py**
   - Add `--mode` flag (local/remote)
   - Conditional initialization based on mode
   - Mode-specific error handling

7. **FlightBookingAgent** (or agent base class)
   - Accept credential source (SDK client or direct BitwardenAgent)
   - Abstract credential retrieval interface
   - Support both local and remote modes

### Reused Components (No Changes)

8. **BitwardenCLI** - Vault access wrapper
9. **SecureCredential** - Credential data model
10. **AuditLogger** - Logging for both modes
11. **CredentialRequest/Response** - Request models

## Data Flow Diagrams

### Local Mode (Existing)
```
┌─────────────────┐
│ FlightAgent     │
└────────┬────────┘
         │ (direct call)
┌────────▼────────┐
│ BitwardenAgent  │
└────────┬────────┘
         │ (direct call)
┌────────▼────────┐
│ BitwardenCLI    │
└────────┬────────┘
         │ (subprocess)
┌────────▼────────┐
│ Bitwarden Vault │
└─────────────────┘
```

### Remote Mode (New)
```
Agent Process (Terminal 1)          Approval Client (Terminal 2)
┌─────────────────┐                 ┌──────────────────┐
│ FlightAgent     │                 │ ApprovalUI       │
└────────┬────────┘                 └────────┬─────────┘
         │                                   │
┌────────▼────────┐                 ┌───────▼──────────┐
│ CredentialSDK   │◄────Network────►│ ApprovalServer   │
│ (PAKE Client)   │   (encrypted)   │ (PAKE Server)    │
└────────┬────────┘                 └───────┬──────────┘
         │                                   │
┌────────▼────────┐                 ┌───────▼──────────┐
│ PAKEHandler     │◄────PAKE────────┤ PairingManager   │
│ (session key)   │   Protocol      │ (session key)    │
└─────────────────┘                 └───────┬──────────┘
                                            │
                                    ┌───────▼──────────┐
                                    │ BitwardenCLI     │
                                    └───────┬──────────┘
                                            │
                                    ┌───────▼──────────┐
                                    │ Bitwarden Vault  │
                                    └──────────────────┘
```

### PAKE Pairing Flow
```
Agent (Terminal 1)              Approval Server (Terminal 2)
      │                                  │
      │ 1. Generate pairing code         │
      ├────────────────────────────────► │
      │    (847293)                      │
      │                                  │
      │         [User enters code]       │
      │                                  │
      │ 2. PAKE Protocol Exchange        │
      │ ◄────────────────────────────────┤
      │    (PAKE messages, not keys!)    │
      │                                  │
      │ 3. Both derive session key       │
      │    (locally, independently)      │
      │    Key NEVER transmitted!        │
      ▼                                  ▼
[Session Key A]  <-- MATCH -->  [Session Key B]
```

### Credential Request Flow
```
Agent                        Approval Server
  │                                │
  │ 1. Encrypt request with        │
  │    PAKE-derived key            │
  ├──────────────────────────────► │
  │    {encrypted_payload}         │
  │                                │
  │                                │ 2. Decrypt with
  │                                │    PAKE-derived key
  │                                │
  │                                │ 3. Display request
  │                                │    to user
  │                                │
  │                                │ 4. User approves,
  │                                │    unlocks vault
  │                                │
  │                                │ 5. Encrypt response
  │                                │    with PAKE-derived key
  │ ◄──────────────────────────────┤
  │    {encrypted_payload}         │
  │                                │
  │ 6. Decrypt with                │
  │    PAKE-derived key            │
  ▼                                ▼
[Credential]                  [Vault locked]
```

## Dependencies

### Existing Dependencies (Reused)
- Python 3.8+
- Playwright (browser automation)
- Bitwarden CLI (vault access)
- Rich (terminal UI)
- cryptography (for Fernet encryption)

### New Dependencies (Required)
- **PAKE Library** (choose one):
  - `python-spake2` (RECOMMENDED - simple, pure Python)
  - `pysrp` (SRP protocol, well-tested)
  - `opaque-cloudflare` (modern, more complex)
- **HTTP Server** (choose one):
  - Flask (simple, synchronous)
  - FastAPI (async, modern, requires uvicorn)
- **Optional:**
  - `websockets` or `Flask-SocketIO` (if WebSocket support desired)

### Dependency Rationale

**Why python-spake2 is recommended:**
- Pure Python implementation (easier to understand for learning)
- SPAKE2 is simpler than OPAQUE (good for educational POC)
- Well-documented protocol
- Active maintenance
- Clear API for client/server sides

**Why Flask is recommended:**
- Simpler than FastAPI for this use case
- Synchronous model easier to reason about
- No async complexity for POC
- Smaller learning curve
- Built-in development server

## Constraints

### Technical Constraints
- Must use Python (no additional languages)
- Must work with existing Bitwarden CLI approach
- Cannot modify existing local mode code paths
- **MUST implement actual PAKE protocol** (not password hashing)
- **MUST NOT use PBKDF2/scrypt/Argon2 alone as substitute for PAKE**
- Localhost deployment only (no remote network required)
- Single machine, two-process architecture

### Security Constraints
- PAKE protocol must demonstrate mutual authentication
- PAKE protocol must derive keys without transmitting pairing code
- Must use established PAKE library (not custom crypto)
- Production-grade hardening may be simplified (acceptable for POC)
- Core PAKE protocol execution must be authentic (not simulated)

### Educational Constraints (Unique to This Project)
- **NO shortcuts that bypass PAKE learning objective**
- **NO "simplified simulation" that skips key exchange protocol**
- **YES to taking extra time to understand PAKE correctly**
- **YES to iteration and experimentation with PAKE**
- **YES to extensive testing of PAKE correctness**

### Business/Timeline Constraints
- Build on existing working POC (don't start from scratch)
- **NO hard deadline** - quality over speed
- Take whatever time needed for proper PAKE implementation
- Must not break existing local mode functionality
- Focus on correctness, not rushing to completion
- Learning from implementation challenges is valuable

## Out of Scope

### Explicitly Out of Scope
- Multi-user support (reason: single-user POC)
- Production-grade error recovery (reason: POC scope)
- Actual remote deployment across networks (reason: localhost only)
- GUI approval client (reason: terminal-based sufficient)
- Noise protocol on top of PAKE (reason: PAKE alone demonstrates concept)
- Browser extension approval UI (reason: terminal-based sufficient)
- Cloud deployment infrastructure (reason: localhost only)
- Forward secrecy (reason: beyond PAKE basics for POC)
- Formal security proofs (reason: educational POC, not production)
- Advanced CPAKE features (composability, parallel sessions)

### May Add Later (Post-MVP)
- WebSocket support for real-time notifications
- Multiple concurrent agents (if time permits)
- Session timeout configuration
- Persistent pairing (survives restart)
- GUI approval client
- Multiple credentials per session

## Acceptance Criteria Summary

### Must Pass (Definition of Done)
1. ✅ Local mode works: `python -m src.main --mode local` succeeds
2. ✅ Remote mode starts: Approval server runs in separate terminal
3. ✅ Pairing works: Agent generates code, user enters, PAKE protocol executes
4. ✅ PAKE keys match: Both sides derive identical key (verified in tests)
5. ✅ Session established: Shared secret logged (but not the key value)
6. ✅ Credential request: Agent requests aa.com credential
7. ✅ Approval prompt: Approval client shows request to user
8. ✅ User approves: Approval collected in approval terminal
9. ✅ Encryption works: Credential encrypted with PAKE-derived key and transmitted
10. ✅ Agent receives: Credential decrypted using PAKE-derived key
11. ✅ Login succeeds: Agent successfully logs into aa.com
12. ✅ No plaintext: Credentials not visible in network traffic logs
13. ✅ Documentation: Both modes explained clearly in README

### PAKE-Specific Acceptance Criteria (Critical)
1. ✅ PAKE protocol messages exchanged (not just keys transmitted)
2. ✅ Session keys derived through protocol execution (not hashed from password)
3. ✅ Pairing code never transmitted in plaintext over network
4. ✅ Both sides independently derive identical session key
5. ✅ Protocol demonstrates mutual authentication
6. ✅ Implementation uses established PAKE library (python-spake2 or similar)
7. ✅ Tests validate PAKE correctness (not just encryption)

## Risk Flags

### High Priority Risks
1. **PAKE implementation complexity** - First-time PAKE implementation may take longer than expected
2. **Library selection** - Choosing wrong PAKE library could require restart
3. **Backward compatibility** - Risk of breaking existing local mode
4. **Two-process testing** - More complex test infrastructure required

### Medium Priority Risks
1. **Network reliability** - Even localhost can have issues
2. **Session management** - Timeout/revocation edge cases
3. **Error handling** - Network errors harder to test than local errors
4. **Performance** - Encryption overhead may exceed targets

### Low Priority Risks
1. **UI consistency** - Keeping two terminals in sync
2. **Documentation** - Explaining both modes clearly
3. **Platform compatibility** - Localhost networking differences

See `risk_analysis.md` for detailed risk assessment.

## References

**PAKE Protocols:**
- SPAKE2: Simple Password-Authenticated Key Exchange
- OPAQUE: Modern asymmetric PAKE
- SRP: Secure Remote Password protocol
- CPace: Efficient PAKE with composability

**Python PAKE Libraries:**
- python-spake2: https://pypi.org/project/spake2/
- pysrp: https://pypi.org/project/srp/
- opaque-cloudflare: https://github.com/cloudflare/opaque-ts

**CPAKE Paper:**
- https://eprint.iacr.org/2020/886.pdf
- Composable Password-Authenticated Key Exchange

**Similar Patterns:**
- OAuth 2.0 Device Flow (pairing code UX)
- SSH agent forwarding (remote credential concept)
- Bitwarden browser extension (approval flow pattern)

## Next Steps for Architecture Phase

1. **Select PAKE library** - Research and choose between python-spake2, pysrp, opaque
2. **Select HTTP framework** - Choose Flask vs. FastAPI
3. **Design message protocol** - Specify exact message formats
4. **Design PAKE integration** - Detail how PAKE fits into pairing flow
5. **Design error handling** - Network failures, timeouts, retries
6. **Design testing strategy** - Two-process test infrastructure
7. **Design component interfaces** - Clear contracts between components
8. **Create architecture diagrams** - Component relationships, data flows
9. **Specify file structure** - Where new components live in codebase
10. **Plan implementation phases** - Break work into manageable stages

## Questions for Architect

1. **PAKE Library:** python-spake2 (simple), pysrp (proven), or opaque-cloudflare (modern)?
2. **HTTP Framework:** Flask (simple) or FastAPI (async)?
3. **WebSocket Support:** Worth the complexity for credential approval notifications?
4. **Session Persistence:** In-memory (simple) or file-based (survives restart)?
5. **Pairing Code Format:** 6-digit (user-friendly) or 8-character (more secure)?
6. **Message Transport:** HTTP polling or WebSocket push?
7. **Error Recovery:** How aggressive should retry logic be?
8. **Testing Infrastructure:** How to automate two-process testing?
