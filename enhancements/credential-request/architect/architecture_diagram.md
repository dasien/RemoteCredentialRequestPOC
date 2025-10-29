---
enhancement: credential-request
agent: architect
task_id: task_1761664245_23534
timestamp: 2025-10-28T18:30:00Z
status: READY_FOR_IMPLEMENTATION
---

# Architecture Diagram: AI Agent Credential Request System

## System Context Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         External Systems                           │
│                                                                    │
│  ┌─────────────────┐              ┌──────────────────┐           │
│  │  Bitwarden      │              │   aa.com         │           │
│  │  Vault          │              │   Website        │           │
│  │  (Cloud/Local)  │              │   (External)     │           │
│  └────────┬────────┘              └────────┬─────────┘           │
│           │                                │                     │
└───────────┼────────────────────────────────┼─────────────────────┘
            │                                │
            │ CLI commands                   │ HTTPS
            │                                │
┌───────────┼────────────────────────────────┼─────────────────────┐
│           │    Credential Request POC      │                     │
│           │                                │                     │
│  ┌────────▼─────────┐           ┌─────────▼──────────┐          │
│  │  Bitwarden CLI   │           │   Playwright       │          │
│  │  (subprocess)    │           │   Browser          │          │
│  └────────▲─────────┘           └─────────▲──────────┘          │
│           │                                │                     │
│  ┌────────┴─────────┐           ┌─────────┴──────────┐          │
│  │ BitwardenAgent   │◄──────────┤ FlightBookingAgent │          │
│  └────────▲─────────┘           └─────────▲──────────┘          │
│           │                                │                     │
│           └────────────┬───────────────────┘                     │
│                        │                                         │
│              ┌─────────▼─────────┐                               │
│              │  Main Orchestrator│                               │
│              └─────────▲─────────┘                               │
│                        │                                         │
│              ┌─────────▼─────────┐                               │
│              │   User Interface  │                               │
│              │   (CLI prompts)   │                               │
│              └─────────▲─────────┘                               │
│                        │                                         │
└────────────────────────┼─────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │  User   │
                    └─────────┘
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  User Interface (src/main.py)                                 │  │
│  │  • Rich console output (formatted prompts)                    │  │
│  │  • getpass for password input                                 │  │
│  │  • Progress indicators                                        │  │
│  │  • Status messages                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Orchestration Layer                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Main Orchestrator (src/main.py)                              │  │
│  │  • Initialize agents                                          │  │
│  │  • Route credential requests                                  │  │
│  │  • Top-level error handling                                   │  │
│  │  • Cleanup coordination                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                         Agent Layer                                 │
│  ┌─────────────────────────┐      ┌──────────────────────────────┐ │
│  │  BitwardenAgent         │      │  FlightBookingAgent          │ │
│  │  (src/agents/)          │      │  (src/agents/)               │ │
│  │                         │      │                              │ │
│  │  • Prompt for approval  │◄─────┤  • Launch browser            │ │
│  │  • Collect password     │      │  • Navigate to site          │ │
│  │  • Unlock vault         │      │  • Detect login form         │ │
│  │  • Search credentials   │      │  • Request credentials       │ │
│  │  • Lock vault           │      │  • Fill login form           │ │
│  │  • Generate audit logs  │─────►│  • Verify login success      │ │
│  │                         │      │  • Clear credentials         │ │
│  └────────┬────────────────┘      └──────────┬───────────────────┘ │
└───────────┼────────────────────────────────────┼─────────────────────┘
            │                                    │
┌───────────▼────────────────────────────────────▼─────────────────────┐
│                      Integration Layer                               │
│  ┌─────────────────────────┐      ┌──────────────────────────────┐  │
│  │  BitwardenCLI           │      │  Browser Automation          │  │
│  │  (src/utils/)           │      │  (Playwright)                │  │
│  │                         │      │                              │  │
│  │  • unlock(password)     │      │  • async browser launch      │  │
│  │  • list_items(domain)   │      │  • page.goto(url)            │  │
│  │  • lock()               │      │  • page.fill(selector)       │  │
│  │  • status()             │      │  • page.click(selector)      │  │
│  │                         │      │  • page.wait_for_selector()  │  │
│  └────────┬────────────────┘      └──────────┬───────────────────┘  │
└───────────┼────────────────────────────────────┼─────────────────────┘
            │                                    │
