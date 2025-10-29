# Manual Integration Tests

This directory contains manual integration tests for the remote credential access enhancement. These tests require human interaction across two terminals to validate the complete pairing and credential request flows.

## Quick Start (5 Minutes)

### Terminal 1: Start Approval Client
```bash
python -m src.approval_client
```

### Terminal 2: Run Quick Smoke Test
```bash
python -m tests.manual --quick
```

Follow the on-screen instructions. This validates the two most critical flows:
1. ✅ Pairing with PAKE exchange
2. ✅ Credential request with NO password prompt

---

## Prerequisites

Before running manual tests, ensure:

1. **Approval Client Running (Terminal 1)**
   ```bash
   python -m src.approval_client
   ```
   Should show: "Server running on 127.0.0.1:5000"

2. **Bitwarden CLI Logged In**
   ```bash
   bw login  # If not already logged in
   bw status  # Should show status as logged in
   ```

3. **Test Credential Exists**
   ```bash
   # Check if example.com exists
   bw list items --search example.com
   
   # If not, create one:
   bw get template item | \
     jq '.type = 1 | .login = {username: "test@example.com", password: "test123"} | .name = "example.com"' | \
     bw encode | \
     bw create item
   ```

---

## Running Tests

### Run All Tests (~15 minutes)
```bash
python -m tests.manual
```

Runs all test suites in sequence:
1. Pairing Flow (2 tests, ~3 min)
2. Credential Request (2 tests, ~4 min)
3. Session Management (2 tests, ~3 min)
4. Error Cases (4 tests, ~5 min)

### Run Specific Test Suite

**Pairing Flow Only:**
```bash
python -m tests.manual --test pairing
```

**Credential Request Only:**
```bash
python -m tests.manual --test credential
```

**Session Management Only:**
```bash
python -m tests.manual --test session
```

**Error Cases Only:**
```bash
python -m tests.manual --test errors
```

### Quick Smoke Test (~5 minutes)
```bash
python -m tests.manual --quick
```

Runs minimal validation:
- ✓ Pairing works
- ✓ One credential request works
- ✓ NO password prompt during request

---

## Test Suites

### 1. Pairing Flow (`test_pairing.py`)

**Tests:**
- TC1: Successful pairing with correct password
- TC2: Pairing code format validation

**Critical Validation:**
- ✅ Master password entered ONCE during pairing
- ✅ Vault unlocked message appears
- ✅ PAKE exchange completes
- ✅ Session established

**Duration:** ~3 minutes

### 2. Credential Request (`test_credential_request.py`)

**Tests:**
- TC1: Credential request with approval
- TC2: Credential request with denial

**Critical Validation:**
- ✅ **NO password prompt during request** (MOST IMPORTANT)
- ✅ User only sees Y/N approval
- ✅ Credential retrieved using stored token
- ✅ Credential encrypted in transit

**Duration:** ~4 minutes

### 3. Session Management (`test_session_management.py`)

**Tests:**
- TC1: List active sessions
- TC2: Session revocation

**Validation:**
- ✅ Sessions listed correctly
- ✅ Revocation works
- ✅ Revoked session rejects requests

**Duration:** ~3 minutes

### 4. Error Cases (`test_error_cases.py`)

**Tests:**
- TC1: Wrong master password
- TC2: Expired pairing code
- TC3: Request without pairing
- TC4: Credential not found

**Validation:**
- ✅ Clear error messages
- ✅ Graceful failure handling
- ✅ Security maintained

**Duration:** ~5 minutes

---

## Understanding Test Output

