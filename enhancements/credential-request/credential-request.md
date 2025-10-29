---
slug: credential-request-use
status: NEW
created: 2025-10-28
author: Development Team
priority: high
---

# Enhancement: AI Agent Credential Request System via Bitwarden

## Overview
**Goal:** Enable AI agents to securely request and receive user credentials from Bitwarden with explicit human approval, allowing agents to perform authenticated tasks on behalf of users without exposing credentials in agent configurations.

**User Story:**
As a user, I want my AI agents to request access to my credentials stored in Bitwarden when they need to log into websites on my behalf, so that I maintain control over credential access while enabling powerful automation without compromising security.

## Context & Background
**Current State:**
- AI agents increasingly need to perform tasks requiring authentication (booking flights, managing expenses, etc.)
- Current solutions either hard-code credentials (insecure), require manual input (breaks automation), or create permanent API tokens (overly broad access)
- No standardized way for agents to request credentials with human-in-the-loop approval
- Bitwarden CLI exists and can be used for programmatic vault access

**Technical Context:**
- Target platform: Python-based AI agent system
- Integration with Bitwarden CLI for credential management
- Headless browser automation (Playwright) for web interaction
- Human-in-the-loop approval pattern for credential access
- Example use case: Flight booking agent accessing aa.com
- Multi-agent architecture where specialized agents handle different responsibilities

**Dependencies:**
- Bitwarden CLI (must be pre-installed and configured with user account)
- Python 3.8+ with async/await support
- Playwright for browser automation
- User must have Bitwarden vault with relevant credentials stored

## Requirements

### Functional Requirements
1. **Agent Credential Request**: Agent must be able to request credentials for a specific domain with reason/context
2. **User Approval Prompt**: System must prompt user for explicit approval before accessing vault
3. **Vault Access**: System must unlock Bitwarden vault using user-provided password
4. **Credential Retrieval**: System must search vault for credentials matching requested domain
5. **Secure Credential Delivery**: Credentials must be passed to requesting agent without persistence
6. **Credential Usage**: Agent must use credentials to authenticate with target website
7. **Vault Locking**: Vault must be locked after credential retrieval is complete
8. **Access Auditing**: System must log credential access requests and user responses (approve/deny)

### Non-Functional Requirements
- **Security:** Credentials never written to disk, logs, or persistent storage; in-memory only
- **Performance:** Credential retrieval within 30 seconds of user approval
- **Memory:** Credentials cleared from memory immediately after use
- **Reliability:** Graceful handling of wrong vault password, missing credentials, vault timeout
- **Compatibility:** Works with existing Bitwarden CLI without modifications
- **Usability:** Clear, actionable prompts for user decisions

### Must Have (MVP)
- [ ] Flight booking agent that navigates to aa.com login page
- [ ] Bitwarden agent that interfaces with Bitwarden CLI
- [ ] User approval flow with vault password prompt
- [ ] Credential request message format (domain, reason, requesting agent)
- [ ] Credential retrieval from vault by domain/URL
- [ ] Secure credential passing between agents
- [ ] Successful login to aa.com using retrieved credentials
- [ ] Vault lifecycle management (unlock → use → lock)
- [ ] Basic error handling (wrong password, missing credential)

### Should Have (if time permits)
- [ ] Session-based vault unlocking (unlock once, use multiple times)
- [ ] Credential caching for limited duration (e.g., 5 minutes)
- [ ] Support for multiple domain requests in single session
- [ ] Detailed audit log with timestamps and outcomes
- [ ] Configurable timeout for user approval
- [ ] Retry mechanism for failed vault unlock

### Won't Have (out of scope)
- Complete flight booking workflow (reason: POC focuses on credential access mechanism)
- CPAKE/Noise protocol implementation (reason: using simpler CLI-based approach)
- Browser extension or mobile app approval (reason: CLI-only for POC)
- Persistent agent authorization (reason: every access requires approval)
- Multi-user support (reason: single-user POC)
- Risk scoring or anomaly detection (reason: complexity beyond MVP)

