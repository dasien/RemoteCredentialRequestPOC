---
enhancement: credential-request
agent: requirements-analyst
task_id: task_1761662103_22288
timestamp: 2025-10-28T00:00:00Z
status: READY_FOR_DEVELOPMENT
---

# Open Questions Analysis

This document provides detailed analysis of the 8 open questions identified in the source enhancement specification, with recommendations for the architect agent.

---

## Question 1: Agent Architecture Pattern

### Question Statement
"Should we use the MultiAgentTemplate system or a simpler direct approach for this POC?"

### Context and Implications

**MultiAgentTemplate Approach:**
- Structured framework for multi-agent systems
- Standardized agent communication patterns
- Built-in orchestration and lifecycle management
- Learning curve for framework
- Additional setup and boilerplate code

**Direct Approach:**
- Simple Python classes for each agent
- Direct function calls between agents
- Minimal boilerplate and overhead
- Faster initial development
- Less standardization, more ad-hoc

### Impact Analysis

**Development Timeline:**
- MultiAgentTemplate: +2-3 days for learning and setup
- Direct approach: Faster initial implementation
- **Impact Level:** HIGH (affects timeline significantly)

**Code Quality:**
- MultiAgentTemplate: More consistent, maintainable structure
- Direct approach: Risk of ad-hoc patterns, harder to extend
- **Impact Level:** MEDIUM (affects maintainability)