┌───────────▼────────────────────────────────────▼─────────────────────┐
│                      External Systems                                │
│  ┌─────────────────────────┐      ┌──────────────────────────────┐  │
│  │  Bitwarden CLI          │      │  Target Website              │  │
│  │  (subprocess)           │      │  (aa.com)                    │  │
│  │                         │      │                              │  │
│  │  • bw unlock            │      │  • Login page                │  │
│  │  • bw list items        │      │  • Form submission           │  │
│  │  • bw lock              │      │  • Success/error response    │  │
│  │  • bw status            │      │                              │  │
│  └─────────────────────────┘      └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Models

```
┌────────────────────────────────────────────────────────────────┐
│                     Core Data Models                           │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  CredentialRequest (dataclass)                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  agent_id: str           "flight-booking-001"      │  │ │
│  │  │  agent_name: str         "Flight Booking Agent"    │  │ │
│  │  │  domain: str             "aa.com"                  │  │ │
│  │  │  reason: str             "Logging in to search..." │  │ │
│  │  │  timestamp: datetime     2025-10-28T18:30:00Z      │  │ │
│  │  │  timeout: int            300                       │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  CredentialResponse (dataclass)                           │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  status: CredentialStatus                          │  │ │
│  │  │    → APPROVED / DENIED / NOT_FOUND / ERROR         │  │ │
│  │  │  credential: Optional[SecureCredential]            │  │ │
│  │  │  error_message: Optional[str]                      │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  SecureCredential (class with context manager)            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  _username: str          (private)                 │  │ │
│  │  │  _password: str          (private)                 │  │ │
│  │  │  _cleared: bool          False → True              │  │ │
│  │  │                                                     │  │ │
│  │  │  Methods:                                           │  │ │
│  │  │    username: property    (raises if cleared)       │  │ │
│  │  │    password: property    (raises if cleared)       │  │ │
│  │  │    clear()               Overwrite & delete        │  │ │
│  │  │    __enter__()           Return self               │  │ │
│  │  │    __exit__()            Call clear()              │  │ │
│  │  │    __del__()             Call clear()              │  │ │
│  │  │    __repr__()            Safe (no credentials)     │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     Security Boundaries                            │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  User's Trust Boundary                                        │ │
│  │  ┌────────────────────────────────────────────────────────┐  │ │
│  │  │  Bitwarden Vault (encrypted)                           │  │ │
│  │  │  • Master password known only to user                  │  │ │
│  │  │  • Vault locked by default                            │  │ │
│  │  │  • Credentials encrypted at rest                      │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  │                            ▲                                  │ │
│  │                            │ CLI unlock with password         │ │
│  │                            │                                  │ │
│  │  ┌─────────────────────────┴──────────────────────────────┐  │ │
│  │  │  Application Memory (transient)                        │  │ │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │ │
│  │  │  │  SecureCredential object                         │  │  │ │
│  │  │  │  • Exists only during use                        │  │  │ │
│  │  │  │  • Overwritten before deletion                   │  │  │ │
│  │  │  │  • Context manager ensures cleanup               │  │  │ │
│  │  │  └──────────────────────────────────────────────────┘  │  │ │
│  │  │                                                         │  │ │
│  │  │  Security Controls:                                     │  │ │
│  │  │  • No disk writes                                       │  │ │
│  │  │  • No logging                                           │  │ │
│  │  │  • Immediate clearing                                   │  │ │
│  │  │  • Context manager guarantees                           │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  │                            │                                  │ │
│  │                            │ Fill form fields                 │ │
│  │                            ▼                                  │ │
│  │  ┌────────────────────────────────────────────────────────┐  │ │
│  │  │  Browser Memory (Playwright)                           │  │ │
│  │  │  • Credentials in form fields briefly                  │  │ │
│  │  │  • Submitted over HTTPS                                │  │ │
│  │  │  • Browser context closed after use                    │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Audit Log (persistent, safe)                                 │ │
│  │  • Credential requests (metadata only)                        │ │
│  │  • User decisions (approve/deny)                              │ │
│  │  • Outcomes (success/failure)                                 │ │
│  │  • NO credential values                                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## Credential Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Credential Lifecycle                         │
│                                                                 │
│  1. CREATION (in BitwardenAgent)                                │
│     ┌──────────────────────────────────────────────────────┐   │
│     │  credential = SecureCredential(username, password)   │   │
│     └──────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  2. PASSING (to FlightBookingAgent)                             │
│     ┌──────────────────▼───────────────────────────────────┐   │
│     │  return CredentialResponse(                          │   │
│     │      status=APPROVED,                                │   │
│     │      credential=credential                           │   │
│     │  )                                                   │   │
│     └──────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  3. USAGE (in context manager)                                  │
│     ┌──────────────────▼───────────────────────────────────┐   │
│     │  with response.credential as cred:                   │   │
│     │      await browser.fill("input", cred.username)      │   │
│     │      await browser.fill("password", cred.password)   │   │
│     │      # credential used here                          │   │
│     └──────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  4. CLEARING (automatic on context exit)                        │
│     ┌──────────────────▼───────────────────────────────────┐   │
│     │  # __exit__ called automatically                     │   │
│     │  cred._username = "X" * len(cred._username)          │   │
│     │  cred._password = "X" * len(cred._password)          │   │
│     │  del cred._username                                  │   │
│     │  del cred._password                                  │   │
│     │  cred._cleared = True                                │   │
│     └──────────────────┬───────────────────────────────────┘   │
│                        │                                        │
│  5. GARBAGE COLLECTION                                          │
│     ┌──────────────────▼───────────────────────────────────┐   │
│     │  Python GC collects object                           │   │
│     │  Memory released                                     │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  Lifetime: ~10-30 seconds (from unlock to clearing)            │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Strategy                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Expected User Errors (Friendly Messages)                 │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • User denies request      → Exit gracefully      │  │  │
│  │  │  • Wrong vault password     → Retry prompt         │  │  │
│  │  │  • Credential not found     → Add to vault message │  │  │
│  │  │  • User cancels (Ctrl+C)    → Cleanup & exit      │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Expected System Errors (Recoverable)                     │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • CLI not installed        → Install instructions │  │  │
│  │  │  • Not logged into CLI      → Login instructions   │  │  │
│  │  │  • Browser launch failure   → Retry or report      │  │  │
│  │  │  • Network timeout          → Check connection     │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Unexpected Errors (Fatal)                                │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • JSON parse failure       → Log & exit           │  │  │
│  │  │  • Playwright crash         → Log & exit           │  │  │
│  │  │  • Unknown exception        → Log & exit           │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  All Error Paths:                                               │
│  • Ensure vault locked (try/finally)                           │
│  • Clear credentials from memory                               │
│  • Log error (without sensitive data)                          │
│  • Return meaningful exit code                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Testing Strategy                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Unit Tests (Fast, Isolated)                             │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • BitwardenCLI (mocked subprocess)                │  │  │
│  │  │  • SecureCredential (lifecycle testing)            │  │  │
│  │  │  • Data models (creation, validation)              │  │  │
│  │  │  • AuditLogger (file writes)                       │  │  │
│  │  │                                                     │  │  │
│  │  │  Tools: pytest, unittest.mock                      │  │  │
│  │  │  Coverage: >80%                                     │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Integration Tests (Real Components)                      │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • BitwardenAgent + Real CLI                       │  │  │
│  │  │  • FlightBookingAgent + Real Browser               │  │  │
│  │  │  • Error scenarios (wrong password, not found)     │  │  │
│  │  │  • Vault locking verification                      │  │  │
│  │  │                                                     │  │  │
│  │  │  Tools: pytest, real CLI, test vault               │  │  │
│  │  │  Coverage: Happy path + errors                     │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Security Tests (Validation)                              │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • Grep logs for credentials                       │  │  │
│  │  │  • Check vault locked after run                    │  │  │
│  │  │  • Find credential files on disk                   │  │  │
│  │  │  • Verify audit log completeness                   │  │  │
│  │  │                                                     │  │  │
│  │  │  Tools: pytest, grep, bw status                    │  │  │
│  │  │  Coverage: All security requirements               │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  End-to-End Tests (Complete Flow)                         │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  • Full POC execution                              │  │  │
│  │  │  • User interaction (manual)                       │  │  │
│  │  │  • Real Bitwarden + real browser                   │  │  │
│  │  │  • Happy path validation                           │  │  │
│  │  │                                                     │  │  │
│  │  │  Tools: pytest, manual validation                  │  │  │
│  │  │  Coverage: 1-2 complete flows                      │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Deployment (Single Machine)                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  User's Machine                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Python 3.8+ Runtime                               │  │  │
│  │  │  • src/ (application code)                         │  │  │
│  │  │  • .venv/ (virtual environment)                    │  │  │
│  │  │  • Playwright browsers (Chromium)                  │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Bitwarden CLI                                     │  │  │
│  │  │  • bw executable in PATH                           │  │  │
│  │  │  • User logged in (bw login)                       │  │  │
│  │  │  • Vault locked by default                         │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Generated Files                                   │  │  │
│  │  │  • credential_audit.log (audit trail)              │  │  │
│  │  │  • *.pyc (Python bytecode)                         │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Prerequisites:                                                 │
│  • Python 3.8+ installed                                        │
│  • Bitwarden CLI installed                                      │
│  • Internet connection (for aa.com, Bitwarden sync)            │
│  • Chromium browser (installed via Playwright)                 │
│                                                                 │
│  Not Required:                                                  │
│  • No database                                                  │
│  • No web server                                                │
│  • No container runtime                                         │
│  • No network services                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                     Technology Stack                            │
│                                                                 │
│  Language & Runtime:                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Python 3.8+                                              │  │
│  │  • Type hints for clarity                                 │  │
│  │  • Async/await for Playwright                             │  │
│  │  • Dataclasses for models                                 │  │
│  │  • Context managers for resource safety                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  External Dependencies:
  ┌────────────────────────────────────────────────────────┐
  │  Playwright (>=1.40.0)                                    │
  │  • Browser automation (async)                             │
  │  • Reliable selector waiting                              │
  │  • Multi-browser support (using Chromium)                 │
  │                                                            │
  │  playwright-stealth (>=1.0.0)                             │
  │  • Bot detection avoidance                                │
  │  • Removes webdriver property                             │
  │  • Randomizes browser fingerprint                         │
  │                                                            │
  │  Rich (>=13.7.0)                                          │
│  │  • Formatted CLI output                                   │  │
│  │  • Progress indicators                                    │  │
│  │  • Syntax highlighting                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Standard Library:                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • subprocess  → Bitwarden CLI execution                  │  │
│  │  • getpass     → Secure password input                    │  │
│  │  • asyncio     → Async/await support                      │  │
│  │  • dataclasses → Data models                              │  │
│  │  • logging     → Application logging                      │  │
│  │  • json        → CLI output parsing                       │  │
│  │  • datetime    → Timestamps                               │  │
│  │  • argparse    → CLI argument parsing                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  External Systems:                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Bitwarden CLI (bw)                                       │  │
│  │  • Version: Latest stable                                 │  │
│  │  • Commands: unlock, list, lock, status                   │  │
│  │  • Output: JSON format                                    │  │
│  │                                                            │  │
│  │  aa.com (American Airlines website)                       │  │
│  │  • Login page: https://www.aa.com/login                   │  │
│  │  • HTML form-based authentication                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architectural Principles Applied

### 1. Separation of Concerns
- **Presentation** (CLI) separate from **Business Logic** (Agents) separate from **Integration** (CLI/Browser)
- Each layer testable independently
- Changes in one layer don't cascade to others

### 2. Dependency Injection
- Agents accept dependencies in constructor (BitwardenCLI, Browser)
- Enables mocking for unit tests
- Facilitates different implementations (real vs. mock)

### 3. Fail-Safe Defaults
- Vault locked by default
- Credentials cleared by default (context manager)
- Deny by default (user must explicitly approve)

### 4. Defense in Depth
- Multiple layers of credential protection:
  - Bitwarden encryption
  - User approval required
  - In-memory only
  - Context manager cleanup
  - Vault locking after use

### 5. Explicit Over Implicit
- Context managers make credential lifetime explicit
- Approval flow clearly shown to user
- Error messages explicitly guide user action

### 6. Single Responsibility Principle
- BitwardenAgent: Only credential management
- FlightBookingAgent: Only browser automation
- BitwardenCLI: Only CLI subprocess interaction
- Each component has one reason to change

---

**End of Architecture Diagram Document**