## Open Questions
> These need answers before architecture review

1. **Agent architecture:** Should we use the MultiAgentTemplate system or a simpler direct approach for this POC?
2. **Credential passing:** How should credentials be passed between agents? Options:
   - Direct function call with return value (in-process)
   - Message queue with encrypted payload
   - Shared memory object with access controls
3. **Vault session management:** Should vault be unlocked once per POC run or per credential request?
4. **Password storage:** Should vault password be kept in memory for session duration or re-prompted each time?
5. **Error recovery:** If browser login fails with credentials, should agent request credentials again or abort?
6. **Testing credentials:** Should we use real Bitwarden vault with test credentials or mock the CLI interface?
7. **Browser visibility:** Should browser run in headed mode (visible) or headless for POC demonstration?
8. **Credential matching:** How should system match agent's domain request to vault items (exact match, wildcard, fuzzy)?

## Constraints & Limitations
**Technical Constraints:**
- Must use Bitwarden CLI (no custom protocol implementation)
- Cannot modify Bitwarden vault structure or API
- Must not persist credentials to any storage (disk, database, config files)
- Must work within Python async/await programming model
- Bitwarden CLI rate limits apply (if any)

**Business/Timeline Constraints:**
- POC scope only - not production-ready system
- Focus on demonstrating concept, not handling all edge cases
- Single-user, single-machine deployment
- No enterprise features (admin approval, policy engine)
- Development time target: 1-2 weeks

**Security Constraints:**
- No credentials in source code or configuration
- No credentials in logs or debug output
- Vault password not stored after use
- Browser automation must not expose credentials to network sniffing

## Success Criteria
**Definition of Done:**
- [ ] Flight booking agent successfully navigates to aa.com login page
- [ ] User receives clear prompt: "Agent X requests credentials for aa.com for reason Y"
- [ ] User can approve or deny credential request
- [ ] Bitwarden agent unlocks vault using provided password
- [ ] Bitwarden agent retrieves aa.com credentials from vault
- [ ] Credentials passed securely to flight booking agent (no logging)
- [ ] Flight booking agent successfully logs into aa.com
- [ ] Vault is locked after credential use
- [ ] No credentials visible in any log files or console output
- [ ] README documents how to setup and run POC
- [ ] Code includes comments explaining security measures

**Acceptance Tests:**
1. **Happy Path:** Given aa.com login page displayed, when flight agent requests credentials and user provides correct vault password, then credentials are retrieved and login succeeds
2. **User Denial:** Given credential request prompt, when user denies or cancels, then agent gracefully aborts without attempting vault access
3. **Wrong Password:** Given credential request approved, when user provides incorrect vault password, then system prompts again with error message and allows retry
4. **Missing Credential:** Given credential request for domain not in vault, when Bitwarden agent searches, then clear error message returned and agent handles gracefully
5. **Vault Timeout:** Given vault unlocked, when timeout period expires, then vault auto-locks and agent must re-request access
6. **Successful Audit:** Given credential access granted and used, when reviewing logs, then audit entry shows timestamp, agent, domain, and outcome

## Security & Safety Considerations
**Critical Security Requirements:**
- **No Credential Persistence**: Credentials must never be written to disk, database, or any persistent storage
- **No Credential Logging**: Credentials must never appear in logs, console output, or debug messages
- **Memory Cleanup**: Credential variables must be overwritten/cleared immediately after use
- **Vault Locking**: Vault must be locked after each credential retrieval (defense in depth)
- **Password Handling**: Vault password must use `getpass` (no echo) and not be stored
- **Secure Transport**: If passing between processes, credentials must be encrypted in transit
- **Access Auditing**: All credential requests and user decisions must be logged (without credential values)

**Data Validation:**
- Validate domain format before vault search
- Sanitize reason text to prevent log injection
- Verify credential structure before passing to agent

