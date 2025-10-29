---
enhancement: credential-request
agent: architect
task_id: task_1761664245_23534
timestamp: 2025-10-28T18:30:00Z
status: READY_FOR_IMPLEMENTATION
---

# Security Architecture: AI Agent Credential Request System

## Security Overview

This document provides comprehensive security specifications for implementing the credential request system. Security is the PRIMARY concern of this system, as it handles user credentials for authentication.

## Threat Model

### Assets to Protect

**Primary Assets**:
1. **User Credentials**: Username and password for aa.com
2. **Vault Master Password**: Bitwarden vault master password
3. **Vault Session Key**: Temporary session token from Bitwarden CLI

**Secondary Assets**:
4. **Audit Log**: Record of credential access (without credential values)
5. **User Privacy**: Which agents accessed what credentials when

### Threat Actors

**In Scope**:
- **Malicious Software**: Other processes on user's machine attempting to read memory/files
- **Log Analysis**: Attackers gaining access to log files
- **File System Access**: Attackers reading files left on disk
- **Network Eavesdropping**: MITM attacks on network traffic (LIMITED - HTTPS mitigates)

**Out of Scope** (POC limitations):
- Advanced persistent threats (APTs)
- Hardware attacks (cold boot, DMA)
- Kernel-level attacks
- Social engineering attacks
- Compromised Python runtime or libraries

### Attack Vectors

**AV-1: Credential Extraction from Logs**
- **Description**: Attacker reads log files to extract credential values
- **Likelihood**: HIGH (common misconfiguration)
- **Impact**: CRITICAL (full credential compromise)
- **Mitigation**: Logging architecture that never logs credentials

**AV-2: Credential Extraction from Disk**
- **Description**: Attacker finds credential files written to disk
- **Likelihood**: MEDIUM (common developer error)
- **Impact**: CRITICAL (full credential compromise)
- **Mitigation**: No file writes containing credentials

**AV-3: Credential Extraction from Memory**
- **Description**: Attacker dumps process memory to find credentials
- **Likelihood**: LOW (requires advanced access)
- **Impact**: CRITICAL (full credential compromise)
- **Mitigation**: Minimal credential lifetime, explicit clearing

**AV-4: Vault Left Unlocked**
- **Description**: Process crashes leaving vault unlocked, other processes access vault
- **Likelihood**: MEDIUM (exceptions can bypass cleanup)
- **Impact**: HIGH (vault contents exposed)
- **Mitigation**: try/finally blocks, vault locking in all paths

**AV-5: Session Key Leakage**
- **Description**: Bitwarden session key exposed in logs or files
- **Likelihood**: MEDIUM (developers may log subprocess output)
- **Impact**: HIGH (vault access without password)
- **Mitigation**: Never log subprocess output containing session keys

**AV-6: Man-in-the-Middle (MITM) Attack**
- **Description**: Network traffic intercepted between browser and aa.com
- **Likelihood**: LOW (requires network position)
- **Impact**: HIGH (credential interception)
- **Mitigation**: HTTPS enforced by browser, certificate validation

**AV-7: Credential in Exception Traceback**
- **Description**: Exception raised with credential in message or context
- **Likelihood**: MEDIUM (easy developer error)
- **Impact**: HIGH (credential in logs/console)
- **Mitigation**: Sanitize exception messages, custom exception handling

**AV-8: Python Garbage Collection Delay**
- **Description**: Credential objects not immediately freed from memory
- **Likelihood**: HIGH (Python GC is non-deterministic)
- **Impact**: MEDIUM (credentials persist longer than expected)
- **Mitigation**: Explicit overwrite before deletion, best-effort approach

---

## Security Requirements by Category

### Category 1: Credential Confidentiality

**SEC-REQ-1.1: No Disk Persistence**

**Requirement**: Credentials MUST NEVER be written to any persistent storage

