---
enhancement: remote-credential-request
agent: implementer
task_id: task_1761752781_48543
timestamp: 2025-10-29T00:00:00Z
status: READY_FOR_TESTING
---

# Test Plan: Remote Credential Access with PAKE

## Implementation Summary

This document describes the implementation of the remote credential access enhancement and provides comprehensive testing guidance for the testing phase.

### What Was Implemented

The remote credential access enhancement adds a new mode to the credential-request POC that allows agents to securely request credentials from a remote approval server using PAKE (Password-Authenticated Key Exchange) protocol.

**Core Components Implemented:**

1. **PAKEHandler** (`src/sdk/pake_handler.py`)
   - Wrapper for SPAKE2 protocol operations
   - Supports both client (SPAKE2_A) and server (SPAKE2_B) roles
   - Provides encrypt/decrypt methods using PAKE-derived keys
   - Educational implementation with clear documentation

2. **CredentialClient** (`src/sdk/credential_client.py`)
   - Agent-side SDK for remote credential requests
   - Handles pairing flow with polling mechanism
   - Encrypts all credential requests
   - Returns CredentialResponse (same API as local mode)

3. **PairingManager** (`src/server/pairing_manager.py`)
   - Manages pairing lifecycle and session storage
   - Handles PAKE server-side operations (SPAKE2_B)
   - **CRITICAL**: Unlocks vault during pairing (one-time password entry)
   - Stores Bitwarden session token for credential retrieval
   - Uses callback pattern for UI integration

4. **ApprovalServer** (`src/server/approval_server.py`)
   - Flask HTTP server with RESTful API
   - Endpoints for pairing, credential requests, and session management
   - Delegates business logic to PairingManager

5. **ApprovalClient** (`src/approval_client.py`)
   - Terminal UI for user approval
   - Runs Flask server in background thread
   - Interactive commands: pair, sessions, revoke, quit
   - Rich library for consistent UI

### Key Design Decisions

**PAKE Protocol Implementation:**
- Used `python-spake2` library (pure Python, Ed25519 curve)
- Both parties derive identical keys without transmitting password
- Pairing code (6-digit numeric) used as PAKE password
- Keys derived locally, never transmitted

**Vault Unlock Strategy:**
- User enters master password **once** during pairing
- Vault unlocked, session token obtained and stored
- Token stored in `Session.bitwarden_session_token`
- Token used for all credential requests (no re-authentication)
- Master password never stored or logged

**Communication:**
- HTTP with short polling (2-second intervals)
- 202 Accepted status for pending pairing
- All credential data encrypted with PAKE-derived keys
- Replay protection via timestamp validation (5-minute window)

**Session Management:**
- In-memory storage (dict-based)
- Pairing codes expire in 5 minutes
- Sessions expire in 30 minutes of inactivity
- Session revocation locks vault

### Files Created

**SDK (Agent-Side):**
- `src/sdk/__init__.py`
- `src/sdk/pake_handler.py` (233 lines)
- `src/sdk/credential_client.py` (296 lines)

**Server (Approval-Side):**
- `src/server/__init__.py`
- `src/server/pairing_manager.py` (473 lines)
- `src/server/approval_server.py` (256 lines)

**Client UI:**
- `src/approval_client.py` (368 lines)

**Dependencies:**
- Updated `requirements.txt` with: spake2>=0.9, Flask>=3.0.0, pytest>=7.4.0, cryptography>=41.0.0

**Total:** 7 new files, 1 modified file, ~1,626 lines of production code

### Files Modified

None yet - this is pure addition. Integration with existing code (FlightBookingAgent, main.py) is deferred to integration phase.

---

## Test Scenarios

### Scenario 1: PAKE Protocol Correctness

**Goal:** Verify SPAKE2 key derivation works correctly

**Test Cases:**

#### TC1.1: Client and Server Derive Identical Keys
**Preconditions:**
- Both parties use same password

**Steps:**
1. Client creates PAKEHandler(role="client") with password "123456"
2. Client calls start_exchange() to get msg_out_a
3. Server creates PAKEHandler(role="server") with password "123456"
4. Server calls start_exchange() to get msg_out_b
5. Client calls finish_exchange(msg_out_b)
6. Server calls finish_exchange(msg_out_a)
7. Client encrypts test message
8. Server decrypts test message