**Error Handling:**
- Fail closed: On any error, deny credential access
- Clear credentials from memory in exception handlers
- Lock vault even if retrieval fails

**Resource Cleanup:**
- Use try/finally blocks to ensure vault locking
- Close browser contexts after login attempt
- Clear credential objects in finally blocks

## UI/UX Considerations
**User Prompts:**
```
╔═══════════════════════════════════════════════╗
║ 🔐 Credential Access Request                 ║
╟───────────────────────────────────────────────╢
║ Agent: Flight Booking Agent                   ║
║ Domain: aa.com                                ║
║ Reason: Logging in to search and book         ║
║         flight to Chicago                     ║
║                                               ║
║ Allow this agent to access your credentials?  ║
║                                               ║
║ [Y] Approve    [N] Deny    [C] Cancel         ║
╚═══════════════════════════════════════════════╝

Enter Bitwarden vault password: ********
```

**Status Indicators:**
- Show which agent is currently active
- Display progress: "Unlocking vault...", "Searching for credentials...", "Logging in..."
- Clear success/failure messages
- Error messages that guide user action (e.g., "Credential not found for aa.com. Please add it to Bitwarden.")

**Input Validation:**
- Accept Y/y/yes for approval, N/n/no for denial
- Allow Ctrl+C to cancel at any time
- Show password masking (******) during input
- Provide feedback if invalid option selected

## Testing Strategy
**Unit Tests:**
- Bitwarden CLI wrapper: Mock subprocess calls, test parsing
  - Test successful vault unlock
  - Test failed vault unlock (wrong password)
  - Test credential retrieval with match
  - Test credential retrieval with no match
  - Test vault locking
- Flight booking agent: Mock browser automation
  - Test navigation to login page
  - Test credential request generation
  - Test login form filling
- Credential handler: Test secure credential object
  - Test credential clearing
  - Test memory overwrites

**Integration Tests:**
- End-to-end with test Bitwarden vault:
  - Create test vault with aa.com credential
  - Run full flow from agent start to login success
  - Verify vault locked at end
- Error scenarios:
  - Wrong vault password (verify retry)
  - Missing credential (verify error handling)
  - Network failure during login
  - Browser crash during automation

**Manual Test Scenarios:**
1. **First Time Setup:**
   - Step 1: Install Bitwarden CLI and login
   - Step 2: Add test credential for aa.com to vault
   - Step 3: Run POC script
   - Step 4: Observe prompt and enter vault password
   - Step 5: Watch browser login automatically
   - Expected: Successful login visible in browser

2. **User Denies Access:**
   - Step 1: Run POC script
   - Step 2: When prompted, select "Deny"
   - Expected: Script exits gracefully with message "User denied credential access"

3. **Wrong Password Recovery:**
   - Step 1: Run POC script
   - Step 2: Enter incorrect vault password
   - Step 3: See error and retry prompt
   - Step 4: Enter correct password
   - Expected: Continues and logs in successfully

4. **Missing Credential:**
   - Step 1: Remove aa.com credential from vault
   - Step 2: Run POC script
   - Step 3: Approve and enter password
   - Expected: Clear error "No credential found for aa.com"

**Security Testing:**
- Review all log files for credential leakage
- Monitor memory (if tooling available) for credential persistence
- Verify vault locks after each run
- Confirm no credentials in environment variables
- Check no credentials in Python traceback on error

## Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2)
**Setup:**
- Create Python project structure
- Install dependencies (playwright, subprocess management)
- Setup Bitwarden CLI and test vault
- Create configuration files

**Bitwarden CLI Wrapper (`utils/bitwarden_cli.py`):**
```python
class BitwardenCLI:
    def unlock(self, password: str) -> Optional[str]:
        """Unlock vault and return session key"""
        
    def get_credential(self, domain: str, session: str) -> Optional[Dict]:
        """Search vault and retrieve credential for domain"""
        
    def lock(self) -> bool:
        """Lock the vault"""
```