**Implementation**:
```python
# ❌ PROHIBITED - Never do this
with open("creds.txt", "w") as f:
    f.write(f"{username}:{password}")

with open("config.json", "w") as f:
    json.dump({"password": password}, f)

# ❌ PROHIBITED - Environment variables persist
os.environ["PASSWORD"] = password

# ❌ PROHIBITED - Cache files
cache = {"credentials": credential}
pickle.dump(cache, open("cache.pkl", "wb"))

# ✅ CORRECT - Keep in memory only
credential = SecureCredential(username, password)
# Use credential
credential.clear()
```

**Validation**:
- Manual: `find . -type f -name "*.txt" -o -name "*.json" -o -name "*.pkl" | xargs grep -l "password"`
- Automated: Test searches for credential values in file system

**Risk if Violated**: CRITICAL - Credentials exposed indefinitely on disk

---

**SEC-REQ-1.2: No Log Persistence**

**Requirement**: Credentials MUST NEVER appear in any log output

**Implementation**:
```python
# ❌ PROHIBITED - Credentials in logs
logger.info(f"Retrieved password: {password}")
logger.debug(f"Credential: {credential}")
print(f"Using {username}:{password}")

# ❌ PROHIBITED - Credentials in log via f-string
logger.error(f"Login failed for {username} with {password}")

# ✅ CORRECT - Log metadata only
logger.info(f"Retrieved credential for domain: {domain}")
logger.error(f"Login failed for user: {username[:3]}***")
logger.debug("Credential retrieval successful")

# ✅ CORRECT - Secure representation
class SecureCredential:
    def __repr__(self):
        return f"SecureCredential(status={'cleared' if self._cleared else 'active'})"
    # Never include username or password in __repr__ or __str__
```

**Logging Filter Implementation**:
```python
class SensitiveDataFilter(logging.Filter):
    """Filter to prevent credential leakage in logs."""

    SENSITIVE_KEYWORDS = [
        "password", "passwd", "pwd",
        "secret", "token", "key",
        "credential", "auth",
        "session_key", "session-key"
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Block or sanitize log records with sensitive data."""
        message = record.getMessage().lower()

        # Block if message contains sensitive keyword with value
        for keyword in self.SENSITIVE_KEYWORDS:
            if f"{keyword}=" in message or f'"{keyword}"' in message:
                record.msg = "[BLOCKED: Message contained sensitive data pattern]"
                record.args = ()
                return True  # Allow the sanitized message

        return True
```

**Validation**:
- Manual: `grep -i "password\|credential\|secret" *.log`
- Automated: Test parses logs and fails if pattern matches credential format

**Risk if Violated**: CRITICAL - Credentials exposed in logs forever

---

**SEC-REQ-1.3: Memory Clearing**

**Requirement**: Credentials MUST be overwritten in memory before deletion

**Implementation**:
```python
class SecureCredential:
    """Secure credential with explicit memory clearing."""

    def clear(self) -> None:
        """Clear credential from memory (best-effort)."""
        if self._cleared:
            return

        # Overwrite strings before deletion
        # Python strings are immutable, so we can't truly overwrite
        # But we can replace the reference with overwritten data
        if self._username:
            # Create new string with X's, replace reference
            self._username = "X" * len(self._username)
        if self._password:
            self._password = "X" * len(self._password)

        self._cleared = True

        # Delete references (Python GC will eventually free memory)
        del self._username
        del self._password

    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            self.clear()
        except:
            pass  # Ignore errors in __del__

# Usage
credential = SecureCredential("user", "pass")
try:
    # Use credential
    use_credential(credential)
finally:
    credential.clear()  # Explicit clearing
```

**Context Manager Pattern**:
```python
class SecureCredential:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()  # Guaranteed cleanup
        return False  # Don't suppress exceptions

# Usage guarantees cleanup
with SecureCredential(username, password) as cred:
    use_credential(cred)
# Automatically cleared here
```

**Validation**:
- Manual: Visual code review of credential lifecycle
- Automated: Test that accessing cleared credential raises ValueError

**Risk if Violated**: MEDIUM - Credentials persist longer in memory

**Note**: Python string immutability limits effectiveness of memory clearing. This is best-effort mitigation. Production systems should use mlock() or similar OS features (out of scope for POC).

---