### Success Example
```
═════════════════════════════════════════════════════════════════
  MANUAL TEST: Credential Request Flow
═════════════════════════════════════════════════════════════════

Checking Prerequisites
→ Checking approval server...
✓ Approval server is running
→ Checking Bitwarden CLI...
✓ Bitwarden CLI is available

✓ Prerequisites met

Setup: Establishing Session
→ Initializing credential client...
→ Initiating pairing with server...

✓ PAIRING CODE: 847293

╔═══════════════════════════════════════════════════════════════╗
║             🔵 ACTION REQUIRED IN TERMINAL 1                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Type in Terminal 1: pair 847293                             ║
║  Then enter your Bitwarden master password.                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

✓ Pairing successful

Test 1: Credential Request (Approved)
→ Requesting credential for example.com...

╔═══════════════════════════════════════════════════════════════╗
║             🔵 ACTION REQUIRED IN TERMINAL 1                  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ⚠️  CRITICAL VALIDATION:                                     ║
║                                                               ║
║  In Terminal 1, you should see credential request prompt.    ║
║                                                               ║
║  WATCH CAREFULLY: You should see:                            ║
║    ✓ Agent name and domain                                   ║
║    ✓ [Y] Approve    [N] Deny                                 ║
║                                                               ║
║  You should NOT see:                                         ║
║    ✗ Password prompt                                         ║
║    ✗ 'Enter Bitwarden master password'                       ║
║                                                               ║
║  Press Y to approve the request.                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

✓ Credential approved!
   Username: test@example.com
   Password: ********** (hidden)

✓ CRITICAL: No password prompt appeared ✓
✓ Vault was already unlocked from pairing ✓

═════════════════════════════════════════════════════════════════
  TEST SUMMARY
═════════════════════════════════════════════════════════════════

                        Test Results
┌──────────────────────┬──────────┬──────────┬────────────────┐
│ Test                 │ Status   │ Duration │ Message        │
├──────────────────────┼──────────┼──────────┼────────────────┤
│ Setup: Pairing       │ ✓ PASSED │ 12.34s   │ Session est... │
│ Credential Request   │ ✓ PASSED │ 8.56s    │ Credential ... │
└──────────────────────┴──────────┴──────────┴────────────────┘

Total: 2 tests
Passed: 2
Failed: 0
Skipped: 0

✓ ALL TESTS PASSED
```

### What to Watch For

**In Terminal 1 (Approval Client):**

✅ **During pairing:**
```
approval> pair 847293
Bitwarden master password: ********  ← Should see this ONCE
✓ Pairing successful - vault unlocked
```

✅ **During credential request:**
```
╔═══════════════════════════════════════════╗
║      🔐 Credential Access Request         ║
╟───────────────────────────────────────────╢
║ Agent: Test Agent                         ║
║ Domain: example.com                       ║
║ Allow this agent to access credentials?   ║
║                                           ║
║ Y = Approve    N = Deny                   ║  ← Only Y/N, NO PASSWORD!
╚═══════════════════════════════════════════╝

Decision: Y  ← Just type Y
✓ Approved   ← No password prompt!
```

🚨 **RED FLAG** - If you see this during a credential request:
```
Bitwarden master password: ********  ← This should NEVER appear here!
```

This means vault unlock timing is wrong. It should only appear during pairing.

---

## File Structure

```
tests/manual/
├── __init__.py              # Package initialization
├── __main__.py              # Test runner (entry point)
├── base.py                  # Base class with common utilities
├── test_pairing.py          # Pairing flow tests
├── test_credential_request.py  # Credential request tests
├── test_session_management.py  # Session management tests
├── test_error_cases.py      # Error case tests
└── README.md                # This file
```

---

## Troubleshooting

### "Failed to connect to approval server"
**Solution:** Make sure Terminal 1 is running:
```bash
python -m src.approval_client
```

### "Prerequisites not met"
Check each prerequisite:
```bash
# 1. Server running
curl http://localhost:5000/health

# 2. Bitwarden CLI
bw status

# 3. Test credential exists
bw list items --search example.com
```

### "Pairing timed out"
- Code expires in 5 minutes (or custom timeout)
- Make sure you enter code quickly in Terminal 1
- Check Terminal 1 is responding to input

### "Invalid pairing code"
- Make sure you typed it exactly (6 digits)
- Code may have expired - generate a new one

### "Incorrect master password"
- Use the same password that works with `bw unlock`
- Check Caps Lock is off

### "No credential found for example.com"
Create one:
```bash
bw get template item | \
  jq '.type = 1 | .login = {username: "test@example.com", password: "test123"} | .name = "example.com"' | \
  bw encode | \
  bw create item
```

---

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed
- `1` - Prerequisites not met

---

## Test Results

After running tests, you'll have validated:

✅ **PAKE Protocol:**
- Client and server derive identical keys
- Encrypted communication works
- Protocol messages exchanged correctly

✅ **Vault Security:**
- Master password entered once during pairing
- NO password prompt during credential requests
- Session token stored securely (never transmitted)

✅ **Session Management:**
- Sessions created and tracked
- Sessions can be listed and revoked
- Revoked sessions reject requests

✅ **Error Handling:**
- Wrong password detected
- Timeouts handled gracefully
- Missing credentials handled
- Clear error messages

---

## Next Steps

After manual tests pass:
1. Document results (save terminal output)
2. Proceed to Phase 4: Integration with FlightBookingAgent
3. Add --mode flag to main.py
4. Test end-to-end with actual aa.com login

---

**Total Test Time:** ~15 minutes (all suites) or ~5 minutes (quick test)

**Critical Validation:** NO password prompt during credential requests!