### Phase 2: Agent Development (Days 3-5)
**Bitwarden Agent (`agents/bitwarden_agent.py`):**
- Implement credential request handler
- Implement user approval prompt
- Implement vault unlock logic
- Implement credential search and retrieval
- Implement secure credential return
- Implement vault locking

**Flight Booking Agent (`agents/flight_booking_agent.py`):**
- Implement browser launch (Playwright)
- Implement navigation to aa.com
- Implement login page detection
- Implement credential request to Bitwarden agent
- Implement login form filling
- Implement success verification

**Credential Handler (`utils/credential_handler.py`):**
```python
class SecureCredential:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def clear(self):
        """Overwrite credential data"""
        self.username = "X" * len(self.username)
        self.password = "X" * len(self.password)
```

### Phase 3: Integration (Days 6-7)
**Agent Communication:**
- Define credential request message format
- Implement secure credential passing
- Setup agent coordination (direct call or queue)

**Main Orchestrator (`main.py`):**
- Initialize agents
- Coordinate credential request flow
- Handle errors and cleanup
- Provide user feedback

### Phase 4: Testing & Documentation (Days 8-10)
**Testing:**
- Create test Bitwarden vault
- Run end-to-end tests
- Test all error scenarios
- Validate security (no leaks)
- Performance testing

**Documentation:**
- README with setup instructions
- Architecture diagram
- Security considerations document
- Usage guide with examples
- Troubleshooting guide

## Technical Architecture

### System Components
```
┌──────────────────────────────────────────────┐
│             User Interface (CLI)             │
│  • Approval prompts                          │
│  • Password input (getpass)                  │
│  • Status messages                           │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│           Main Orchestrator                  │
│  • Agent lifecycle management                │
│  • Request routing                           │
│  • Error handling                            │
└────────┬──────────────────────┬──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌──────────────────────┐
│ Flight Booking  │───▶│  Bitwarden Agent     │
│     Agent       │    │                      │
│                 │◀───│  • User approval     │
│ • Browser nav   │    │  • CLI interface     │
│ • Login logic   │    │  • Cred retrieval    │
│ • Cred request  │    │  • Vault locking     │
└────────┬────────┘    └──────────┬───────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│   Playwright    │    │   Bitwarden CLI      │
│     Browser     │    │   (subprocess)       │
│  • aa.com       │    │  • bw unlock         │
│  • Form filling │    │  • bw get            │
│  • Navigation   │    │  • bw lock           │
└─────────────────┘    └──────────────────────┘
```

### Data Flow Sequence
```
User → Main: Start POC
Main → FlightAgent: Initialize
FlightAgent → Browser: Launch & navigate to aa.com
FlightAgent → Main: Request credentials for "aa.com"
Main → BitwardenAgent: Forward credential request
BitwardenAgent → User: "Agent requests aa.com credentials. Approve? [Y/N]"
User → BitwardenAgent: "Y"
BitwardenAgent → User: "Enter vault password:"
User → BitwardenAgent: [password]
BitwardenAgent → CLI: bw unlock [password]
CLI → BitwardenAgent: [session_key]
BitwardenAgent → CLI: bw get --search aa.com --session [key]
CLI → BitwardenAgent: {username, password}
BitwardenAgent → CLI: bw lock
BitwardenAgent → Main: SecureCredential(username, password)
Main → FlightAgent: SecureCredential
FlightAgent → Browser: Fill login form
Browser → aa.com: POST login
Browser → FlightAgent: Login success/failure
FlightAgent → Main: Task complete
Main → FlightAgent: Cleanup (clear credentials)
Main → User: "Login successful. Vault locked."
```

### Credential Request Message Format
```python
@dataclass
class CredentialRequest:
    agent_id: str          # "flight-booking-001"
    agent_name: str        # "Flight Booking Agent"
    domain: str            # "aa.com"
    reason: str            # "Logging in to search and book flight"
    timestamp: datetime    # Request time
    timeout: int           # Seconds to wait for approval (default: 300)

@dataclass
class CredentialResponse:
    status: str            # "approved" | "denied" | "error"
    credential: Optional[SecureCredential]
    error_message: Optional[str]
    timestamp: datetime
```