### Category 2: Vault Security

**SEC-REQ-2.1: Vault Locking**

**Requirement**: Vault MUST be locked after every credential access, even on errors

**Implementation**:
```python
def _retrieve_credential(self, domain: str, password: str) -> Optional[SecureCredential]:
    """Retrieve credential with guaranteed vault locking."""
    session_key = None
    try:
        # Unlock vault
        session_key = self.cli.unlock(password)

        # Retrieve credential
        items = self.cli.list_items(domain, session_key)
        credential = parse_credential(items)

        return credential

    except Exception as e:
        # Log error (not credential)
        logger.error(f"Credential retrieval failed: {e}")
        raise

    finally:
        # CRITICAL: Always lock vault, even on exception
        if session_key:
            try:
                self.cli.lock()
                logger.info("Vault locked")
            except Exception as e:
                logger.error(f"Failed to lock vault: {e}")
                # Still raise original exception if there was one
```

**Cleanup Handler**:
```python
class BitwardenAgent:
    def ensure_locked(self) -> None:
        """Ensure vault is locked (called during cleanup)."""
        try:
            self.cli.lock()
        except Exception as e:
            logger.warning(f"Ensure lock failed: {e}")

# In main.py
def main():
    bitwarden_agent = BitwardenAgent()
    try:
        run_poc()
    finally:
        # Always lock vault on exit
        bitwarden_agent.ensure_locked()
```

**Validation**:
- Manual: After POC runs, check `bw status` - should show "locked"
- Automated: Test that checks vault status after operations

**Risk if Violated**: HIGH - Vault contents exposed to other processes

---

**SEC-REQ-2.2: Password Handling**

**Requirement**: Vault password MUST NOT be stored beyond its immediate use

**Implementation**:
```python
def request_credential(self, domain: str) -> CredentialResponse:
    """Request credential with secure password handling."""

    # Get password from user
    password = self._get_vault_password()  # getpass.getpass()

    try:
        # Use password immediately
        credential = self._retrieve_credential(domain, password)
        return CredentialResponse(status=APPROVED, credential=credential)

    finally:
        # CRITICAL: Clear password from memory
        if password:
            password = "X" * len(password)  # Overwrite
            del password  # Delete reference

# ❌ PROHIBITED - Don't store password as instance variable
class BitwardenAgent:
    def __init__(self):
        self.password = None  # NEVER DO THIS

# ❌ PROHIBITED - Don't pass password around
def store_password(password: str):
    """NEVER create functions like this"""
    self.stored_password = password
```

**Password Input**:
```python
import getpass

def _get_vault_password(self) -> str:
    """Securely collect vault password (no echo)."""
    return getpass.getpass("Enter Bitwarden vault password: ")

# ❌ PROHIBITED - Password echoes to terminal
password = input("Password: ")  # NEVER USE input() for passwords
```

**Validation**:
- Code review: No password stored in instance/class variables
- Test: Password never appears in logs

**Risk if Violated**: HIGH - Password exposed for longer duration

---

**SEC-REQ-2.3: Session Key Handling**

**Requirement**: Bitwarden session key MUST NOT be logged or persisted

**Implementation**:
```python
def unlock(self, password: str) -> str:
    """Unlock vault and return session key."""
    result = subprocess.run(
        [self.cli_path, "unlock", password, "--raw"],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        # ❌ PROHIBITED - Don't log stderr (may contain hints)
        # logger.error(f"Unlock failed: {result.stderr}")

        # ✅ CORRECT - Log sanitized message
        if "Invalid master password" in result.stderr:
            raise BitwardenCLIError("Invalid master password")
        else:
            raise BitwardenCLIError("Failed to unlock vault")

    session_key = result.stdout.strip()

    # ❌ PROHIBITED - Don't log session key
    # logger.debug(f"Session key: {session_key}")

    # ✅ CORRECT - Log that unlock succeeded (no key value)
    logger.info("Vault unlocked successfully")

    return session_key
```

**Validation**:
- Manual: `grep -i "session" *.log` - should not find session key values
- Test: Check logs after successful unlock