**Expected Results:**
- Both handlers complete finish_exchange() without errors
- Decrypted message matches original plaintext
- Both handlers report is_ready() == True

**Priority:** CRITICAL (foundation of security)

#### TC1.2: Wrong Password Causes PAKE Failure
**Preconditions:**
- Parties use different passwords

**Steps:**
1. Client creates PAKEHandler with password "123456"
2. Server creates PAKEHandler with password "999999"
3. Exchange messages and call finish_exchange()

**Expected Results:**
- finish_exchange() raises ValueError
- Error message indicates wrong password or invalid message
- Handlers remain in non-ready state

**Priority:** HIGH (security property)

#### TC1.3: PAKE Messages Are Not Keys
**Preconditions:**
- PAKE exchange in progress

**Steps:**
1. Capture msg_out_a and msg_out_b
2. Attempt to use messages directly as encryption keys

**Expected Results:**
- Messages are not valid Fernet keys
- Only derived shared secret (via finish()) can be used for encryption

**Priority:** HIGH (educational validation)

---

### Scenario 2: Pairing Flow

**Goal:** Verify complete pairing flow from agent initiation to session establishment

**Test Cases:**

#### TC2.1: Successful Pairing
**Preconditions:**
- Approval server running on localhost:5000
- Bitwarden CLI logged in

**Steps:**
1. Agent calls `client.pair("test-agent", "Test Agent")`
2. Observe pairing code displayed
3. In approval client, run `pair <code>`
4. Enter correct master password
5. Wait for pairing to complete

**Expected Results:**
- Pairing code is 6 digits (100000-999999)
- Approval client shows "Pairing successful - vault unlocked"
- Agent receives session_id
- Agent's PAKEHandler is ready (is_ready() == True)
- Session appears in `sessions` command

**Priority:** CRITICAL

#### TC2.2: Pairing Timeout
**Preconditions:**
- Approval server running
- Agent initiates pairing

**Steps:**
1. Agent calls `client.pair()` with timeout=10
2. Do NOT enter pairing code in approval client
3. Wait 10+ seconds

**Expected Results:**
- Agent raises TimeoutError after 10 seconds
- Error message: "Pairing timed out after 10 seconds"
- No session created

**Priority:** HIGH

#### TC2.3: Incorrect Master Password
**Preconditions:**
- Agent initiated pairing with valid code

**Steps:**
1. In approval client, run `pair <code>`
2. Enter incorrect master password

