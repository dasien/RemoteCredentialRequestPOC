---
slug: remote-credential-access
status: NEW
created: 2025-10-28
author: Development Team
priority: high
timeline: flexible - quality over speed
---

# Enhancement: Remote Credential Access with CPAKE/PAKE Implementation

## Project Philosophy

**This is an educational/learning project with no hard deadline.**

**Priorities (in order):**
1. **Educational value** - Actually implement and understand PAKE protocols
2. **Correctness** - Proper PAKE implementation, not shortcuts
3. **Quality** - Well-tested, well-documented code
4. **Speed** - Take whatever time is needed

**Timeline Approach:**
- No rushing or corner-cutting
- Each phase completes when it's done properly
- PAKE integration gets whatever time it needs (research, testing, iteration)
- Learning from implementation issues is part of the value

**For All Agents:** When you see timeline pressure or suggestions to "simplify for speed," reject them. The goal is to learn PAKE properly, not to deliver quickly.

**Expected Outcomes:**
- Deep understanding of how PAKE protocols work
- Working implementation of PAKE-based remote credential access
- Well-documented code that others can learn from
- Confidence in the security properties PAKE provides

**Unexpected delays are acceptable** if they lead to better understanding or more correct implementation. Research time, experimentation, and iterative refinement are all valuable.

## Overview
**Goal:** Extend the existing credential-request POC to support a remote/distributed architecture that simulates CPAKE-based agent pairing and secure credential delivery over a network boundary.

**User Story:**
As a user, I want to demonstrate how AI agents running on remote machines can securely request credentials from my local Bitwarden client with pairing-based authentication, so that stakeholders can understand the production architecture for distributed agent systems.

## Context & Background
**Current State:**
- Working POC (`credential-request-use`) that demonstrates local credential access
- FlightBookingAgent and BitwardenAgent run in same process
- Direct CLI access to Bitwarden vault
- Credentials passed via Python object references (in-memory)
- Successfully logs into aa.com with human-in-the-loop approval

**CRITICAL EDUCATIONAL GOAL:**
This enhancement's primary purpose is to **implement and understand CPAKE/PAKE protocols**. The point is NOT to build the simplest possible POC, but rather to learn how password-authenticated key exchange actually works by implementing it.

**What "POC" means for this project:**
- POC = Proof of Concept **for CPAKE/PAKE implementation**
- NOT POC = "minimum viable demo with shortcuts"
- The educational value comes from actually implementing the PAKE protocol
- Simplified alternatives (like PBKDF2) defeat the purpose

## Understanding CPAKE/PAKE (For All Agents)

**What PAKE (Password-Authenticated Key Exchange) Is:**

PAKE is a cryptographic protocol where two parties can:
1. **Mutually authenticate** using only a shared password/code
2. **Derive a shared session key** for encryption
3. **WITHOUT transmitting the password** over the network
4. **Resist offline attacks** - intercepted messages don't enable password guessing

**How PAKE Differs from Simple Password Hashing:**