**Risk if Violated**: HIGH - Session key grants vault access without password

---

### Category 3: Exception and Error Handling

**SEC-REQ-3.1: Safe Exception Messages**

**Requirement**: Exceptions MUST NOT contain credential values in messages

**Implementation**:
```python
# ❌ PROHIBITED - Credential in exception message
raise ValueError(f"Login failed for {username}:{password}")

# ❌ PROHIBITED - Credential in exception context
try:
    login(username, password)
except Exception:
    logger.error(f"Failed with credentials: {username}, {password}")

# ✅ CORRECT - Safe exception messages
if not username:
    raise ValueError("Username is required (not provided)")

if login_failed:
    raise LoginError(f"Login failed for user: {username[:3]}***")

# ✅ CORRECT - Custom exception with safe representation
class BitwardenCLIError(Exception):
    """Safe exception for Bitwarden CLI errors."""

    def __init__(self, message: str):
        # Never include credentials in message
        super().__init__(message)

    def __str__(self):
        # Ensure string representation is safe
        return self.args[0] if self.args else "BitwardenCLIError"
```

**Exception Handling in Agent**:
```python
def request_credential(self, domain: str) -> CredentialResponse:
    """Request credential with safe error handling."""
    credential = None
    try:
        credential = self._retrieve_credential(domain, password)
        return CredentialResponse(status=APPROVED, credential=credential)

    except BitwardenCLIError as e:
        # Safe error message (no credentials)
        logger.error(f"Credential retrieval failed: {e}")
        return CredentialResponse(
            status=ERROR,
            credential=None,
            error_message=str(e)  # Already sanitized
        )

    except Exception as e:
        # Unexpected error - log but don't expose details to user
        logger.error(f"Unexpected error during credential retrieval", exc_info=True)
        return CredentialResponse(
            status=ERROR,
            credential=None,
            error_message="An unexpected error occurred"
        )

    finally:
        # Clear credential if exception occurred after creation
        if credential:
            credential.clear()
```

**Validation**:
- Code review: All exception messages checked
- Test: Trigger exceptions and verify no credentials in output

**Risk if Violated**: HIGH - Credentials exposed in logs/console via exceptions

---

### Category 4: Input Validation

**SEC-REQ-4.1: Domain Validation**

**Requirement**: Domain input MUST be validated before use

**Implementation**:
```python
import re

def _validate_domain(self, domain: str) -> str:
    """
    Validate domain format.

    Args:
        domain: Domain string from agent

    Returns:
        Validated domain string

    Raises:
        ValueError: If domain format is invalid
    """
    if not domain:
        raise ValueError("Domain cannot be empty")

    # Allow alphanumeric, dots, hyphens
    # Prevent path traversal, command injection, etc.
    if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
        raise ValueError(f"Invalid domain format: {domain}")

    # Prevent overly long domains (DOS)
    if len(domain) > 253:  # DNS max length
        raise ValueError(f"Domain too long: {len(domain)} chars")

    return domain.lower()  # Normalize to lowercase

# Usage
def request_credential(self, domain: str, reason: str, ...) -> CredentialResponse:
    """Request credential with validated inputs."""

    # Validate inputs before processing
    domain = self._validate_domain(domain)
    reason = self._sanitize_reason(reason)

    # Proceed with request
    ...
```

**Reason Sanitization**:
```python
def _sanitize_reason(self, reason: str) -> str:
    """
    Sanitize reason text for safe display and logging.

    Args:
        reason: Reason text from agent

    Returns:
        Sanitized reason text

    Raises:
        ValueError: If reason is invalid
    """
    if not reason:
        raise ValueError("Reason cannot be empty")

    # Limit length to prevent DOS or UI issues
    max_length = 200
    if len(reason) > max_length:
        reason = reason[:max_length] + "..."

    # Remove control characters (prevent log injection)
    reason = "".join(char for char in reason if char.isprintable())

    return reason
```

**Validation**:
- Test: Pass invalid domains, verify ValueError raised
- Test: Pass malicious strings (path traversal, command injection), verify blocked