## References & Research
**Documentation:**
- Bitwarden CLI documentation: https://bitwarden.com/help/cli/
- Playwright Python docs: https://playwright.dev/python/
- Python getpass module: https://docs.python.org/3/library/getpass.html
- Python secrets module: https://docs.python.org/3/library/secrets.html

**Similar Implementations:**
- SSH agent (credential delegation model)
- OAuth device flow (user approval pattern)
- Browser autofill extensions (credential management)

**Security Best Practices:**
- OWASP Credential Storage Cheat Sheet
- CWE-256: Plaintext Storage of a Password
- CWE-532: Insertion of Sensitive Information into Log File

**Related Technologies:**
- CPAKE (Composable Password-Authenticated Key Exchange)
- Noise Protocol Framework
- WebAuthn / FIDO2

## Notes for PM Subagent
> Instructions for how to process this enhancement

- If the choice between MultiAgentTemplate vs. simple approach is unclear, evaluate and recommend based on complexity vs. benefit
- Validate that the scope is appropriate for a POC (not trying to build production system)
- Confirm test credentials strategy before implementation begins
- Flag if security requirements seem insufficient for even POC-level work
- Consider whether "flight booking" is the right example or if "login to website" is sufficient

## Notes for Architect Subagent
> Key architectural considerations

- **Critical Decision:** How should credentials be passed between agents? In-process objects vs. encrypted messages?
- **Session Management:** Design vault unlock lifecycle (per-request vs. per-session)
- **Error Handling:** Design fallback paths for each failure mode
- **Security:** Ensure credentials never touch disk or logs at any point in architecture
- **Memory Management:** Consider Python's garbage collection and how to ensure credential cleanup
- **Extensibility:** While POC is simple, design should allow future expansion to multiple websites
- **Browser Context:** Isolated browser contexts per login attempt vs. persistent session

## Notes for Implementer Subagent
> Implementation guidance

- Use `getpass.getpass()` for password input (no echo to terminal)
- Use `subprocess.run()` with `capture_output=True` for Bitwarden CLI
- Clear sensitive variables explicitly: `password = "X" * len(password); del password`
- Add logging for flow, but NEVER log credentials: `logger.info("Retrieved credentials for %s", domain)` not `logger.info("Password: %s", password)`
- Use `try/finally` to ensure vault locking even on exceptions
- Use Playwright's `page.wait_for_selector()` for reliable element detection
- Add type hints for all functions involving credentials
- Consider using `__del__` method on SecureCredential class for cleanup
- Test with Playwright in headed mode first (headless=False) for debugging

## Notes for Testing Subagent
> Testing and validation guidance

- **Test Vault Setup:** Create dedicated Bitwarden vault with test credentials (test-user@example.com / TestPass123!)
- **Security Validation:** After each test, grep all log files for password fragments
- **Manual Testing:** Run with visible browser to verify login visually
- **Error Scenarios:** Test with wrong password, missing credential, network failure
- **Memory Testing:** While difficult in Python, at minimum verify variables are deleted
- **Audit Testing:** Verify audit log entries created for each credential request
- **Integration Testing:** Test full flow multiple times to check for state issues
- **Cleanup Testing:** Verify vault is locked even when POC crashes or is interrupted

## Success Metrics
**Technical Metrics:**
- Time from approval to credential delivery: < 30 seconds
- Zero credential leaks in logs (verify with log analysis)
- 100% vault locking rate (even on errors)
- Login success rate with valid credentials: 100%

**Usability Metrics:**
- User understands what they're approving (feedback survey)
- Average time for user to respond to prompt: < 60 seconds
- Error messages lead to correct user action

**Security Metrics:**
- Zero credentials in persistent storage
- Zero credentials in logs or output
- Vault auto-locks after every use
- Complete audit trail of access requests