❌ **NOT PAKE (What we don't want):**
```python
# Simple password hashing - NOT PAKE
shared_key = PBKDF2(password, salt)
send_over_network(shared_key)  # Key transmitted
# Problem: Vulnerable to interception, no mutual auth
```

✅ **ACTUAL PAKE (What we do want):**
```python
# Client side
client = SPAKE2_A(password)
client_msg = client.start()
send_to_server(client_msg)  # Safe to transmit
server_msg = receive_from_server()
client_key = client.finish(server_msg)

# Server side  
server = SPAKE2_B(password)
server_msg = server.start()
send_to_client(server_msg)  # Safe to transmit
client_msg = receive_from_client()
server_key = server.finish(client_msg)

# Result: client_key == server_key
# Neither password nor keys were ever transmitted!
```

**Key Properties We Must Demonstrate:**
1. **Password never sent** - Pairing code stays on both terminals
2. **Mutual authentication** - Both sides prove they know the code
3. **Key derivation** - Session key comes from protocol execution, not hashing
4. **Message exchange** - Client and server exchange protocol messages

**Acceptable PAKE Protocols for This POC:**
- **SPAKE2** (Recommended) - Simple, good Python library (python-spake2)
- **OPAQUE** - Modern, but more complex
- **SRP (Secure Remote Password)** - Older but proven, good library (pysrp)
- **CPace** - Efficient, may require more research

**NOT Acceptable:**
- ❌ PBKDF2 alone (password hashing, not PAKE)
- ❌ Scrypt alone (password hashing, not PAKE)
- ❌ Argon2 alone (password hashing, not PAKE)
- ❌ Any approach that transmits derived keys
- ❌ "Simplified simulation" that skips the key exchange protocol

**Why This Matters:**
The Bitwarden Remote Credential Access document specifically mentions CPAKE because it provides security properties that simple password hashing cannot:
- Protection against man-in-the-middle attacks
- No certificate/PKI required
- Mutual authentication (both sides verified)
- Forward secrecy potential (with proper implementation)

**Technical Context:**
- Build upon existing working POC in AgentCredentialRequest/
- Add "remote mode" alongside existing "local mode"
- Two-process architecture (agent process + approval client process)
- **CRITICAL: Implement actual CPAKE or PAKE protocol** - this is an educational/demonstration POC to learn how password-authenticated key exchange works
- Use SPAKE2, OPAQUE, SRP, or similar PAKE protocol (NOT simple PBKDF2 hashing)
- HTTP or WebSocket for transport layer (network boundary)
- PAKE protocol handles mutual authentication and session key derivation

**Dependencies:**
- Existing credential-request-use POC (fully functional)
- Python 3.8+ with async support
- **PAKE protocol library:** python-spake2, opaque-cloudflare, pysrp, or architect's choice
- Flask or FastAPI for approval server
- cryptography library (for any additional encryption needs beyond PAKE)
- Optional: WebSocket library (websockets or socket.io) for real-time communication
- All existing dependencies (Playwright, Bitwarden CLI, Rich)

## Requirements

### Functional Requirements
1. **Dual-Mode Operation**: System must support both local mode (existing) and remote mode (new)
2. **Agent Pairing**: Agent must generate pairing code that user enters in approval client to establish trust
3. **Approval Server**: Separate process runs approval server that handles credential requests from remote agents
4. **Encrypted Communication**: Credential requests and responses must be encrypted using shared secret derived from pairing
5. **User Approval UI**: Approval client must present credential requests and collect user approval/denial
6. **Credential Delivery**: Approved credentials must be encrypted and delivered to agent over network
7. **Session Management**: Pairing establishes a session; session can be revoked by user
8. **Backward Compatibility**: Local mode (existing POC) must continue to work unchanged

### Non-Functional Requirements
- **Security:** Pairing codes one-time use; shared secrets derive from pairing; credentials encrypted in transit
- **Performance:** Credential request roundtrip <5 seconds (local network)
- **Reliability:** Handle network failures, disconnections, timeout gracefully
- **Usability:** Clear separation between agent terminal and approval client terminal
- **Compatibility:** Works on macOS, Linux, Windows (localhost networking)

### Must Have (MVP)
- [ ] Pairing flow: Agent generates code, user enters in approval client
- [ ] Shared secret derivation from pairing code (PBKDF2 or similar)
- [ ] Approval server (HTTP or WebSocket) handling credential requests
- [ ] Encrypted credential request message format
- [ ] Encrypted credential response with approved credentials
- [ ] User approval UI in approval client (similar to current BitwardenAgent prompts)
- [ ] Agent SDK client for remote credential requests
- [ ] Vault access in approval client (using existing BitwardenCLI wrapper)
- [ ] Session revocation (user can terminate agent access)
- [ ] --mode flag: `--mode local` (existing) or `--mode remote` (new)

### Should Have (if time permits)
- [ ] WebSocket support for real-time notifications (vs. polling)
- [ ] Multiple concurrent agent support (approval client handles multiple agents)
- [ ] Session timeout (pairing expires after X minutes)
- [ ] Persistent pairing (survives process restart)
- [ ] GUI approval client (instead of terminal-based)
- [ ] Multiple credential requests per session

### Won't Have (out of scope)
- Multi-user support (reason: single-user POC)
- Production-grade error recovery (reason: POC scope)
- Actual remote deployment across networks (reason: localhost simulation only)
- GUI approval client (reason: terminal-based sufficient)
- Noise protocol on top of PAKE (reason: PAKE alone demonstrates the concept)
- Browser extension approval UI (reason: terminal-based sufficient)
- Cloud deployment infrastructure (reason: localhost only)

## Open Questions
> These need answers before architecture review

1. **Communication protocol:** HTTP with polling, WebSocket for bidirectional, or both? Which provides better UX for credential request/approval flow?
2. **Pairing storage:** Should pairing persist across restarts or be session-only?
3. **Shared secret derivation:** Use PBKDF2, scrypt, or Argon2 for key derivation from pairing code?
4. **Encryption approach:** Use Fernet (symmetric), or simulate asymmetric with key exchange?
5. **Server framework:** Flask (simpler), FastAPI (async-native), or plain HTTP server?
6. **Approval client UI:** Terminal-based (Rich), web-based (Flask + browser), or both?
7. **Process coordination:** How should user start both processes? Shell script, or manual two-terminal approach?
8. **Credential caching:** Should agent cache credentials for session duration or request each time?

## Constraints & Limitations
**Technical Constraints:**
- Must use Python (no additional languages)
- Must work with existing Bitwarden CLI approach
- Cannot modify existing local mode code (backward compatibility)
- **MUST implement actual PAKE protocol (SPAKE2, OPAQUE, SRP, or CPace)**
- **MUST NOT use simple password hashing as a shortcut (PBKDF2, scrypt, Argon2 alone do not constitute PAKE)**
- Localhost deployment only (no actual remote network required)

**Security Constraints:**
- PAKE protocol must demonstrate mutual authentication (both sides prove knowledge of pairing code)
- PAKE protocol must derive session keys without transmitting the pairing code
- Implementation must be based on established PAKE protocol (not custom crypto)
- Using a Python PAKE library is preferred over implementing from scratch (unless educational value dictates otherwise)
- Production-grade hardening may be simplified (error handling, edge cases), but the core PAKE protocol execution must be authentic

**Business/Timeline Constraints:**
- Build on existing working POC (don't start from scratch)
- **No hard deadline** - Quality and educational value prioritized over speed
- Take whatever time needed to properly implement PAKE protocol
- Must not break existing local mode functionality
- Focus on demonstrating concept correctly, not rushing to completion

## Success Criteria
**Definition of Done:**
- [ ] Local mode still works (`python -m src.main --mode local`)
- [ ] Remote mode starts approval server in separate terminal
- [ ] Agent generates pairing code and displays to user
- [ ] User enters pairing code in approval client
- [ ] Pairing establishes shared secret (logged but not the secret value)
- [ ] Agent requests credential for aa.com
- [ ] Approval client shows request and prompts user
- [ ] User approves in approval client terminal
- [ ] Credential encrypted and sent to agent
- [ ] Agent receives and decrypts credential
- [ ] Agent successfully logs into aa.com
- [ ] Credentials not visible in network traffic (encrypted)
- [ ] Documentation explains both modes

**Acceptance Tests:**
1. **Local Mode Regression:** Given existing POC, when run with `--mode local`, then works exactly as before
2. **Pairing Flow:** Given agent started in remote mode, when user enters pairing code in approval client, then shared secret established and logged
3. **Remote Credential Request:** Given paired agent, when agent requests credential, then approval client shows request in its terminal
4. **User Approval Remote:** Given credential request displayed, when user approves in approval client, then credential encrypted and delivered to agent terminal
5. **Encrypted Delivery:** Given credential response, when inspecting network traffic (logs), then credential values not visible in plaintext
6. **Login Success Remote:** Given credential received remotely, when agent uses to login, then aa.com login succeeds
7. **Session Revocation:** Given active pairing, when user revokes in approval client, then agent credential requests fail

## Security & Safety Considerations
**Critical Security Note:** This is a **simulation** for demonstration purposes. The security model is simplified:

- **Pairing code security:** 6-digit code is weak (real CPAKE uses stronger methods)
- **Key derivation:** PBKDF2 is simpler than actual CPAKE protocol
- **Encryption:** Fernet is symmetric (real CPAKE derives keys differently)
- **Network security:** Localhost only (no TLS needed for demo)
- **Session management:** Basic timeout (no advanced revocation mechanisms)

**What This Demonstrates:**
- ✅ Concept of agent pairing with user approval
- ✅ Credential encryption in transit
- ✅ Separation between agent and vault access
- ✅ Human-in-the-loop approval in distributed system

**What This Doesn't Provide:**
- ❌ Production-grade CPAKE implementation
- ❌ Forward secrecy (real CPAKE/Noise provides this)
- ❌ Resistance to sophisticated attacks
- ❌ Secure remote deployment

**Security Requirements:**
- Pairing code must be one-time use (prevent replay)
- Shared secret must not be logged
- Credentials must be encrypted before network transmission
- Pairing must expire after timeout
- User must be able to revoke agent access
- Audit log must show pairing and request events

## UI/UX Considerations

### Agent Terminal (Process A)
```
=== AI Agent Credential Request POC (Remote Mode) ===
Starting agent in remote mode...
Approval server: http://localhost:5000

╔════════════════════════════════════════╗
║         Agent Pairing Required         ║
╟────────────────────────────────────────╢
║ Enter this code in approval client:    ║
║                                        ║
║            847293                      ║
║                                        ║
║ Waiting for user to approve pairing... ║
╚════════════════════════════════════════╝

✓ Pairing successful! Session established.

Starting flight booking agent...
Requesting credentials for aa.com...
⏳ Waiting for user approval in approval client...
✓ Credentials received (encrypted)
Logging into aa.com...
✓ Login successful!
```

### Approval Client Terminal (Process B)
```
=== Bitwarden Credential Approval Client ===
Starting approval server on http://localhost:5000

Enter pairing code from agent: 847293
✓ Agent paired: Flight Booking Agent (flight-booking-001)

╔════════════════════════════════════════════════╗
║      🔐 Credential Access Request              ║
╟────────────────────────────────────────────────╢
║ Agent: Flight Booking Agent                    ║
║ Domain: aa.com                                 ║
║ Reason: Logging in to search and book flights  ║
║                                                ║
║ Allow this agent to access your credentials?   ║
║                                                ║
║ [Y] Approve    [N] Deny    [R] Revoke Session  ║
╚════════════════════════════════════════════════╝

Decision: Y

Enter Bitwarden vault password: ********
✓ Credentials retrieved and sent to agent (encrypted)

[Active Sessions]
• Flight Booking Agent (flight-booking-001) - Last access: 2s ago
  [R] Revoke
```

## Testing Strategy
**Unit Tests:**
- Pairing code generation and validation
- Shared secret derivation (deterministic)
- Encryption/decryption of credential messages
- Approval server request handling (mocked)
- Agent SDK client (mocked server responses)

**Integration Tests:**
- Two-process pairing flow (agent + approval client)
- Credential request/response roundtrip
- Encrypted message validation
- Session revocation
- Network failure handling

**Security Tests:**
- Verify credentials encrypted in message payloads
- Verify shared secret not logged
- Verify pairing code one-time use
- Verify session revocation terminates access

**Manual Test Scenarios:**
1. Start approval client, then agent → Enter pairing code → Request credential → Approve → Login succeeds
2. Start agent without approval client → Pairing fails with clear error
3. Start approval client → Agent pairs → User denies credential request → Agent handles gracefully
4. Active session → User revokes in approval client → Agent's next request fails

## References & Research
**CPAKE Protocol:**
- CPAKE paper: https://eprint.iacr.org/2020/886
- Concept: Composable Password-Authenticated Key Exchange
- Goal: Mutual authentication without PKI

**Noise Protocol:**
- Framework for secure communication patterns
- Provides forward secrecy
- Used in WireGuard, WhatsApp, etc.

**Simplified Approaches for POC:**
- PBKDF2 for key derivation (Python's hashlib)
- Fernet for symmetric encryption (cryptography library)
- HMAC for message authentication

**Similar Systems:**
- SSH agent protocol (agent forwarding concept)
- OAuth device flow (pairing code UX pattern)
- Bitwarden browser extension (approval flow pattern)

## Implementation Approach

### Architecture Pattern
**Layered Remote Architecture:**
```
Agent Process (A)               Approval Client Process (B)
┌─────────────────┐            ┌──────────────────────┐
│ FlightAgent     │            │ ApprovalUI           │
└────────┬────────┘            └──────────┬───────────┘
         │                                 │
┌────────▼────────┐            ┌──────────▼───────────┐
│ CredentialSDK   │◄──Network─►│ ApprovalServer       │
│ (Client)        │            │ (HTTP/WebSocket)     │
└────────┬────────┘            └──────────┬───────────┘
         │                                 │
┌────────▼────────┐            ┌──────────▼───────────┐
│ SimplePAKE      │◄─Pairing──►│ PairingManager       │
│ (Encryption)    │            │ (Key Derivation)     │
└─────────────────┘            └──────────┬───────────┘
                                          │
                               ┌──────────▼───────────┐
                               │ BitwardenCLI         │
                               │ (Vault Access)       │
                               └──────────────────────┘
```

### Data Flow (Remote Mode)
```
1. User starts approval client
   → Approval server listens on http://localhost:5000

2. User starts agent with --mode remote
   → Agent generates pairing code: "847293"
   → Agent displays: "Enter code in approval client"

3. User enters "847293" in approval client
   → PAKE protocol execution begins:
     • Client creates PAKE instance with pairing code
     • Client generates and sends first protocol message
     • Server receives message, creates PAKE instance with same code
     • Server generates and sends response message
     • Both sides complete PAKE protocol
     • Both independently derive same session key
   → Session established with PAKE-derived key

4. Agent requests credential
   → encrypted_request = encrypt_with_pake_key({domain: "aa.com", reason: "..."})
   → POST /credential/request {encrypted: encrypted_request}
   → Approval server decrypts using PAKE-derived session key

5. Approval client prompts user
   → User approves + enters vault password
   → Approval client unlocks vault, retrieves credential
   → encrypted_response = encrypt_with_pake_key({username: "...", password: "..."})
   → Returns to agent

6. Agent receives encrypted response
   → Decrypts using PAKE-derived session key
   → Uses credential to login to aa.com
```

### Component Breakdown

**New Components:**

1. **ApprovalServer** (`src/server/approval_server.py`)
   - HTTP server (Flask/FastAPI) handling /pairing and /credential endpoints
   - Manages active agent sessions
   - Routes requests to approval UI
   - Encrypts/decrypts messages using session keys

2. **ApprovalClient** (`src/approval_client.py`)
   - Terminal UI for user interaction
   - Collects pairing codes from user
   - Displays credential requests
   - Handles vault access (reuses BitwardenAgent logic)
   - Manages session revocation

3. **CredentialSDK** (`src/sdk/credential_client.py`)
   - Client-side SDK for agents
   - Initiates pairing
   - Sends encrypted credential requests
   - Receives and decrypts responses
   - Handles session management

4. **PAKEHandler** (`src/sdk/pake_handler.py`)
   - Wraps chosen PAKE library (python-spake2, pysrp, or architect's choice)
   - Pairing code generation (6-digit random)
   - PAKE protocol execution (client and server sides)
   - Session key derivation from PAKE protocol
   - Encryption/decryption using PAKE-derived keys
   - Session key management

5. **PairingManager** (`src/server/pairing_manager.py`)
   - Tracks active pairings
   - Validates pairing codes
   - Executes server-side PAKE protocol
   - Manages session timeouts
   - Handles revocation

**Modified Components:**

6. **main.py** - Add --mode flag, conditional initialization
7. **FlightBookingAgent** - Use SDK client in remote mode, BitwardenAgent in local mode

## Open Questions
> These need answers before architecture review

1. **Communication protocol:** HTTP with long-polling, WebSocket for push notifications, or Server-Sent Events? What provides best UX for credential approval notifications?
2. **Pairing code entropy:** 6-digit numeric (user-friendly), 8-character alphanumeric (more secure), or UUID (most secure)? Balance usability vs. security for demo.
3. **Shared secret algorithm:** PBKDF2 (simple), scrypt (better), or Argon2 (best)? Consider Python stdlib availability.
4. **Message format:** JSON with base64-encoded encryption, or binary protocol? JSON is easier to debug.
5. **Session persistence:** In-memory only (restarts require re-pairing), or file-based (survives restarts)? Which better demonstrates concept?
6. **Server framework:** Flask (simple, sync), FastAPI (async, modern), or http.server (stdlib only)? Consider async compatibility with Playwright.
7. **Multiple agents:** Support multiple paired agents simultaneously, or one at a time? Complexity vs. demonstration value.
8. **Network simulation:** Localhost only (127.0.0.1), or support actual LAN (192.168.x.x) for realistic demo?

## Constraints & Limitations
**Technical Constraints:**
- Must maintain backward compatibility with local mode
- Must use Python (no additional languages for server)
- Localhost networking only (no cloud deployment)
- Simplified CPAKE (not cryptographically equivalent to full CPAKE)
- Single machine deployment (simulate remote with two processes)
- Cannot break existing tests or functionality

**Security Constraints:**
- This is a **simulation** not production-grade CPAKE
- Pairing code transmitted in clear (acceptable for localhost)
- Shared secret derivation simplified (acceptable for demo)
- No forward secrecy (unlike real CPAKE + Noise)
- Accept these limitations for POC demonstration purposes

**Timeline Constraints:**
- No hard deadline - take time needed for quality implementation
- Learning PAKE properly is more important than speed
- Expect PAKE integration to take time (research, testing, iteration)
- Building on existing POC reduces overall effort
- Phased approach allows for learning and experimentation

## Success Criteria
**Definition of Done:**
- [ ] User can run approval client in one terminal
- [ ] User can run agent in remote mode in second terminal
- [ ] Pairing code displayed and accepted successfully
- [ ] Agent successfully requests credential over network
- [ ] Approval client displays request and collects approval
- [ ] Credential encrypted, transmitted, and decrypted successfully
- [ ] Agent logs into aa.com using remotely-retrieved credential
- [ ] User can revoke session from approval client
- [ ] Local mode continues to work (regression testing)
- [ ] README documents both modes with clear instructions
- [ ] Architecture diagram shows local vs. remote mode

**Acceptance Tests:**
1. **Dual Mode Operation:** Given `--mode local`, when POC runs, then uses existing direct approach (no network)
2. **Pairing Success:** Given approval client running, when agent starts with `--mode remote` and user enters pairing code, then session established and logged
3. **Remote Credential Request:** Given paired session, when agent requests credential, then approval client shows request within 2 seconds
4. **Remote Approval:** Given request displayed, when user approves in approval client, then credential delivered to agent within 5 seconds
5. **Encryption Validation:** Given credential transmitted, when inspecting server logs, then credential values not in plaintext
6. **Remote Login:** Given credential received remotely, when agent uses for login, then aa.com login succeeds
7. **Session Revocation:** Given active session, when user revokes in approval client, then agent's next request fails with "session revoked" error
8. **Local Mode Unchanged:** Given local mode, when running all existing tests, then all pass unchanged

## Security & Safety Considerations
**Threat Model for Remote Mode:**

**Attack Vectors:**
- Network eavesdropping on localhost (LOW risk - same machine)
- Pairing code interception (MEDIUM risk - brief exposure in terminals)
- Replay attacks on messages (MEDIUM risk - need nonces/timestamps)
- Session hijacking (LOW risk - localhost only, PAKE provides mutual auth)
- Man-in-the-middle (LOW risk - PAKE protocol resistant to MITM)

**Why PAKE Provides Security:**
- **No password transmission** - Pairing code never sent over network
- **Mutual authentication** - Both agent and server prove knowledge of code
- **MITM resistance** - Protocol designed to detect/prevent interception
- **Offline attack resistance** - Intercepted protocol messages don't enable brute force

**Security Requirements:**
- PAKE protocol must be implemented correctly per specification
- Pairing code must be one-time use only (prevent replay of PAKE exchange)
- Session keys from PAKE must be used for all subsequent encryption
- Message nonces/timestamps required to prevent replay attacks
- Sessions must timeout and be revocable
- Audit log must show pairing and request events

**What This Demonstrates:**
- ✅ Actual PAKE protocol execution (not simulation)
- ✅ Password-authenticated key exchange concepts
- ✅ Mutual authentication without certificates
- ✅ Secure session establishment
- ✅ Credential encryption with PAKE-derived keys

**What This Doesn't Provide (Acceptable for POC):**
- Advanced CPAKE features (composability, parallel sessions)
- Noise protocol on top of PAKE (forward secrecy)
- Production-grade implementation hardening
- Formal security proofs or audits
- Resistance to advanced cryptographic attacks

**Implementation Guidance:**
```python
# Example using python-spake2 library
from spake2 import SPAKE2_A, SPAKE2_B

# Agent (client) side:
pake_client = SPAKE2_A(pairing_code.encode())
outbound_msg = pake_client.start()
# Send outbound_msg to server

# Server (approval) side:
pake_server = SPAKE2_B(pairing_code.encode())  
outbound_msg = pake_server.start()
# Send outbound_msg to client

# Both receive each other's messages
client_key = pake_client.finish(server_msg)
server_key = pake_server.finish(client_msg)

# Keys match! Now use for encryption
# assert client_key == server_key
```

## UI/UX Considerations

### Starting the System (Remote Mode)
```bash
# Terminal 1: Start approval client first
cd AgentCredentialRequest
python -m src.approval_client

# Terminal 2: Start agent
cd AgentCredentialRequest
python -m src.main --mode remote --approval-server http://localhost:5000
```

### Pairing Flow UX
**Agent Terminal:**
```
╔═══════════════════════════════════════╗
║         Agent Pairing Required        ║
╟───────────────────────────────────────╢
║ Enter this code in approval client:   ║
║                                       ║
║              847293                   ║
║                                       ║
║ Waiting for pairing approval...       ║
║ (Times out in 300 seconds)            ║
╚═══════════════════════════════════════╝
```

**Approval Client Terminal:**
```
=== Bitwarden Credential Approval Client ===
Server started on http://localhost:5000

Enter pairing code from agent: 847293
Validating pairing code...
✓ Agent paired: Flight Booking Agent (flight-booking-001)

[Waiting for credential requests...]
```

### Credential Request Flow UX
**Agent Terminal:**
```
Requesting credentials for aa.com...
⏳ Waiting for approval... (request sent to approval client)
```

**Approval Client Terminal:**
```
╔═══════════════════════════════════════════════╗
║      🔐 Credential Access Request             ║
╟───────────────────────────────────────────────╢
║ Agent: Flight Booking Agent                   ║
║ Domain: aa.com                                ║
║ Reason: Logging in to search and book flights ║
║                                               ║
║ Allow this agent to access your credentials?  ║
║                                               ║
║ [Y] Approve    [N] Deny    [R] Revoke Session ║
╚═══════════════════════════════════════════════╝

Decision: Y
Enter Bitwarden vault password: ********
✓ Credentials sent to agent (encrypted)
```

**Then Agent Terminal:**
```
✓ Credentials received from approval client
Decrypting credentials...
Logging into aa.com...
✓ Login successful!
```

## Testing Strategy
**Unit Tests:**
- SimplePAKE: Test key derivation determinism
- SimplePAKE: Test encryption/decryption roundtrip
- PairingManager: Test pairing validation and expiry
- CredentialSDK: Test request serialization (mocked server)
- ApprovalServer: Test endpoint handlers (mocked approval)

**Integration Tests:**
- Two-process pairing flow (start both processes, complete pairing)
- Credential request roundtrip (request → approve → receive)
- Encrypted message validation (inspect payload, no plaintext)
- Session timeout (wait for timeout, verify request fails)
- Session revocation (revoke, verify request fails)

**End-to-End Tests:**
- Complete flow: Start approval client → Start agent → Pair → Request → Approve → Login to aa.com
- Local mode regression (ensure existing POC still works)

**Security Tests:**
- Network traffic inspection (log server requests, verify encryption)
- Pairing code reuse prevention (try same code twice)
- Shared secret exposure (grep logs for secret values)

**Manual Test Scenarios:**
1. **Happy Path Remote:**
   - Start approval client in Terminal 1
   - Start agent in remote mode in Terminal 2
   - Enter pairing code when prompted
   - Approve credential request when shown
   - Verify login succeeds
   - Check both terminals show appropriate messages

2. **Pairing Failure:**
   - Start agent without approval client
   - Verify clear error: "Cannot connect to approval server"
   - Start approval client
   - Retry agent, verify works

3. **User Denial Remote:**
   - Complete pairing
   - Agent requests credential
   - User denies in approval client
   - Agent receives denial and exits gracefully

4. **Session Revocation:**
   - Complete pairing
   - User revokes session in approval client
   - Agent attempts credential request
   - Agent receives "session revoked" error

## Notes for PM Subagent
> Instructions for processing this enhancement

- **No timeline pressure** - This is an educational project; quality and learning are more important than speed
- Validate that building on existing POC reduces risk and effort
- Confirm whether WebSocket adds enough educational/demonstration value over HTTP polling
- Consider whether pairing persistence is worth the complexity for learning PAKE
- **Do NOT pressure team to cut corners on PAKE implementation** - the learning value is in doing it properly
- If PAKE integration takes longer than expected, that's acceptable - it's complex cryptography
- Evaluate whether simplified CPAKE adequately demonstrates the concept for stakeholders (answer: actual PAKE is required)

## Notes for Architect Subagent
> Key architectural considerations

- **Critical:** Design must not break existing local mode (backward compatibility)
- **Communication protocol:** Evaluate HTTP polling vs. WebSocket for approval flow responsiveness
- **Shared secret derivation:** Choose algorithm available in Python stdlib (avoid external crypto libraries if possible)
- **Message format:** Design encrypted message envelope (metadata + encrypted payload)
- **Error handling:** Design remote error propagation (server errors, network failures, timeouts)
- **Session management:** Design pairing lifecycle (creation, timeout, revocation)
- **Code reuse:** Maximize reuse of existing BitwardenAgent, BitwardenCLI, SecureCredential
- **Testing:** Design for easy two-process testing (script to start both processes?)

## Notes for Implementer Subagent
> Implementation guidance

- **Reuse existing components:** BitwardenCLI, SecureCredential, AuditLogger (don't rewrite)
- **Conditional imports:** Use `if mode == "remote"` to avoid importing server components in local mode
- **Server framework:** If using Flask, keep it simple (no blueprints needed for 2 endpoints)
- **Encryption:** Use `cryptography.fernet.Fernet` (already in crypto library for Python)
- **Key derivation:** Use `hashlib.pbkdf2_hmac` (Python stdlib, no extra dependencies)
- **Testing:** Create `tests/remote/` for remote-mode-specific tests
- **Documentation:** Update README with clear two-terminal startup instructions
- **Error messages:** Network errors should guide user (e.g., "Is approval client running?")

## Notes for Testing Subagent
> Testing and validation guidance

- **PAKE correctness is top priority** - Validate that PAKE protocol executes correctly before testing other features
- **Regression testing critical** - All existing local mode tests must pass unchanged
- **Two-process testing infrastructure** - Create reusable fixtures for starting/stopping server in tests
- **Network testing:** Verify encrypted payloads (use server logs, not packet capture)
- **PAKE testing:** Verify both sides derive identical keys (compare key hashes), verify protocol messages safe to transmit
- **Security testing:** Verify encryption with test vectors, pairing code one-time use, credentials never in plaintext
- **Error scenarios:** Test with approval server not running, network timeout, invalid pairing codes, session expiry
- **Manual testing:** Two-terminal setup required for realistic validation
- **Performance:** Measure PAKE overhead separately from network latency
- **Take time for thorough testing** - Finding PAKE implementation bugs early is more valuable than quick testing

## Implementation Phases

### Phase 1: Foundation (Days 1-2)
**Goal:** Create basic two-process communication with actual PAKE protocol

**Deliverables:**
- PAKEHandler module using chosen library (python-spake2 recommended)
- PAKE protocol client and server wrappers
- Pairing code generation
- Basic approval server (Flask with /health endpoint)
- Basic CredentialSDK client (connect to server)
- Test PAKE key derivation (both sides derive same key)
- Test two-process communication (ping/pong)

**Validation:**
- [ ] Can generate and validate pairing codes
- [ ] Can execute PAKE protocol (client and server sides)
- [ ] Both sides derive identical session key from PAKE
- [ ] Can encrypt/decrypt test messages with PAKE-derived key
- [ ] Server starts and responds to /health
- [ ] Client can connect to server

### Phase 2: Pairing Flow (Days 3-4)
**Goal:** Implement agent pairing with actual PAKE protocol execution

**Deliverables:**
- PairingManager in approval server (executes server-side PAKE)
- Pairing endpoints (/pairing/initiate, /pairing/exchange)
- PAKE message exchange (client ↔ server protocol messages)
- ApprovalClient pairing UI
- CredentialSDK pairing client (executes client-side PAKE)
- Session tracking with PAKE-derived keys

**Validation:**
- [ ] Agent generates and displays pairing code
- [ ] User enters code in approval client
- [ ] PAKE protocol messages exchanged successfully
- [ ] Both sides derive identical session key (verify in logs without showing key)
- [ ] Session established with PAKE-derived encryption key
- [ ] Pairing code one-time use enforced
- [ ] Invalid codes rejected with clear error

### Phase 3: Credential Request Flow (Days 5-6)
**Goal:** Implement remote credential request/response using PAKE-derived session keys

**Deliverables:**
- Credential request endpoint (/credential/request)
- Message encryption/decryption using PAKE-derived keys in both client and server
- Approval UI for credential requests (reuse BitwardenAgent prompts)
- CredentialSDK request method
- Vault access in approval client

**Validation:**
- [ ] Agent encrypts credential request with PAKE-derived session key
- [ ] Approval client decrypts and displays request
- [ ] User approval collected in approval client
- [ ] Vault unlocked and credential retrieved
- [ ] Credential encrypted with PAKE-derived session key and returned to agent
- [ ] Agent decrypts credential using same PAKE-derived key
- [ ] aa.com login succeeds with remotely-retrieved credential
- [ ] Credentials never visible in plaintext in server logs

### Phase 4: Session Management & Polish (Day 7)
**Goal:** Add session management and polish UX

**Deliverables:**
- Session revocation endpoint
- Approval client session management UI
- Session timeout implementation
- --mode flag in main.py
- Updated README with both modes
- Regression testing for local mode

**Validation:**
- [ ] User can revoke active sessions
- [ ] Sessions timeout after inactivity
- [ ] Local mode still works (all existing tests pass)
- [ ] README clearly explains both modes
- [ ] Two-terminal startup documented

## Detailed Requirements

### Pairing Requirements

**PR-1: Pairing Code Generation**
- Generate random 6-digit numeric code (100000-999999)
- Code must be cryptographically random (secrets.randbelow)
- Code displayed to user with clear formatting
- Code expires after 5 minutes if not used

**PR-2: Pairing Code Validation**
- User enters code in approval client
- Server validates code exists and not expired
- Server validates code not already used (one-time use)
- Invalid code shows clear error message

**PR-3: PAKE Protocol Execution**
- Agent executes client-side PAKE protocol with pairing code
- Server executes server-side PAKE protocol with same pairing code
- PAKE protocol messages exchanged between agent and server
- Both sides independently derive identical session key from PAKE execution
- Session key never transmitted over network (derived locally by both sides)
- Protocol: SPAKE2, OPAQUE, SRP, or architect's choice (must be actual PAKE)
- Implementation uses established PAKE library (python-spake2, pysrp, etc.)

**PR-4: Session Establishment**
- Successful pairing creates session ID
- Session tracked in approval server
- Session includes: agent_id, agent_name, shared_secret, created_at, last_access
- Session timeout after 30 minutes of inactivity

### Credential Request Requirements

**CR-1: Request Encryption**
- Agent encrypts request before sending
- Encrypted payload includes: domain, reason, timestamp, nonce
- Nonce prevents replay attacks
- Timestamp allows server to reject old requests (>5 min old)

**CR-2: Request Transmission**
- Agent sends POST request to /credential/request
- Headers include: session_id for routing
- Body includes: encrypted_payload
- Server responds with request_id (for polling or WebSocket)

**CR-3: User Approval Collection**
- Approval client displays decrypted request
- User sees: agent name, domain, reason
- User approves/denies with Y/N
- User enters vault password if approved
- Vault unlocked, credential retrieved, vault locked

**CR-4: Response Encryption**
- Server encrypts credential before returning
- Encrypted payload includes: status, username, password, timestamp, nonce
- Nonce different from request nonce
- Timestamp for freshness validation

**CR-5: Response Reception**
- Agent polls or receives WebSocket notification
- Agent decrypts response using shared secret
- Agent validates timestamp (reject if >5 min old)
- Agent extracts credential into SecureCredential object

### Message Format Specification

**Encrypted Request Format:**
```python
# Before encryption
request_plaintext = {
    "domain": "aa.com",
    "reason": "Logging in to search and book flights",
    "timestamp": "2025-10-28T16:48:30Z",
    "nonce": "a1b2c3d4e5f6"
}

# After encryption
request_message = {
    "session_id": "sess_abc123",
    "encrypted_payload": "gAAAAABl...",  # Fernet encrypted JSON
}

# POST to /credential/request
```

**Encrypted Response Format:**
```python
# Before encryption
response_plaintext = {
    "status": "approved",
    "username": "user@example.com",
    "password": "secretpass",
    "timestamp": "2025-10-28T16:48:35Z",
    "nonce": "f6e5d4c3b2a1"
}

# After encryption
response_message = {
    "request_id": "req_xyz789",
    "encrypted_payload": "gAAAAABl...",  # Fernet encrypted JSON
}

# Returned from /credential/request or delivered via WebSocket
```

### API Endpoints Specification

**POST /pairing/initiate**
- Request: `{"agent_id": "flight-001", "agent_name": "Flight Agent"}`
- Response: `{"pairing_code": "847293", "expires_at": "2025-10-28T17:00:00Z"}`
- Agent displays pairing code to user

**POST /pairing/pair**
- Request: `{"pairing_code": "847293"}`
- Response: `{"session_id": "sess_abc123", "agent_id": "flight-001"}`
- Approval client confirms pairing

**POST /credential/request**
- Request: `{"session_id": "sess_abc123", "encrypted_payload": "..."}`
- Response (if approved): `{"status": "approved", "encrypted_payload": "..."}`
- Response (if denied): `{"status": "denied", "error": "User denied"}`

**POST /session/revoke**
- Request: `{"session_id": "sess_abc123"}`
- Response: `{"revoked": true}`
- Terminates agent session

**GET /session/status**
- Request: `?session_id=sess_abc123`
- Response: `{"active": true, "last_access": "2025-10-28T16:50:00Z"}`
- Agent can check session validity

## Code Reuse Strategy

**Reuse Without Modification:**
- `BitwardenCLI` - Approval client uses for vault access
- `SecureCredential` - Both modes use for credential handling
- `AuditLogger` - Both modes log to same audit file
- `CredentialRequest/Response` - Models work for both modes

**Modify for Dual Mode:**
- `main.py` - Add --mode flag, conditional initialization
- `FlightBookingAgent` - Accept credential source (SDK or direct)

**New for Remote Mode:**
- `ApprovalServer` - HTTP server for approval client
- `ApprovalClient` - User interface for approvals
- `CredentialSDK` - Agent-side client
- `SimplePAKE` - Pairing and encryption
- `PairingManager` - Server-side session management

## Migration Path

**Phase 1: Add Remote Mode (This Enhancement)**
- POC demonstrates both local and remote
- Remote mode uses simplified CPAKE simulation

**Phase 2: Production CPAKE (Future)**
- Replace SimplePAKE with real CPAKE library
- Add Noise protocol for forward secrecy
- Multi-client support (browser extension, mobile)

**Phase 3: Cloud Deployment (Far Future)**
- Deploy approval server to cloud
- Real remote agents (not localhost)
- Enterprise features (admin approval, policies)

## References & Research
**CPAKE Resources:**
- CPAKE paper: https://eprint.iacr.org/2020/886.pdf
- Password-authenticated key exchange overview
- Composability properties

**Python Crypto Libraries:**
- `cryptography.fernet` - Symmetric encryption (simple)
- `hashlib.pbkdf2_hmac` - Key derivation (stdlib)
- `secrets` module - Cryptographically secure random (stdlib)

**Server Frameworks:**
- Flask: Simple, well-documented, synchronous
- FastAPI: Modern, async, but more complex
- http.server: Stdlib only, but very basic

**WebSocket Libraries:**
- `websockets` - Pure async WebSocket
- `python-socketio` - Socket.IO protocol
- Flask-SocketIO - WebSocket for Flask

**Similar Patterns:**
- OAuth 2.0 Device Flow - Pairing code pattern
- SSH agent forwarding - Remote credential access
- Browser extension messaging - Approval flow pattern

## Success Metrics
**Technical Metrics:**
- Pairing success rate: 100% with valid codes
- Credential request roundtrip time: <5 seconds
- Encryption overhead: <100ms
- Local mode regression: 0 broken tests

**Demonstration Metrics:**
- Stakeholder can understand remote architecture from demo
- Clear visual separation between agent and approval terminals
- Pairing flow intuitive to user
- Credential encryption visible in logs (base64 ciphertext, not plaintext)

**Security Metrics:**
- Pairing code one-time use: 100% enforced
- Credentials encrypted in transit: 100% (verify in server logs)
- Shared secret not logged: 100% (grep for secret values)
- Session revocation immediate: <1 second from revoke to request failure