**Risk if Violated**: MEDIUM - Potential for injection attacks

---

### Category 5: Audit and Logging

**SEC-REQ-5.1: Audit Completeness**

**Requirement**: All credential access attempts MUST be logged (without credential values)

**Implementation**:
```python
class AuditLogger:
    """Audit logger for credential access events."""

    def log_request(self, agent_id: str, domain: str, reason: str) -> None:
        """Log credential request."""
        self.logger.info(
            f"REQUEST | agent={agent_id} | domain={domain} | reason={reason}"
        )

    def log_approval(self, agent_id: str, domain: str) -> None:
        """Log user approval."""
        self.logger.info(
            f"APPROVED | agent={agent_id} | domain={domain}"
        )

    def log_denial(self, agent_id: str, domain: str) -> None:
        """Log user denial."""
        self.logger.info(
            f"DENIED | agent={agent_id} | domain={domain}"
        )

    def log_success(self, agent_id: str, domain: str) -> None:
        """Log successful credential use."""
        self.logger.info(
            f"SUCCESS | agent={agent_id} | domain={domain}"
        )

    def log_failure(self, agent_id: str, domain: str, error: str) -> None:
        """Log failed credential use."""
        # Sanitize error message
        safe_error = error[:200]  # Limit length
        self.logger.error(
            f"FAILURE | agent={agent_id} | domain={domain} | error={safe_error}"
        )
```

**Audit Log Format**:
```
2025-10-28T18:30:00Z | INFO | REQUEST | agent=flight-booking-001 | domain=aa.com | reason=Logging in to search and book flights
2025-10-28T18:30:15Z | INFO | APPROVED | agent=flight-booking-001 | domain=aa.com
2025-10-28T18:30:45Z | INFO | SUCCESS | agent=flight-booking-001 | domain=aa.com
```

**What to Log**:
- ✅ Timestamp (ISO 8601 format)
- ✅ Agent ID and name
- ✅ Domain requested
- ✅ Reason for request
- ✅ User decision (approve/deny)
- ✅ Outcome (success/failure)
- ❌ Username (maybe log first 3 chars with mask: `use***`)
- ❌ Password (NEVER)
- ❌ Session key (NEVER)

**Validation**:
- Test: Check audit log after each operation
- Test: Grep audit log for credential values (should find none)

**Risk if Violated**: LOW - Reduced accountability, harder incident response

---

**SEC-REQ-5.2: Log File Security**

**Requirement**: Audit log file MUST be protected from unauthorized access

**Implementation**:
```python
import os
import stat

class AuditLogger:
    def __init__(self, log_file: str = "credential_audit.log"):
        """Initialize audit logger with secure file permissions."""
        self.log_file = log_file
        self._setup_logger()
        self._secure_log_file()

    def _secure_log_file(self) -> None:
        """Set restrictive permissions on log file (Unix-like systems)."""
        if os.path.exists(self.log_file):
            # Set permissions to 0600 (read/write for owner only)
            os.chmod(self.log_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.debug(f"Secured audit log: {self.log_file}")
```

**File Permissions**:
- Unix: `chmod 600 credential_audit.log` (owner read/write only)
- Windows: Use ACLs to restrict access to current user

**Validation**:
- Manual: Check `ls -l credential_audit.log` shows `-rw-------`
- Test: Verify file permissions after log creation

**Risk if Violated**: LOW - Audit log readable by other users (but no credentials in log)

---

### Category 6: Browser Security

**SEC-REQ-6.1: HTTPS Enforcement**

**Requirement**: Browser MUST only navigate to HTTPS URLs

**Implementation**:
```python
async def run(self) -> bool:
    """Execute flight booking task."""
    # ✅ CORRECT - HTTPS URL
    await self.page.goto("https://www.aa.com/login")

    # ❌ PROHIBITED - HTTP URL (credentials in plaintext)
    # await self.page.goto("http://www.aa.com/login")

# URL validation
def _validate_url(self, url: str) -> str:
    """Validate URL is HTTPS."""
    if not url.startswith("https://"):
        raise ValueError(f"Only HTTPS URLs allowed, got: {url}")
    return url
```