**POC Success:**
- Either approach can demonstrate credential flow
- Core concept independent of agent framework
- **Impact Level:** LOW (doesn't affect POC viability)

**Future Extensibility:**
- MultiAgentTemplate: Easier to add new agents or features
- Direct approach: Would require refactoring to scale
- **Impact Level:** MEDIUM (but POC not intended for production)

### Analysis of Trade-offs

**Favor MultiAgentTemplate if:**
- POC will evolve into production system
- Team plans to build multiple agent-based projects
- Standardization is high priority
- Timeline can accommodate learning curve

**Favor Direct Approach if:**
- Timeline is strict (8-10 days firm)
- POC is truly throwaway code
- Team unfamiliar with MultiAgentTemplate
- Simplicity and speed prioritized over structure

### Recommendation for Architect

**Recommendation:** **Direct Approach** for MVP, with clear agent interfaces

**Rationale:**
1. 8-10 day timeline is tight for learning new framework
2. POC explicitly scoped as demonstration, not production
3. Core functionality (credential flow) is simple enough for direct approach
4. Can always migrate to framework later if POC successful

**Implementation Guidance:**
- Define clear agent interface (ABC or Protocol class)
- Use consistent patterns across agents (reduce ad-hoc code)
- Document agent communication explicitly
- Design for potential future migration to framework

**Minimal Agent Interface Example:**
```python
from abc import ABC, abstractmethod

class Agent(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize agent resources"""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup agent resources"""
        pass

class FlightBookingAgent(Agent):
    # Implementation
    pass

class BitwardenAgent(Agent):
    # Implementation
    pass
```

**Migration Path (if needed later):**
- Agent interface compatible with framework concepts
- Refactor to MultiAgentTemplate if POC becomes production
- Document migration considerations in architecture

---

## Question 2: Credential Passing Mechanism

### Question Statement
"How should credentials be passed between agents? Options: Direct function call with return value (in-process), Message queue with encrypted payload, Shared memory object with access controls"

### Context and Implications

**Option A: Direct Function Call (In-Process)**
```python
# FlightBookingAgent calls BitwardenAgent directly
credential = bitwarden_agent.get_credential(domain="aa.com", reason="Login")
browser.login(credential.username, credential.password)
credential.clear()
```

**Option B: Message Queue with Encrypted Payload**
```python
# FlightBookingAgent sends request to queue
request = CredentialRequest(domain="aa.com", reason="Login")
queue.send(request)
# BitwardenAgent receives, processes, encrypts credential
encrypted_response = queue.receive()
credential = decrypt(encrypted_response, session_key)
```

**Option C: Shared Memory with Access Controls**
```python
# BitwardenAgent writes to shared memory region
shared_mem = SharedMemory(name="credentials", create=True, size=1024)
# FlightBookingAgent reads from shared memory
credential = CredentialAccessor(shared_mem).read()
```

### Security Analysis

**Option A (Direct Call):**
- ✅ Credentials stay in single process memory space
- ✅ No serialization risk (object references only)
- ✅ Simplest cleanup (GC handles most)
- ❌ All agents must be in same process
- ❌ No encryption (but same process memory)
- **Security Rating:** GOOD for single-process

**Option B (Message Queue):**
- ✅ Supports multi-process agents
- ✅ Can encrypt credentials in transit
- ❌ Credentials serialized (persistence risk)
- ❌ More complex key management
- ❌ Queue itself may persist messages
- ❌ Additional attack surface (queue security)
- **Security Rating:** MEDIUM (depends on queue implementation)

**Option C (Shared Memory):**
- ✅ Supports multi-process agents
- ✅ Fast inter-process communication
- ❌ Credentials in shared memory (accessible to all processes)
- ❌ Complex access control implementation
- ❌ Memory not automatically cleared on exit
- ❌ Highest attack surface (all processes can access)
- **Security Rating:** POOR for credential handling

### Performance Analysis

| Option | Latency | Throughput | Complexity |
|--------|---------|------------|------------|
| A: Direct Call | <1ms | N/A | Low |
| B: Message Queue | 10-100ms | High | High |
| C: Shared Memory | 1-5ms | Very High | Medium |

**For POC:** Performance differences negligible (single credential request)

### Implementation Complexity

**Option A: Direct Call**
- Code complexity: LOW
- Setup complexity: NONE
- Error handling: Simple (exceptions)
- Testing: Easy (mock agent methods)

**Option B: Message Queue**
- Code complexity: HIGH
- Setup complexity: HIGH (queue setup, encryption)
- Error handling: Complex (timeouts, message loss)
- Testing: Difficult (mock queue, test serialization)

**Option C: Shared Memory**
- Code complexity: MEDIUM
- Setup complexity: MEDIUM (memory setup, locking)
- Error handling: Medium (memory corruption)
- Testing: Medium (cleanup between tests)

### Scalability Considerations

**Option A: Direct Call**
- Scalability: Single process, single machine
- Limitation: Can't distribute agents across processes/machines
- POC Impact: NOT A CONCERN (single-machine POC)

**Option B: Message Queue**
- Scalability: Excellent (distributed systems)
- Limitation: Queue becomes bottleneck at high volume
- POC Impact: NOT A CONCERN (single credential request)

**Option C: Shared Memory**
- Scalability: Good (multi-process on same machine)
- Limitation: Limited to single machine
- POC Impact: NOT A CONCERN (single-machine POC)

### Recommendation for Architect

**Recommendation:** **Option A - Direct Function Call**

**Rationale:**
1. **Security:** Simplest is safest - no serialization, no encryption complexity
2. **Timeline:** Fastest to implement - no queue or memory management setup
3. **POC Scope:** Single-process sufficient for demonstration
4. **Testability:** Easiest to unit test and mock
5. **Debugging:** Simplest to debug - standard call stack

**Implementation Pattern:**
```python
class Orchestrator:
    def __init__(self):
        self.bitwarden_agent = BitwardenAgent()
        self.flight_agent = FlightBookingAgent()

    async def run(self):
        # FlightAgent navigates to login page
        await self.flight_agent.navigate_to_login()

        # Request credentials via direct call
        credential_request = CredentialRequest(
            domain="aa.com",
            reason="Logging in to search flights"
        )

        # Direct function call (synchronous)
        credential_response = self.bitwarden_agent.request_credential(
            credential_request
        )

        if credential_response.status == "approved":
            # Pass credential object directly
            await self.flight_agent.login(credential_response.credential)
            # Clear immediately
            credential_response.credential.clear()
```

**Design for Future Migration:**
- Abstract agent communication behind interface
- Use CredentialRequest/CredentialResponse dataclasses (serializable)
- Document upgrade path to message queue if needed

**Upgrade Path (if multi-process needed later):**
```python
class AgentCommunicator(ABC):
    @abstractmethod
    def request_credential(self, request: CredentialRequest) -> CredentialResponse:
        pass

class DirectCommunicator(AgentCommunicator):
    # Current implementation - direct calls
    pass

class QueueCommunicator(AgentCommunicator):
    # Future implementation - message queue
    pass
```

---

## Question 3: Vault Session Management

### Question Statement
"Should vault be unlocked once per POC run or per credential request?"

### Context and Implications

**Per-Request (Unlock → Retrieve → Lock):**
- User prompted for password each time credentials needed
- Vault unlocked only for duration of retrieval (~5-10 seconds)
- Vault locked immediately after credential retrieved

**Per-Session (Unlock once, multiple requests):**
- User prompted for password once at POC start
- Vault stays unlocked for duration of POC run
- Supports multiple credential requests without re-authentication
- Vault locked at POC end or session timeout

### Security Comparison

| Aspect | Per-Request | Per-Session |
|--------|-------------|-------------|
| Vault Unlock Duration | 5-10 seconds | Minutes to hours |
| Attack Window | Minimal | Extended |
| Password Exposure | Brief (immediately cleared) | Longer (stored for session) |
| Defense in Depth | Best (re-lock frequently) | Weaker (reliance on timeout) |
| Password Storage | Not stored | Stored in memory |
| Session Key Storage | Not stored | Stored in memory |

**Security Assessment:**
- Per-Request: BEST (minimal exposure)
- Per-Session: ACCEPTABLE (relies on timeout)

### User Experience Comparison

| Aspect | Per-Request | Per-Session |
|--------|-------------|-------------|
| Password Prompts | Multiple (each request) | Once (start of session) |
| Convenience | Lower (repetitive) | Higher (password once) |
| Interruption | Each request interrupts flow | Smooth after first unlock |
| User Control | High (approve each access) | Lower (blanket approval) |

**UX Assessment:**
- Per-Request: Acceptable for POC (1-2 credential requests)
- Per-Session: Better for production (multiple requests common)

### Implementation Complexity

**Per-Request:**
- Complexity: LOW
- Logic: Straightforward (unlock, retrieve, lock)
- State management: None (stateless)
- Error handling: Simple (fail and retry)

**Per-Session:**
- Complexity: MEDIUM
- Logic: Session lifecycle management
- State management: Session key storage, timeout tracking
- Error handling: Session expiration, refresh logic

### POC Requirements Analysis

**MVP Requirements:**
- Single credential request (aa.com)
- Demonstrate approval flow
- Show secure credential handling

**POC Scope:**
- Not intended for production use
- Demonstration, not optimization
- Security more important than convenience

**User Experience:**
- 1-2 credential requests maximum
- Password prompt acceptable for POC
- Trade-off favors security

### Recommendation for Architect

**Recommendation:** **Per-Request for MVP, Design for Session Upgrade**

**Rationale:**
1. **Security First:** POC should demonstrate best security practices
2. **Simplicity:** Per-request is simpler to implement correctly
3. **POC Scope:** Single request means UX impact minimal
4. **Clear Upgrade Path:** Can add session mode as "should have" feature

**MVP Implementation:**
```python
def request_credential(self, request: CredentialRequest) -> CredentialResponse:
    # 1. Prompt for approval
    if not self.prompt_user_approval(request):
        return CredentialResponse(status="denied")

    # 2. Prompt for password
    password = self.get_vault_password()

    try:
        # 3. Unlock vault
        session_key = self.cli.unlock(password)

        # 4. Retrieve credential
        credential = self.cli.get_credential(request.domain, session_key)

        return CredentialResponse(status="approved", credential=credential)
    finally:
        # 5. Always lock vault
        self.cli.lock()
        # 6. Clear password
        password = 'X' * len(password)
        del password
```

**Session Mode (Future Enhancement):**
```python
class BitwardenAgent:
    def __init__(self):
        self.session_key = None
        self.session_expiry = None

    def start_session(self):
        """Unlock vault for session duration"""
        password = self.get_vault_password()
        self.session_key = self.cli.unlock(password)
        self.session_expiry = time.time() + 300  # 5 minute timeout
        password = 'X' * len(password)

    def request_credential(self, request: CredentialRequest):
        # Check session valid
        if not self._session_valid():
            self.start_session()

        # Use existing session
        credential = self.cli.get_credential(request.domain, self.session_key)
        return CredentialResponse(status="approved", credential=credential)

    def end_session(self):
        """Lock vault and clear session"""
        self.cli.lock()
        self.session_key = None
```

**Configuration (Future):**
```python
# Command-line flag
--session-mode   # Enable session-based unlocking
--session-timeout 300  # Session timeout in seconds
```

---

## Question 4: Password Storage During Session

### Question Statement
"Should vault password be kept in memory for session duration or re-prompted each time?"

### Dependency on Question 3
This question is directly dependent on OQ-3 (session management):
- If **per-request**: Password MUST be re-prompted (no session)
- If **per-session**: Password MAY be stored or re-prompted

### Analysis Assuming Per-Session Mode

**Option A: Store Password for Session**
```python
class BitwardenAgent:
    def __init__(self):
        self._session_password = None  # Stored in memory

    def start_session(self):
        self._session_password = getpass.getpass("Vault password: ")
        # Keep password for re-unlock if session expires

    def end_session(self):
        # Clear password
        if self._session_password:
            self._session_password = 'X' * len(self._session_password)
            self._session_password = None
```

**Option B: Re-Prompt if Session Expires**
```python
class BitwardenAgent:
    def start_session(self):
        password = getpass.getpass("Vault password: ")
        self.session_key = self.cli.unlock(password)
        # Clear password immediately
        password = 'X' * len(password)
        del password

    def _refresh_session_if_expired(self):
        if self._session_expired():
            # Re-prompt user for password
            password = getpass.getpass("Session expired. Vault password: ")
            self.session_key = self.cli.unlock(password)
            password = 'X' * len(password)
```

### Security Implications

**Storing Password:**
- ❌ Password in memory longer (attack window)
- ❌ Password could leak via memory dump
- ❌ More variables to clear on cleanup
- ✅ Can re-unlock vault silently if session expires

**Re-Prompting:**
- ✅ Password in memory briefly (minimal exposure)
- ✅ Cleared immediately after unlock
- ✅ Fewer variables to secure
- ❌ User interruption if session expires

**Security Verdict:** Re-prompting is more secure

### User Experience

**Storing Password:**
- ✅ Seamless re-unlock (no user interruption)
- ✅ Better for multiple credential requests
- ❌ User may forget password was given (implicit reuse)

**Re-Prompting:**
- ❌ User interrupted if session expires
- ✅ Explicit user action for re-authentication
- ✅ User aware of vault access

**UX Verdict:** Storing is more convenient, re-prompting is more transparent

### Recommendation for Architect

**Recommendation:** **Re-Prompt on Session Expiry (if session mode implemented)**

**Rationale:**
1. **Security:** Aligns with principle of minimal credential lifetime
2. **Transparency:** User explicitly aware of vault access
3. **Implementation:** Simpler (one less variable to secure)
4. **POC Scope:** Session expiry unlikely in short POC run

**Conditional Recommendation:**
- **For MVP (per-request mode):** Not applicable - password never stored
- **For Session Mode (future):** Re-prompt on expiry
- **For Production (far future):** Consider OS keychain for password storage

**Implementation Pattern:**
```python
def _ensure_session_active(self):
    """Ensure vault session is active, prompt if expired"""
    if not self.session_key or self._session_expired():
        print("Vault session expired or inactive.")
        password = getpass.getpass("Enter vault password: ")
        try:
            self.session_key = self.cli.unlock(password)
            self.session_expiry = time.time() + self.session_timeout
        finally:
            # Clear password immediately
            password = 'X' * len(password)
            del password
```

**Alternative for Production (OS Keychain):**
```python
# Store password in OS keychain (macOS Keychain, Windows Credential Manager)
import keyring

def store_session_password(self, username, password):
    # OS handles secure storage
    keyring.set_password("bitwarden_poc", username, password)

def retrieve_session_password(self, username):
    # OS handles secure retrieval
    return keyring.get_password("bitwarden_poc", username)
```

---

## Question 5: Login Failure Recovery

### Question Statement
"If browser login fails with credentials, should agent request credentials again or abort?"

### Failure Scenario Analysis

**Possible Causes of Login Failure:**

1. **Wrong Credentials in Vault** (User Error)
   - User stored incorrect username/password
   - Password changed on website, vault not updated
   - **Frequency:** LOW (user's responsibility)
   - **Resolution:** User must update vault

2. **Website Changed Login Flow** (Website Change)
   - Form structure changed (selectors broken)
   - New authentication method (2FA, CAPTCHA)
   - **Frequency:** MEDIUM (over time)
   - **Resolution:** Update POC selectors

3. **Network Error** (Transient)
   - Timeout during form submission
   - Connection lost during authentication
   - **Frequency:** LOW
   - **Resolution:** Retry

4. **Bot Detection** (Website Defense)
   - Website detected automation and blocked
   - CAPTCHA presented
   - **Frequency:** MEDIUM (depends on website)
   - **Resolution:** Use stealth mode or manual intervention

5. **Credential Worked but 2FA Required** (Out of Scope)
   - First factor succeeded, second factor needed
   - **Frequency:** DEPENDS on test account setup
   - **Resolution:** Use test account without 2FA

### Recovery Strategy Analysis

**Option A: Abort Immediately**
```python
result = await browser.login(credential)
if not result.success:
    raise LoginFailedError(f"Login failed: {result.error}")
# User sees error, POC exits
```

**Pros:**
- Simple implementation
- No retry loops
- Clear failure indication

**Cons:**
- No distinction between transient and permanent errors
- No user guidance on resolution

**Option B: Retry Credential Request**
```python
max_attempts = 3
for attempt in range(max_attempts):
    credential = request_credential(domain)
    result = await browser.login(credential)
    if result.success:
        break
    print(f"Login failed (attempt {attempt+1}/{max_attempts}). Try again?")
```

**Pros:**
- Handles wrong password case (user can provide different credential)
- User can retry

**Cons:**
- Could loop if same wrong credential returned
- Annoying if website issue (not credential issue)

**Option C: Smart Error Detection**
```python
result = await browser.login(credential)
if not result.success:
    if result.error_type == "wrong_credentials":
        # Vault has wrong password
        print("Login failed: Invalid username or password.")
        print("Please update credentials in Bitwarden vault.")
        abort()
    elif result.error_type == "network_error":
        # Retry once
        print("Network error. Retrying...")
        result = await browser.login(credential)
    elif result.error_type == "website_changed":
        # POC issue
        print("Login form not detected. Website may have changed.")
        abort()
```

**Pros:**
- Contextual error handling
- Clear user guidance
- Appropriate action for each error type

**Cons:**
- Complex error detection logic
- May misclassify errors

### Recommendation for Architect

**Recommendation:** **Abort with Specific Error Message (Option C Lite)**

**Rationale:**
1. **User Responsibility:** Credentials in vault are user's concern
2. **POC Scope:** Not a robust production system
3. **Clear Feedback:** Error message guides user to resolution
4. **Simplicity:** No complex retry logic

**Implementation Pattern:**
```python
async def attempt_login(self, credential: SecureCredential) -> LoginResult:
    """Attempt login and return detailed result"""
    try:
        await self.page.fill("#username", credential.username)
        await self.page.fill("#password", credential.password)
        await self.page.click("#login-button")

        # Wait for navigation or error message
        await self.page.wait_for_load_state("networkidle", timeout=30000)

        # Check for success indicators
        if await self.page.query_selector("#user-profile"):
            return LoginResult(success=True)

        # Check for error indicators
        if await self.page.query_selector(".error-message"):
            error_text = await self.page.inner_text(".error-message")
            return LoginResult(
                success=False,
                error_type="wrong_credentials",
                error_message=error_text
            )

        # Inconclusive
        return LoginResult(
            success=False,
            error_type="unknown",
            error_message="Could not determine login outcome"
        )

    except TimeoutError:
        return LoginResult(
            success=False,
            error_type="network_error",
            error_message="Login timed out"
        )

# In orchestrator
result = await flight_agent.attempt_login(credential)
if not result.success:
    if result.error_type == "wrong_credentials":
        print("❌ Login failed: Invalid username or password")
        print("Please verify credentials in Bitwarden vault:")
        print(f"  1. Run: bw get item {domain}")
        print(f"  2. Verify username and password")
        print(f"  3. Update if necessary: bw edit item {domain}")
    elif result.error_type == "network_error":
        print("❌ Login failed: Network timeout")
        print("Please check your internet connection and try again")
    else:
        print(f"❌ Login failed: {result.error_message}")
        print("This may indicate the website has changed.")

    sys.exit(1)
```

**Do NOT Implement:**
- Automatic credential re-request (user will get same wrong credential)
- Silent retries (user should know something failed)
- Complex retry logic (out of scope for POC)

**Future Enhancement:**
- Option to update vault credential from POC
- Multiple credential selection if multiple matches
- Manual intervention mode (pause and let user check)

---

## Question 6: Testing Credentials Strategy

### Question Statement
"Should we use real Bitwarden vault with test credentials or mock the CLI interface?"

### Testing Approaches

**Approach A: Real Vault with Test Credentials**
- Create test Bitwarden account
- Add test credentials (test-user@example.com / TestPass123!)
- Run tests against real Bitwarden CLI
- Requires Bitwarden account and CLI setup

**Approach B: Mock CLI Interface**
- Mock subprocess calls to Bitwarden CLI
- Return predefined responses (JSON)
- No external dependencies
- Isolated unit tests

**Approach C: Hybrid (Both)**
- Unit tests use mocked CLI
- Integration tests use real vault
- Best of both worlds

### Comparison Matrix

| Aspect | Real Vault | Mock CLI | Hybrid |
|--------|-----------|---------|--------|
| **Setup Complexity** | High | Low | Medium |
| **Test Speed** | Slow (network) | Fast | Mixed |
| **External Dependencies** | Required | None | Required (integration only) |
| **Realism** | High | Low | High (integration) |
| **CI/CD Friendly** | Medium | High | High |
| **Error Scenario Testing** | Hard | Easy | Easy (unit) + Real (integration) |

### Unit Testing Considerations

**What to Test:**
- Bitwarden CLI wrapper parsing logic
- Credential request/response handling
- Error mapping and user messages
- Vault locking in exception scenarios

**Mock Approach Benefits:**
- Fast test execution (<1 second)
- Easy to test error scenarios (wrong password, missing credential)
- No network dependency
- Repeatable and deterministic

**Example Unit Test:**
```python
@patch('subprocess.run')
def test_unlock_wrong_password(mock_run):
    # Mock CLI returning error
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Invalid master password"
    )

    cli = BitwardenCLI()
    session_key = cli.unlock("wrong_password")

    assert session_key is None
```

### Integration Testing Considerations

**What to Test:**
- End-to-end flow with real CLI
- Actual vault locking behavior
- Real CLI error codes and messages
- CLI version compatibility

**Real Vault Benefits:**
- Validates actual integration
- Catches CLI behavior changes
- Tests real error codes
- Confidence in production behavior

**Example Integration Test:**
```python
@pytest.mark.integration
def test_full_credential_flow():
    """Requires: Bitwarden CLI logged in, test credential in vault"""
    agent = BitwardenAgent()

    request = CredentialRequest(
        domain="test.example.com",
        reason="Integration test"
    )

    # This will prompt for password (use test password)
    response = agent.request_credential(request)

    assert response.status == "approved"
    assert response.credential.username == "test-user@example.com"

    # Verify vault locked
    status = subprocess.run(["bw", "status"], capture_output=True)
    assert "locked" in status.stdout.decode()
```

### CI/CD Considerations

**Real Vault in CI:**
- Requires Bitwarden CLI installed in CI environment
- Requires test account credentials (secrets management)
- Requires `bw login` in CI setup
- Network dependency (CI must reach Bitwarden servers)

**Mock in CI:**
- No special setup required
- Fast execution
- No secrets needed
- No network dependency

**Hybrid in CI:**
- Unit tests (mocked) run always
- Integration tests (real vault) run optionally or on schedule
- Fast feedback from unit tests
- Confidence from integration tests

### Recommendation for Architect

**Recommendation:** **Hybrid Approach - Mock for Unit Tests, Real Vault for Integration Tests**

**Rationale:**
1. **Speed:** Unit tests with mocks provide fast feedback
2. **Coverage:** Mocks enable testing error scenarios easily
3. **Confidence:** Real vault integration tests validate actual behavior
4. **Flexibility:** Can run unit tests without Bitwarden setup

**Test Organization:**
```
tests/
├── unit/
│   ├── test_bitwarden_cli.py       # Mocked CLI tests
│   ├── test_bitwarden_agent.py     # Mocked agent tests
│   ├── test_flight_agent.py        # Mocked browser tests
│   └── test_credential_handler.py  # Credential object tests
├── integration/
│   ├── test_end_to_end.py          # Real vault + real browser
│   ├── test_bitwarden_integration.py  # Real CLI tests
│   └── conftest.py                 # Setup test vault
└── conftest.py                     # Shared fixtures
```

**Unit Test Strategy (Mocked):**
```python
# tests/unit/test_bitwarden_cli.py
import pytest
from unittest.mock import patch, MagicMock
from utils.bitwarden_cli import BitwardenCLI

@pytest.fixture
def mock_subprocess():
    with patch('subprocess.run') as mock:
        yield mock

def test_unlock_success(mock_subprocess):
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="session_key_abc123",
        stderr=""
    )

    cli = BitwardenCLI()
    session_key = cli.unlock("correct_password")

    assert session_key == "session_key_abc123"
    mock_subprocess.assert_called_once()

def test_unlock_wrong_password(mock_subprocess):
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Invalid master password"
    )

    cli = BitwardenCLI()
    session_key = cli.unlock("wrong_password")

    assert session_key is None

def test_get_credential_found(mock_subprocess):
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout='[{"login": {"username": "user", "password": "pass"}}]',
        stderr=""
    )

    cli = BitwardenCLI()
    credential = cli.get_credential("example.com", "session_key")

    assert credential["username"] == "user"
    assert credential["password"] == "pass"
```

**Integration Test Strategy (Real Vault):**
```python
# tests/integration/conftest.py
import pytest
import subprocess

@pytest.fixture(scope="session")
def bitwarden_test_vault():
    """Setup: Requires env vars BW_TEST_EMAIL, BW_TEST_PASSWORD"""
    # Verify CLI installed
    result = subprocess.run(["bw", "--version"], capture_output=True)
    if result.returncode != 0:
        pytest.skip("Bitwarden CLI not installed")

    # Verify logged in
    result = subprocess.run(["bw", "status"], capture_output=True)
    if "unauthenticated" in result.stdout.decode():
        pytest.skip("Bitwarden CLI not logged in")

    yield

@pytest.mark.integration
def test_real_vault_unlock(bitwarden_test_vault):
    """Test with real Bitwarden CLI"""
    password = os.getenv("BW_TEST_PASSWORD")
    if not password:
        pytest.skip("BW_TEST_PASSWORD not set")

    cli = BitwardenCLI()
    session_key = cli.unlock(password)

    assert session_key is not None
    assert len(session_key) > 0

    # Cleanup: lock vault
    cli.lock()
```

**Documentation in README:**
```markdown
## Testing

### Unit Tests (Fast, No Setup Required)
npm test:unit

### Integration Tests (Requires Bitwarden Setup)
1. Install Bitwarden CLI: `npm install -g @bitwarden/cli`
2. Login: `bw login your-email@example.com`
3. Add test credential:
   bw get template item | jq '.name="test.example.com" | .login={username:"test-user@example.com",password:"TestPass123!",uris:[{match:null,uri:"test.example.com"}]}' | bw encode | bw create item
4. Set environment variable: `export BW_TEST_PASSWORD=your_vault_password`
5. Run integration tests: `pytest tests/integration -m integration`

### Security Tests
pytest tests/security
# Includes: log scanning for credential leaks, vault locking verification
```

---

## Question 7: Browser Visibility Mode

### Question Statement
"Should browser run in headed mode (visible) or headless for POC demonstration?"

### Mode Comparison

**Headed Mode (Visible Browser):**
- Browser window opens on screen
- User can see what agent is doing in real-time
- Easier debugging (visual inspection)
- Requires display/GUI environment

**Headless Mode (Invisible Browser):**
- No browser window (background process)
- Faster execution (no rendering overhead)
- Works on servers without display
- Harder to debug (can't see what's happening)

### Use Case Analysis

**POC Demonstration:**
- Goal: Show stakeholders how agent works
- Requirement: Transparency and trust
- **Verdict:** Headed mode better (visibility builds trust)

**Automated Testing:**
- Goal: Fast, repeatable test execution
- Requirement: No GUI dependency
- **Verdict:** Headless mode better (speed and CI compatibility)

**Development/Debugging:**
- Goal: Fix selector issues, understand website behavior
- Requirement: See what's happening
- **Verdict:** Headed mode better (visual debugging)

**Production Deployment:**
- Goal: Reliable automation at scale
- Requirement: Server compatibility, performance
- **Verdict:** Headless mode better (no display required)

### Technical Considerations

**Headed Mode:**
- Playwright: `browser = await playwright.chromium.launch(headless=False)`
- Resource usage: Higher (rendering UI)
- Compatibility: Requires X11/Wayland/Quartz display
- **Limitation:** Won't work in Docker containers without display

**Headless Mode:**
- Playwright: `browser = await playwright.chromium.launch(headless=True)`
- Resource usage: Lower (no rendering)
- Compatibility: Works anywhere (servers, containers)
- **Limitation:** Harder to diagnose issues

**Configurable:**
```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
args = parser.parse_args()

browser = await playwright.chromium.launch(headless=args.headless)
```

### Recommendation for Architect

**Recommendation:** **Configurable with CLI Flag, Default to Headed for POC**

**Rationale:**
1. **Demonstration:** POC is for stakeholder demo - visibility is key
2. **Development:** Developers benefit from seeing browser during implementation
3. **Flexibility:** Some users may need headless (CI, server environments)
4. **Trust:** Visible automation builds user confidence in security

**Implementation:**
```python
# main.py
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Agent Credential Request POC"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: visible)"
    )
    return parser.parse_args()

async def main():
    args = parse_args()

    # Pass headless flag to agent
    flight_agent = FlightBookingAgent(headless=args.headless)

    print(f"Browser mode: {'headless' if args.headless else 'visible'}")
    await flight_agent.run()

# Usage:
# python main.py              # Visible browser (default)
# python main.py --headless   # Headless browser
```

**README Documentation:**
```markdown
## Usage

### Default Mode (Visible Browser)
python main.py

Browser window will open and you can watch the agent interact with the website.

### Headless Mode (Background)
python main.py --headless

Browser runs in background. Useful for:
- Automated testing
- Server environments without display
- Performance testing

### Debugging
- Use visible mode (default) to debug selector issues
- Take screenshots on errors (saved to screenshots/)
- Check playwright trace for timing issues
```

**Test Configuration:**
```python
# tests/conftest.py
@pytest.fixture
def browser_config(request):
    # Integration tests run in headless by default
    headless = request.config.getoption("--headless", default=True)

    # Unless explicitly testing headed mode
    if request.node.get_closest_marker("headed"):
        headless = False

    return {"headless": headless}

# Test example
@pytest.mark.integration
@pytest.mark.headed  # Force visible browser for this test
def test_login_visual_verification(browser_config):
    # This test runs in headed mode for visual verification
    pass
```

**Future Enhancement:**
- Slow motion mode for demonstrations: `slow_mo=1000` (1 second delay between actions)
- Screenshot on error: Automatically capture screenshot if login fails
- Video recording: Record browser session for bug reports

---

## Question 8: Credential Matching Strategy

### Question Statement
"How should system match agent's domain request to vault items (exact match, wildcard, fuzzy)?"

### Matching Approaches

**Approach A: Exact String Match**
```python
def find_credential(domain: str, items: list) -> dict:
    for item in items:
        if item.get("name") == domain:
            return item
    return None

# Matches: "aa.com" request finds "aa.com" item
# Fails: "aa.com" request does NOT find "www.aa.com" item
```

**Approach B: Fuzzy/Substring Match**
```python
def find_credential(domain: str, items: list) -> dict:
    for item in items:
        # Check if domain is substring of item name or vice versa
        if domain in item.get("name", "") or item.get("name", "") in domain:
            return item
    return None

# Matches: "aa.com" finds "www.aa.com"
# Matches: "aa.com" finds "login.aa.com"
# Risk: "aa.com" might match "www.aaa.com.fake.site"
```

**Approach C: Bitwarden's Built-in URI Matching**
```python
def find_credential(domain: str, session: str) -> dict:
    # Use Bitwarden's own search
    result = subprocess.run(
        ["bw", "list", "items", "--search", domain, "--session", session],
        capture_output=True
    )
    items = json.loads(result.stdout)
    return items[0] if items else None

# Leverages Bitwarden's URI matching logic
# Handles subdomains, schemes, etc.
```

### Bitwarden URI Matching Behavior

**How Bitwarden Stores URIs:**
```json
{
  "name": "American Airlines",
  "login": {
    "uris": [
      {
        "match": null,  // Default matching
        "uri": "https://www.aa.com"
      },
      {
        "match": 0,  // Base domain (matches aa.com, www.aa.com, etc.)
        "uri": "aa.com"
      }
    ],
    "username": "user@example.com",
    "password": "password123"
  }
}
```

**URI Match Types:**
- `null` or `0`: Domain matching (base domain and subdomains)
- `1`: Host matching (exact host only)
- `2`: Starts with (URI starts with given string)
- `3`: Regex matching
- `4`: Exact matching
- `5`: Never

**Bitwarden's Matching Logic:**
- `bw list items --search aa.com` returns items where:
  - Name contains "aa.com"
  - URI contains "aa.com"
  - Notes contain "aa.com"
- Smart enough to handle common variations

### Problem Analysis

**User Storage Patterns:**
Users might store credentials as:
- Name: "American Airlines", URI: "https://www.aa.com"
- Name: "aa.com", URI: "aa.com"
- Name: "AA Login", URI: "www.aa.com"
- Multiple items with different URIs for same site

**Agent Request Patterns:**
- Agent requests: "aa.com" (base domain)
- Webpage URL: "https://www.aa.com/login"
- May vary by page: "booking.aa.com", "login.aa.com"

**Matching Challenges:**
- Agent requests "aa.com", user stored "www.aa.com"
- Agent requests "www.aa.com", user stored "aa.com"
- Multiple credentials for same domain (different accounts)

### Recommendation for Architect

**Recommendation:** **Use Bitwarden's Built-in Search with First-Match Selection**

**Rationale:**
1. **Leverage Existing Logic:** Bitwarden has sophisticated URI matching
2. **User Expectations:** Users are familiar with how Bitwarden matches URIs
3. **Simplicity:** No need to reimplement matching logic
4. **Compatibility:** Works with however user organized their vault

**Implementation:**
```python
def search_vault_for_credential(
    domain: str,
    session_key: str
) -> Optional[Dict[str, str]]:
    """
    Search Bitwarden vault for credential matching domain.

    Uses Bitwarden's built-in search which matches:
    - Item name
    - Item URIs
    - Item notes

    Returns first match found.
    """
    result = subprocess.run(
        ["bw", "list", "items", "--search", domain, "--session", session_key],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        logger.error(f"Bitwarden search failed: {result.stderr}")
        return None

    try:
        items = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Bitwarden output: {result.stdout}")
        return None

    if not items:
        logger.info(f"No credentials found for domain: {domain}")
        return None

    if len(items) > 1:
        logger.warning(f"Multiple credentials found for {domain}, using first match")
        # Future enhancement: prompt user to select

    # Extract login credentials
    item = items[0]
    login = item.get("login", {})

    return {
        "username": login.get("username", ""),
        "password": login.get("password", ""),
        "item_name": item.get("name", "Unknown"),
        "item_id": item.get("id", "")
    }
```

**Error Handling for No Matches:**
```python
credential = search_vault_for_credential("aa.com", session_key)

if credential is None:
    print("❌ No credential found for aa.com")
    print()
    print("Please add a credential to your Bitwarden vault:")
    print("  1. Open Bitwarden (web or app)")
    print("  2. Create new Login item")
    print("  3. Set name: 'American Airlines' (or any name)")
    print("  4. Set URI: 'aa.com' or 'https://www.aa.com'")
    print("  5. Set username and password")
    print("  6. Save and try again")
    return
```

**Handling Multiple Matches (Future Enhancement):**
```python
if len(items) > 1:
    print(f"Multiple credentials found for {domain}:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['name']}")

    choice = input("Select credential (1-{}): ".format(len(items)))
    try:
        index = int(choice) - 1
        if 0 <= index < len(items):
            item = items[index]
        else:
            print("Invalid selection")
            return None
    except ValueError:
        print("Invalid input")
        return None
```

**Documentation for Users:**
```markdown
## Setting Up Credentials in Bitwarden

The POC uses Bitwarden's built-in search to find credentials. Credentials will be found if:

1. **Item name** contains the domain (e.g., item named "aa.com" or "American Airlines")
2. **Item URI** contains the domain (e.g., URI set to "aa.com" or "https://www.aa.com")

### Recommended Setup
bw get template item | \\
  jq '.name="American Airlines" | .login={username:"your-username",password:"your-password",uris:[{match:0,uri:"aa.com"}]}' | \\
  bw encode | \\
  bw create item

### Tips
- Use base domain in URI (aa.com) rather than full URL
- Match type 0 (base domain) works for all subdomains
- If multiple credentials exist for same domain, POC uses first match
```

**Alternative: Strict URI Matching (Not Recommended)**
If Bitwarden's search proves too broad:
```python
def find_exact_uri_match(domain: str, items: list) -> dict:
    """Find item with URI exactly matching domain"""
    for item in items:
        uris = item.get("login", {}).get("uris", [])
        for uri_obj in uris:
            uri = uri_obj.get("uri", "")
            # Strip protocol and www
            clean_uri = uri.replace("https://", "").replace("http://", "").replace("www.", "")
            clean_domain = domain.replace("www.", "")

            if clean_uri == clean_domain or clean_uri.startswith(clean_domain + "/"):
                return item
    return None
```

**Not recommended because:** Requires reimplementing Bitwarden's matching logic, likely to miss edge cases

---

## Summary and Handoff to Architect

All 8 open questions have been analyzed with recommendations:

| Question | Recommendation | Priority |
|----------|---------------|----------|
| OQ-1: Agent Architecture | Direct approach (not MultiAgentTemplate) | HIGH |
| OQ-2: Credential Passing | Direct function calls (in-process) | CRITICAL |
| OQ-3: Vault Session | Per-request for MVP, session as enhancement | CRITICAL |
| OQ-4: Password Storage | Re-prompt (don't store) | CRITICAL |
| OQ-5: Login Failure | Abort with specific error message | HIGH |
| OQ-6: Testing Strategy | Hybrid (mock + real vault) | HIGH |
| OQ-7: Browser Mode | Configurable, default to headed | MEDIUM |
| OQ-8: Credential Matching | Use Bitwarden's built-in search | HIGH |

### Key Principles for Architect

1. **Security First:** When trade-offs arise, favor security over convenience
2. **Simplicity for POC:** Choose simpler implementation over scalable architecture
3. **Clear Upgrade Paths:** Document how to enhance each decision later
4. **User Guidance:** Provide clear error messages and documentation

### Critical Decisions Required Before Implementation

- **Decision 1:** Confirm agent architecture approach (direct vs. MultiAgentTemplate)
- **Decision 2:** Confirm credential passing mechanism (direct calls vs. queue)
- **Decision 3:** Confirm vault session strategy (per-request vs. per-session)

All other questions have clear recommendations that can be implemented directly.

---

**Document End**