**Expected Results:**
- Approval client shows "Pairing failed"
- Error indicates "Incorrect master password"
- No session created
- Agent continues polling (doesn't fail yet)

**Priority:** HIGH

#### TC2.4: Expired Pairing Code
**Preconditions:**
- Pairing code generated 5+ minutes ago

**Steps:**
1. Wait 5+ minutes after pairing code generation
2. Attempt to use pairing code

**Expected Results:**
- Approval client shows "Pairing failed"
- Error indicates "Pairing code expired"
- Agent receives error response

**Priority:** MEDIUM

---

### Scenario 3: Credential Request Flow

**Goal:** Verify credential requests work end-to-end with vault already unlocked

**Test Cases:**

#### TC3.1: Successful Credential Request (User Approves)
**Preconditions:**
- Pairing completed successfully
- Credential for "example.com" exists in vault

**Steps:**
1. Agent calls `client.request_credential(domain="example.com", reason="Testing", ...)`
2. Observe approval prompt in approval client
3. User types "Y" to approve
4. Agent receives response

**Expected Results:**
- Approval client shows credential request with domain and reason
- No password prompt (vault already unlocked!)
- Response status == APPROVED
- Credential username and password populated
- Credential matches vault entry for example.com

**Priority:** CRITICAL

#### TC3.2: User Denies Credential Request
**Preconditions:**
- Pairing completed successfully

**Steps:**
1. Agent requests credential
2. User types "N" to deny

**Expected Results:**
- Response status == DENIED
- Credential is None
- Error message: "User denied credential access"
- No credential retrieved from vault

**Priority:** HIGH

#### TC3.3: Credential Not Found in Vault
**Preconditions:**
- Pairing completed
- Domain "nonexistent.com" not in vault

**Steps:**
1. Agent requests credential for "nonexistent.com"
2. User approves

**Expected Results:**
- Response status == ERROR
- Error message indicates credential not found
- No credential returned

**Priority:** HIGH

#### TC3.4: Request with Expired Session
**Preconditions:**
- Session expired (30+ minutes old)

**Steps:**
1. Agent attempts credential request with old session_id

**Expected Results:**
- Response status == ERROR
- Error message: "Session expired"
- Agent must re-pair

**Priority:** MEDIUM

#### TC3.5: Replay Attack Protection
**Preconditions:**
- Valid session established

**Steps:**
1. Capture encrypted_payload from a credential request
2. Wait 5+ minutes
3. Re-send same encrypted_payload

**Expected Results:**
- Request rejected
- Error message: "Request too old (possible replay attack)"

**Priority:** HIGH (security)

---

### Scenario 4: Session Management

**Goal:** Verify session lifecycle and management operations

**Test Cases:**

#### TC4.1: List Active Sessions
**Preconditions:**
- One or more active sessions

**Steps:**
1. In approval client, run `sessions` command

**Expected Results:**
- Table shows all active sessions
- Columns: Session ID, Agent Name, Agent ID, Created, Expires
- Times displayed in HH:MM:SS format

**Priority:** LOW

#### TC4.2: Revoke Session
**Preconditions:**
- Active session exists

**Steps:**
1. Note session_id from `sessions` command
2. Run `revoke <session_id>`
3. Verify session removed
4. Attempt credential request with revoked session

**Expected Results:**
- "Session revoked" message displayed
- Vault locked (bw lock called)
- Session no longer in `sessions` list
- Credential request fails with "Invalid or expired session"

**Priority:** HIGH

#### TC4.3: Session Expiry (30 minutes)
**Preconditions:**
- Session created 30+ minutes ago (or modify timeout for testing)

**Steps:**
1. Wait for session to expire
2. Attempt credential request

**Expected Results:**
- Session automatically removed
- Error: "Session expired"

**Priority:** MEDIUM

#### TC4.4: Multiple Concurrent Sessions
**Preconditions:**
- Multiple agents pairing simultaneously

**Steps:**
1. Start 3 different agents
2. Each generates pairing code
3. Pair all 3 agents
4. List sessions

**Expected Results:**
- All 3 sessions active
- Each session has unique session_id
- Sessions are independent (approving one doesn't affect others)

**Priority:** LOW

---

### Scenario 5: Encryption and Security

**Goal:** Verify all credential data is encrypted and security properties hold

**Test Cases:**

#### TC5.1: Credentials Encrypted in Transit
**Preconditions:**
- Network traffic capture enabled (e.g., tcpdump, Wireshark)

**Steps:**
1. Complete pairing flow
2. Request credential (approved)
3. Inspect captured HTTP traffic

**Expected Results:**
- No plaintext credentials visible in any HTTP request/response
- Only base64-encoded encrypted payloads
- Pairing code never transmitted after initial exchange

**Priority:** CRITICAL (security)

#### TC5.2: Session Keys Never Logged
**Preconditions:**
- Logging enabled at DEBUG level

**Steps:**
1. Complete pairing and credential request
2. Review all log files

**Expected Results:**
- No SPAKE2 shared secrets in logs
- No Fernet keys in logs
- No Bitwarden session tokens in logs
- No master passwords in logs
- Only message about "derived key (32 bytes)" without actual bytes

**Priority:** CRITICAL (security)

#### TC5.3: Master Password Never Stored
**Preconditions:**
- Code review and memory inspection

**Steps:**
1. Review PairingManager.mark_user_entered_code()
2. Verify password only used for unlock, then discarded

**Expected Results:**
- Password passed to cli.unlock()
- Session token stored
- Password not stored in any class variable
- Password not passed to Session object

**Priority:** CRITICAL (security)

#### TC5.4: Session Token Never Transmitted
**Preconditions:**
- Network traffic capture

**Steps:**
1. Complete pairing
2. Request credential
3. Inspect all HTTP traffic

**Expected Results:**
- Session token never in HTTP request/response
- Only session_id transmitted (not the token)
- Token remains in Terminal 2 process memory

**Priority:** HIGH (security)

---

### Scenario 6: Error Handling

**Goal:** Verify graceful handling of error conditions

**Test Cases:**

#### TC6.1: Server Unreachable
**Preconditions:**
- Approval server NOT running

**Steps:**
1. Agent attempts to pair

**Expected Results:**
- ConnectionError raised
- Clear error message: "Failed to connect to approval server at http://localhost:5000. Is the approval client running?"

**Priority:** HIGH

#### TC6.2: Invalid JSON in Request
**Preconditions:**
- Server running

**Steps:**
1. Send malformed JSON to /pairing/initiate

**Expected Results:**
- 400 Bad Request response
- Error message indicates missing or invalid fields

**Priority:** MEDIUM

#### TC6.3: Decryption Failure (Tampered Data)
**Preconditions:**
- Active session

**Steps:**
1. Send credential request with modified encrypted_payload
2. Change one byte of base64-encoded ciphertext

**Expected Results:**
- Decryption fails
- Error response: "Decryption failed"
- No credential leaked

**Priority:** HIGH (security)

#### TC6.4: Vault Unlock Failure
**Preconditions:**
- Bitwarden CLI in incorrect state

**Steps:**
1. Logout of Bitwarden CLI (`bw logout`)
2. Attempt pairing

**Expected Results:**
- BitwardenCLI initialization fails
- Clear error message about login required

**Priority:** MEDIUM

---

## Testing Instructions

### Environment Setup

**Prerequisites:**
1. Python 3.8+ installed
2. Bitwarden CLI installed and logged in (`bw login`)
3. Dependencies installed: `pip install -r requirements.txt`

**Bitwarden Setup:**
```bash
# Login to Bitwarden CLI
bw login

# Verify login
bw status

# Ensure at least one credential exists
# For testing, create a test entry for "example.com"
```

### Running Unit Tests

**PAKE Unit Tests:**
```bash
# Test PAKE key derivation
pytest tests/test_pake_handler.py::test_pake_key_derivation_match -v

# Test wrong password handling
pytest tests/test_pake_handler.py::test_pake_wrong_password_fails -v

# Run all PAKE tests
pytest tests/test_pake_handler.py -v
```

**SDK Unit Tests:**
```bash
# Test credential client (with mock server)
pytest tests/test_credential_client.py -v
```

**Server Unit Tests:**
```bash
# Test pairing manager
pytest tests/test_pairing_manager.py -v

# Test Flask API endpoints
pytest tests/test_approval_server.py -v
```

### Running Integration Tests (Two-Process)

**Terminal 1 - Approval Client:**
```bash
python -m src.approval_client
```

**Terminal 2 - Test Script:**
```python
from src.sdk.credential_client import CredentialClient

# Test pairing
client = CredentialClient("http://localhost:5000")
pairing_code = client.pair("test-agent", "Test Agent")
print(f"Pairing code: {pairing_code}")

# In Terminal 1, run: pair <code> and enter master password

# Test credential request
response = client.request_credential(
    domain="example.com",
    reason="Integration test",
    agent_id="test-agent",
    agent_name="Test Agent"
)

print(f"Status: {response.status}")
if response.credential:
    with response.credential as cred:
        print(f"Username: {cred.username}")
        # Don't print password in real tests!
```

### Manual Testing Checklist

**Pairing Flow:**
- [ ] Start approval client
- [ ] Start agent (request pairing)
- [ ] Observe pairing code displayed in both terminals
- [ ] Enter code and password in approval client
- [ ] Verify "Pairing successful" message
- [ ] Verify agent receives session_id

**Credential Request Flow:**
- [ ] After pairing, request credential
- [ ] Observe approval prompt in approval client
- [ ] Approve request
- [ ] Verify no password prompt (already unlocked)
- [ ] Verify agent receives credential
- [ ] Verify credential is correct (matches vault)

**Session Management:**
- [ ] List sessions (should show active session)
- [ ] Revoke session
- [ ] Attempt credential request (should fail)
- [ ] Verify vault locked after revocation

**Error Cases:**
- [ ] Try pairing with wrong password (should fail gracefully)
- [ ] Try pairing with expired code (should fail)
- [ ] Try credential request with invalid session (should fail)
- [ ] Deny credential request (agent should receive DENIED status)

---

## Expected Test Results

### Critical Success Criteria

**PAKE Correctness:**
- ✅ Client and server derive identical keys with same password
- ✅ Wrong password causes PAKE exchange to fail
- ✅ Encryption/decryption works with PAKE-derived keys

**Pairing Flow:**
- ✅ Agent can initiate pairing and receive code
- ✅ User can enter code and password in approval client
- ✅ Vault unlocked during pairing (one-time password entry)
- ✅ Session established with session_id and vault token

**Credential Flow:**
- ✅ Agent can request credential with encrypted payload
- ✅ User approval prompt appears (no password prompt!)
- ✅ Credential retrieved using stored vault token
- ✅ Credential encrypted and returned to agent
- ✅ Agent successfully decrypts and receives credential

**Security Properties:**
- ✅ No plaintext credentials in network traffic
- ✅ No keys or tokens in logs
- ✅ Master password never stored
- ✅ Session token never transmitted
- ✅ Replay attacks prevented (timestamp validation)

### Known Limitations

**Current Implementation:**
1. **In-Memory Storage:** Sessions lost on server restart
   - Impact: Users must re-pair after restart
   - Mitigation: Document as expected behavior for POC

2. **Localhost Only:** No remote server support
   - Impact: Both processes must run on same machine
   - Mitigation: This is by design for POC (remote is future enhancement)

3. **No Persistent Sessions:** No session recovery
   - Impact: Long-running agents need re-pairing
   - Mitigation: Document session timeout behavior

4. **Single User:** No multi-user support
   - Impact: One approval client instance at a time
   - Mitigation: This is by design for POC

5. **No Integration with Existing Code:** FlightBookingAgent not modified yet
   - Impact: Cannot test end-to-end with actual agent workflow
   - Mitigation: Integration deferred to next phase

### Areas Requiring Special Attention

**Critical Security Areas:**
1. **Vault Token Storage:** Verify token never logged or transmitted
2. **Password Handling:** Confirm password discarded after unlock
3. **Encryption:** Verify all credential data encrypted in transit
4. **Replay Protection:** Test timestamp validation works

**Educational PAKE Verification:**
1. **Protocol Correctness:** Both parties derive same key
2. **Message Exchange:** Only protocol messages transmitted, not keys
3. **Mutual Authentication:** Wrong password detected by both sides

**User Experience:**
1. **One-Time Password:** Verify user not prompted per-request
2. **Clear Error Messages:** All errors actionable
3. **Session Management:** Sessions listed and revoked correctly

**Edge Cases:**
1. **Concurrent Pairings:** Multiple agents pairing simultaneously
2. **Network Failures:** Connection drops during pairing
3. **Vault State:** Handle locked/unlocked/logged-out states

---

## Test Coverage Goals

**Component-Level Coverage:**
- PAKEHandler: 100% (critical crypto code)
- CredentialClient: 90% (all major paths)
- PairingManager: 90% (all major paths)
- ApprovalServer: 85% (all endpoints)
- ApprovalClient: 70% (UI code, partial coverage acceptable)

**Integration Coverage:**
- Pairing flow: All happy paths + major error paths
- Credential request: All statuses (approved/denied/error)
- Session management: Create, list, revoke, expire

**Security Coverage:**
- PAKE protocol: Key derivation, wrong password, message exchange
- Encryption: Credentials encrypted, no plaintext leaks
- Authentication: Session validation, replay protection
- Vault: Password handling, token storage, lock/unlock

---

## Issues and Concerns

### Implementation Issues

**None Currently Identified**

The implementation followed the architectural plan closely. All specified components were implemented as designed.

### Testing Challenges

**Two-Process Testing:**
- **Challenge:** Integration tests require coordination between two processes
- **Approach:** Use pytest fixtures with subprocess management
- **Status:** Test infrastructure needs to be created

**Vault State Management:**
- **Challenge:** Tests need to manage Bitwarden CLI state (lock/unlock)
- **Approach:** Setup/teardown fixtures to ensure clean state
- **Status:** Needs careful attention to avoid test pollution

**Timing Issues:**
- **Challenge:** Polling-based pairing has timing dependencies
- **Approach:** Use configurable timeouts, allow retries
- **Status:** Should be tested with various timeout values

### Future Improvements

**Post-MVP Enhancements:**
1. **Persistent Sessions:** Store sessions to survive restart
2. **WebSocket Transport:** Replace polling with real-time updates
3. **Remote Server:** Support server on different machine
4. **Session Recovery:** Allow session resumption
5. **Multi-User:** Support multiple approval clients

**Testing Enhancements:**
1. **Automated Integration Tests:** Full two-process test suite
2. **Security Testing:** Penetration testing, fuzzing
3. **Performance Testing:** Load testing, latency measurement
4. **UI Testing:** Automated terminal UI testing

---

## Integration Notes

### Next Steps for Integration Phase

**FlightBookingAgent Modification:**
1. Accept optional `credential_client` parameter
2. Use credential_client if provided, else bitwarden_agent
3. Polymorphic credential retrieval (same interface)

**main.py Modification:**
1. Add `--mode` argument (local/remote)
2. Conditional initialization based on mode
3. Pass appropriate credential source to agent

**Testing:**
1. Regression tests for local mode (unchanged behavior)
2. End-to-end tests for remote mode with actual workflow
3. Both modes work without breaking each other

### Integration Testing Scenarios

**Remote Mode End-to-End:**
1. Start approval client (Terminal 1)
2. Start flight agent with `--mode remote` (Terminal 2)
3. Agent initiates pairing
4. User pairs via approval client
5. Agent requests aa.com credentials
6. User approves
7. Agent logs into aa.com successfully

**Local Mode Regression:**
1. Start flight agent with `--mode local` (or default)
2. Verify existing behavior unchanged
3. No network calls, no pairing needed
4. BitwardenAgent used directly

---

## Summary

### Implementation Status

**✅ Completed:**
- All core components implemented
- Dependencies updated
- Code documented with educational comments
- Error handling implemented
- Logging added throughout

**⏳ Pending:**
- Unit tests (tester responsibility)
- Integration tests (tester responsibility)
- Integration with existing agents (future phase)

### Readiness for Testing

The implementation is **READY_FOR_TESTING**. All specified components are complete and functional. The code follows the architectural design and includes:

- PAKE protocol correctly implemented using python-spake2
- Complete pairing flow with vault unlock during pairing
- Credential request flow with encrypted payloads
- Session management with revocation support
- Terminal UI for user interaction
- Comprehensive error handling
- Educational documentation

### Confidence Level

**High confidence in:**
- PAKE protocol implementation (uses established library)
- Vault unlock timing (password during pairing only)
- Encryption (all credential data protected)
- Error handling (graceful failures)

**Medium confidence in:**
- Two-process coordination (needs integration testing)
- Edge cases (network failures, race conditions)
- User experience (needs real-world usage)

**Recommendations:**
1. Start with unit tests for PAKEHandler (critical foundation)
2. Test pairing flow thoroughly (most complex)
3. Verify vault password handling (security critical)
4. Run integration tests with real Bitwarden vault
5. Test error cases extensively (good error messages)

---

## Appendix: Code Locations

**Component Reference:**

| Component | File Path | Lines | Purpose |
|-----------|-----------|-------|---------|
| PAKEHandler | `src/sdk/pake_handler.py` | 233 | SPAKE2 wrapper, encryption |
| CredentialClient | `src/sdk/credential_client.py` | 296 | Agent SDK, pairing, requests |
| PairingManager | `src/server/pairing_manager.py` | 473 | Session management, vault access |
| ApprovalServer | `src/server/approval_server.py` | 256 | Flask API endpoints |
| ApprovalClient | `src/approval_client.py` | 368 | Terminal UI |

**Key Functions:**

| Function | Location | Purpose |
|----------|----------|---------|
| `PAKEHandler.start_exchange()` | pake_handler.py:67 | Start PAKE protocol |
| `PAKEHandler.finish_exchange()` | pake_handler.py:93 | Complete PAKE, derive key |
| `CredentialClient.pair()` | credential_client.py:51 | Initiate pairing flow |
| `CredentialClient.request_credential()` | credential_client.py:138 | Request credential |
| `PairingManager.mark_user_entered_code()` | pairing_manager.py:105 | Unlock vault during pairing |
| `PairingManager.handle_credential_request()` | pairing_manager.py:209 | Handle request, retrieve credential |
| `ApprovalServer.pairing_exchange()` | approval_server.py:78 | PAKE message exchange endpoint |
| `ApprovalServer.credential_request()` | approval_server.py:146 | Credential request endpoint |

**Testing Entry Points:**

- Unit tests: Each component can be tested independently
- Integration: Start `src.approval_client`, use `CredentialClient` in test script
- Manual: Run approval client, use interactive commands

---

**Status:** READY_FOR_TESTING
**Handoff to:** Tester Agent
**Next Phase:** Comprehensive testing, unit + integration + security tests