**Certificate Validation**:
```python
# Playwright validates certificates by default
# Don't disable certificate validation
browser = await playwright.chromium.launch(
    headless=args.headless
    # ❌ PROHIBITED - Don't disable cert validation
    # ignore_https_errors=True  # NEVER set this
)
```

**Validation**:
- Code review: All URLs start with `https://`
- Test: Verify certificate validation not disabled

**Risk if Violated**: HIGH - MITM attacks possible

---

**SEC-REQ-6.2: Browser Context Isolation**

**Requirement**: Browser context MUST be closed after credential use

**Implementation**:
```python
async def run(self) -> bool:
    """Execute flight booking task with cleanup."""
    try:
        await self._launch_browser()
        # Use browser
        success = await self._login(credential)
        return success

    finally:
        # CRITICAL: Always close browser
        await self._cleanup_browser()

async def _cleanup_browser(self) -> None:
    """Close browser and cleanup resources."""
    try:
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    except Exception as e:
        logger.error(f"Browser cleanup error: {e}")
```

**Validation**:
- Manual: Verify browser closes after POC completes
- Test: Check that browser cleanup happens even on exceptions

**Risk if Violated**: LOW - Browser process persists with credentials in memory

---

**SEC-REQ-6.3: Bot Detection Mitigation**

**Requirement**: Browser MUST use stealth mode to avoid bot detection

**Rationale**: Many websites (including aa.com) detect automated browsers and may block login attempts. This could cause the POC to fail even with correct credentials.

**Implementation**:
```python
from playwright_stealth import stealth_async

async def _launch_browser(self) -> None:
    """Launch browser with stealth mode enabled."""
    self.playwright = await async_playwright().start()
    self.browser = await self.playwright.chromium.launch(headless=self.headless)
    self.page = await self.browser.new_page()
    
    # CRITICAL: Apply stealth mode before navigation
    await stealth_async(self.page)
    logger.debug("Stealth mode applied")

# What playwright-stealth does:
# - Removes navigator.webdriver property
# - Masks automation indicators
# - Randomizes browser fingerprint
# - Makes browser appear more human-like
```

**Why This is Important**:
- aa.com may use bot detection services (PerimeterX, DataDome, etc.)
- Without stealth mode, automation may be blocked
- Leads to POC appearing broken even with correct credentials

**Installation**:
```bash
pip install playwright-stealth
```

**Validation**:
- Test: Successful login with real credentials
- Test: Check DevTools console for webdriver property (should be undefined)

**Risk if Violated**: HIGH - POC may fail due to bot detection, not credential issues

---

## Security Testing Requirements

### Test 1: No Credentials in Logs

**Purpose**: Verify credentials never appear in any log files

**Implementation**:
```python
def test_no_credentials_in_logs():
    """Security test: No credentials in logs."""
    # Known test credentials
    test_username = "test-user@example.com"
    test_password = "TestPassword123!"

    # Run POC (requires manual interaction)
    # ...

    # Check all log files
    log_files = ["credential_audit.log", "application.log"]

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        with open(log_file) as f:
            content = f.read()

            # CRITICAL: These must not appear
            assert test_password not in content, \
                f"Password leaked in {log_file}"

            assert test_username not in content or "***" in content, \
                f"Username leaked without masking in {log_file}"
```

**Expected Result**: Test passes, no credentials found

---

### Test 2: No Credentials on Disk

**Purpose**: Verify no credential files written to disk

**Implementation**:
```python
def test_no_credential_files():
    """Security test: No credential files on disk."""
    # Run POC
    # ...

    # Search for suspicious files
    suspicious_patterns = [
        "*credential*",
        "*password*",
        "*.key",
        "*.secret"
    ]

    found_files = []
    for pattern in suspicious_patterns:
        files = list(Path(".").rglob(pattern))
        # Filter out legitimate files (source code, tests)
        found_files.extend([
            f for f in files
            if f.suffix in ['.txt', '.json', '.pkl', '.dat']
        ])

    assert len(found_files) == 0, \
        f"Found suspicious credential files: {found_files}"
```

**Expected Result**: Test passes, no credential files found

---

### Test 3: Vault Locked After Execution

**Purpose**: Verify vault is locked after POC completes

**Implementation**:
```python
def test_vault_locked_after_completion():
    """Security test: Vault locked after POC."""
    # Run POC
    # ...

    # Check vault status
    result = subprocess.run(
        ["bw", "status"],
        capture_output=True,
        text=True
    )

    status = json.loads(result.stdout)

    # Vault should be locked
    assert status["status"] in ["locked", "unauthenticated"], \
        f"Vault not locked: {status['status']}"
```

**Expected Result**: Test passes, vault is locked

---

### Test 4: Credential Clearing

**Purpose**: Verify credentials cleared from memory

**Implementation**:
```python
def test_credential_clearing():
    """Test that credentials are cleared after use."""
    cred = SecureCredential("user", "pass")

    # Use credential in context manager
    with cred as c:
        assert c.username == "user"
        assert c.password == "pass"

    # After context exit, should be cleared
    with pytest.raises(ValueError, match="cleared"):
        _ = cred.username

    with pytest.raises(ValueError, match="cleared"):
        _ = cred.password
```

**Expected Result**: Test passes, accessing cleared credential raises error

---

## Security Checklist for Implementation

### Pre-Implementation Checklist

- [ ] All team members reviewed this security architecture
- [ ] Security requirements added to acceptance criteria
- [ ] Security tests added to test plan
- [ ] Code review process includes security checks

### During Implementation Checklist

**For Each Function**:
- [ ] No credential values in function parameters (use objects)
- [ ] No credential values in return values without SecureCredential wrapper
- [ ] No credential values in log statements
- [ ] No credential values in exception messages
- [ ] No credential values in comments or docstrings

**For Each File**:
- [ ] No hardcoded credentials
- [ ] No credential values in test fixtures
- [ ] All credential operations use SecureCredential
- [ ] All vault operations use try/finally

**For Each Component**:
- [ ] Unit tests include security test cases
- [ ] Integration tests verify vault locking
- [ ] Error paths tested (no credential leaks on errors)

### Post-Implementation Checklist

- [ ] All security tests passing
- [ ] Manual security audit completed
- [ ] Grep logs for credential values (zero found)
- [ ] Search disk for credential files (zero found)
- [ ] Vault locked after test runs
- [ ] README includes security considerations
- [ ] Known security limitations documented

---

## Security Limitations (POC Scope)

**Acknowledged Limitations**:

1. **Python String Immutability**: Cannot truly overwrite string memory due to Python's immutable strings. Best-effort approach used.

2. **Garbage Collection**: Python GC is non-deterministic. Credential objects may persist in memory longer than expected.

3. **Process Memory Dumps**: Advanced attackers with system access can dump process memory to extract credentials. Out of scope for POC.

4. **Keyboard Logging**: System-level keyloggers can capture vault password during input. Out of scope for POC.

5. **Compromised Libraries**: If Python runtime or dependencies compromised, all bets are off. Supply chain security out of scope.

6. **Single-User Only**: No multi-user separation, authentication, or authorization. POC assumes single user on dedicated machine.

**Recommended for Production**:

- Use system keyring for vault password storage
- Implement mlock() to prevent memory swapping
- Use hardware security module (HSM) for credential encryption
- Implement proper authentication and authorization
- Use secure enclave or TPM for credential protection
- Add rate limiting on credential requests
- Implement anomaly detection
- Add administrator approval workflow

---

## Security Contacts and Escalation

**For Security Issues**:
1. Do NOT commit security issues to public repository
2. Report to [security contact email]
3. Include: Issue description, reproduction steps, impact assessment

**Security Incident Response**:
1. Immediately revoke compromised credentials in Bitwarden
2. Change Bitwarden master password
3. Review audit log for unauthorized access
4. Notify affected users

---

**Document Prepared by**: Architect Agent
**Security Review**: Required before implementation
**Last Updated**: 2025-10-28
