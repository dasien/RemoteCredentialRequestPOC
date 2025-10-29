---
enhancement: credential-request
agent: architect
task_id: task_1761664245_23534
timestamp: 2025-10-28T18:30:00Z
status: READY_FOR_IMPLEMENTATION
---

# Implementation Plan: AI Agent Credential Request System

## Executive Summary

This implementation plan provides comprehensive technical specifications and step-by-step guidance for building a secure credential management system that enables AI agents to request and receive user credentials from Bitwarden with explicit human approval.

**Architecture Approach**: Direct function call pattern with layered architecture
**Credential Passing**: In-process Python object references with context managers
**Session Management**: Per-request vault locking (unlock → retrieve → lock)
**Estimated Timeline**: 8-10 days following the phased approach

## Table of Contents

1. [Architectural Decisions](#architectural-decisions)
2. [System Architecture](#system-architecture)
3. [Component Specifications](#component-specifications)
4. [Data Structures and APIs](#data-structures-and-apis)
5. [Implementation Sequence](#implementation-sequence)
6. [Security Implementation](#security-implementation)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Testing Approach](#testing-approach)
9. [Acceptance Criteria](#acceptance-criteria)

---

## Architectural Decisions

### AD-1: Agent Communication Pattern

**Decision**: Direct function calls (in-process)

**Rationale**:
- **Simplicity**: POC scope requires minimal complexity; function calls are Python-native
- **Security**: Credentials stay in single process memory space, easier to control lifecycle
- **Performance**: No serialization overhead, immediate response
- **Debugging**: Simpler stack traces and error propagation

**Implementation**:
```python
# Main orchestrator directly calls agent methods
credential = bitwarden_agent.request_credential(domain="aa.com", reason="login")
```

**Upgrade Path**: Architecture supports future migration to message queue by wrapping function calls in message adapters.

**Trade-offs Accepted**:
- ❌ Cannot distribute agents across processes (acceptable for POC)
- ❌ Less isolation between agents (mitigated by clear interfaces)
- ✅ Faster development, easier debugging

---

### AD-2: Credential Passing Mechanism

**Decision**: Python object references with context manager protocol

**Rationale**:
- **Security**: Context manager guarantees cleanup even on exceptions
- **Simplicity**: Native Python pattern, no serialization
- **Safety**: `__exit__` method ensures credential clearing
- **Clarity**: Makes credential lifetime explicit in code

**Implementation**:
```python
class SecureCredential:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()  # Guaranteed cleanup
        return False
```

**Usage Pattern**:
```python
with bitwarden_agent.request_credential("aa.com") as cred:
    await browser.fill_login_form(cred.username, cred.password)
# Credential automatically cleared here
```

---

### AD-3: Vault Session Management

**Decision**: Per-request locking (unlock → retrieve → lock)

**Rationale**:
- **Security First**: Minimizes vault exposure window
- **Defense in Depth**: Each access requires fresh authentication
- **Failure Isolation**: Errors don't leave vault unlocked
- **Audit Clarity**: Each credential access is distinct event

**Implementation**:
```python
def request_credential(domain: str) -> Optional[SecureCredential]:
    session_key = None
    try:
        session_key = unlock_vault(password)
        credential = get_credential(domain, session_key)
        return credential
    finally:
        if session_key:
            lock_vault()  # Always lock, even on exception
```

**Session Mode Future**: Design supports optional session mode with timeout (see extensibility notes).

**Trade-offs Accepted**:
- ❌ User enters password for each request (acceptable for POC with single request)
- ✅ Maximum security, vault exposed for minimum duration

---

### AD-4: Error Handling Strategy

**Decision**: Hybrid approach using exceptions for unexpected errors, result objects for expected outcomes

**Rationale**:
- **Expected Outcomes**: User denial, missing credential, wrong password → Return status enum
- **Unexpected Errors**: CLI crash, network failure, parsing error → Raise exceptions
- **User Experience**: Expected outcomes get friendly messages, unexpected errors get technical details

**Implementation**:
```python
@dataclass
class CredentialResponse:
    status: CredentialStatus  # Enum: APPROVED, DENIED, NOT_FOUND, ERROR
    credential: Optional[SecureCredential]
    error_message: Optional[str]

# Expected outcome - return result object
if user_denied:
    return CredentialResponse(status=DENIED, credential=None, error_message=None)

# Unexpected error - raise exception
if cli_parse_failed:
    raise BitwardenCLIError(f"Failed to parse CLI output: {output}")
```

---

### AD-5: Browser Visibility Configuration

**Decision**: Configurable via CLI flag, default to headed mode

**Rationale**:
- **Demo Value**: Visible browser builds trust, shows what agent is doing
- **Debugging**: Easier to debug login flow with visible browser
- **Flexibility**: Headless mode available for testing/automation
- **Development**: Headed mode speeds up development iteration

**Implementation**:
```python
# CLI argument
parser.add_argument('--headless', action='store_true',
                    help='Run browser in headless mode')

# Browser launch
browser = await playwright.chromium.launch(headless=args.headless)
```

---

### AD-6: Credential Matching Strategy

**Decision**: Use Bitwarden CLI's built-in matching with `bw list items --search <domain>`

**Rationale**:
- **Leverage Existing**: Bitwarden already implements sophisticated URI matching
- **Maintainability**: Bitwarden handles subdomains, wildcards, exact matches
- **Compatibility**: Works with however users store credentials
- **Simplicity**: No custom matching logic to maintain

**Implementation**:
```python
# Let Bitwarden handle matching logic
result = subprocess.run(
    ["bw", "list", "items", "--search", domain, "--session", session_key],
    capture_output=True, text=True, check=True
)
items = json.loads(result.stdout)
# Take first match, or prompt user if multiple
```

**Multiple Matches**: If multiple credentials match, return first login item, log warning for user awareness.

---

## System Architecture

### Architectural Pattern

**Pattern**: Layered Architecture with Agent-Based Components

**Layers**:
1. **Presentation Layer**: CLI interface, user prompts, status display
2. **Agent Layer**: FlightBookingAgent, BitwardenAgent (business logic)
3. **Integration Layer**: BitwardenCLI wrapper, Browser automation
4. **External Systems**: Bitwarden CLI subprocess, Playwright browser

**Benefits**:
- Clear separation of concerns (UI, logic, integration)
- Testable in isolation (mock external systems)
- Maintainable (changes to CLI don't affect agent logic)
- Extensible (add new agents without changing infrastructure)

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│  • CLI prompt rendering (Rich library)                      │
│  • Password input (getpass)                                 │
│  • Progress indicators                                      │
│  • Status messages                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Main Orchestrator                          │
│  • Initialize agents                                        │
│  • Route credential requests                                │
│  • Coordinate flow                                          │
│  • Handle top-level errors                                  │
│  • Cleanup and shutdown                                     │
└─────┬──────────────────────────────┬────────────────────────┘
      │                              │
      ▼                              ▼
┌──────────────────────┐    ┌───────────────────────────────┐
│  FlightBookingAgent  │───▶│      BitwardenAgent           │
│                      │    │                               │
│  • Launch browser    │    │  • Request approval from user │
│  • Navigate to site  │    │  • Collect vault password     │
│  • Detect login form │    │  • Unlock vault (CLI)         │
│  • Request credential│◀───│  • Search for credential      │
│  • Fill login form   │    │  • Lock vault                 │
│  • Verify success    │    │  • Return credential          │
│  • Clear credential  │    │  • Generate audit log         │
└──────┬───────────────┘    └───────┬───────────────────────┘
       │                            │
       ▼                            ▼
┌──────────────────────┐    ┌───────────────────────────────┐
│  BrowserAutomation   │    │      BitwardenCLI             │
│    (Playwright)      │    │                               │
│                      │    │  • unlock(password) -> key    │
│  • async context     │    │  • list_items(domain, key)    │
│  • page navigation   │    │  • lock()                     │
│  • form interaction  │    │  • status()                   │
│  • selector waiting  │    │                               │
└──────────────────────┘    └───────────────────────────────┘
```

### Data Flow Sequence (Happy Path)

```
[User]           [Main]              [FlightAgent]        [BitwardenAgent]      [BitwardenCLI]     [Browser]

  │                │                       │                      │                     │              │
  │ Start POC      │                       │                      │                     │              │
  ├───────────────>│                       │                      │                     │              │
  │                │ initialize()          │                      │                     │              │
  │                ├──────────────────────>│                      │                     │              │
  │                │                       │ launch_browser()     │                     │              │
  │                │                       ├──────────────────────┼─────────────────────┼─────────────>│
  │                │                       │                      │                     │              │
  │                │                       │ navigate(aa.com)     │                     │              │
  │                │                       ├──────────────────────┼─────────────────────┼─────────────>│
  │                │                       │                      │                     │    [Page loads]
  │                │                       │                      │                     │              │
  │                │                       │ request_credential("aa.com", reason)       │              │
  │                │                       ├──────────────────────>                     │              │
  │                │                       │                      │ prompt_user()       │              │
  │<───────────────┼───────────────────────┼──────────────────────┤                     │              │
  │ "Approve? Y/N" │                       │                      │                     │              │
  │ Y              │                       │                      │                     │              │
  ├───────────────>│                       │                      │                     │              │
  │                │                       │                      │ get_password()      │              │
  │<───────────────┼───────────────────────┼──────────────────────┤                     │              │
  │ "Vault pwd:"   │                       │                      │                     │              │
  │ ********       │                       │                      │                     │              │
  ├───────────────>│                       │                      │                     │              │
  │                │                       │                      │ unlock(password)    │              │
  │                │                       │                      ├────────────────────>│              │
  │                │                       │                      │ session_key         │              │
  │                │                       │                      │<────────────────────┤              │
  │                │                       │                      │ list_items("aa.com")│              │
  │                │                       │                      ├────────────────────>│              │
  │                │                       │                      │ [{item}]            │              │
  │                │                       │                      │<────────────────────┤              │
  │                │                       │                      │ lock()              │              │
  │                │                       │                      ├────────────────────>│              │
  │                │                       │                      │ locked              │              │
  │                │                       │                      │<────────────────────┤              │
  │                │                       │ SecureCredential     │                     │              │
  │                │                       │<─────────────────────┤                     │              │
  │                │                       │ fill_form(cred)      │                     │              │
  │                │                       ├──────────────────────┼─────────────────────┼─────────────>│
  │                │                       │                      │                     │ [Submit form]
  │                │                       │                      │                     │              │
  │                │                       │ verify_success()     │                     │              │
  │                │                       ├──────────────────────┼─────────────────────┼─────────────>│
  │                │                       │ success=True         │                     │ [Check URL/content]
  │                │                       │                      │                     │              │
  │                │ task_complete(success)│                      │                     │              │
  │                │<──────────────────────┤                      │                     │              │
  │ "Login success"│                       │                      │                     │              │
  │<───────────────┤                       │                      │                     │              │
```

---

## Component Specifications

### 1. Main Orchestrator (`src/main.py`)

**Purpose**: Entry point and top-level coordinator

**Responsibilities**:
- Parse command-line arguments
- Initialize agents
- Coordinate credential request flow
- Handle Ctrl+C and cleanup
- Display status messages to user

**Key Functions**:

```python
def main(args: argparse.Namespace) -> int:
    """
    Main entry point for credential request POC.

    Returns:
        0 for success, non-zero for failure
    """
    try:
        # Setup logging (no credentials logged)
        setup_logging()

        # Initialize agents
        bitwarden_agent = BitwardenAgent()
        flight_agent = FlightBookingAgent(
            bitwarden_agent=bitwarden_agent,
            headless=args.headless
        )

        # Run flight booking task
        asyncio.run(flight_agent.run())

        logger.info("Task completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("User cancelled operation")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
    finally:
        # Ensure vault locked
        bitwarden_agent.ensure_locked()
```

**Configuration**:
```python
parser = argparse.ArgumentParser(description="AI Agent Credential Request POC")
parser.add_argument('--headless', action='store_true',
                    help='Run browser in headless mode')
parser.add_argument('--timeout', type=int, default=300,
                    help='User approval timeout in seconds')
parser.add_argument('--log-level', default='INFO',
                    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
```

**Files to Create**:
- `src/main.py`
- `src/__init__.py`

---

### 2. Bitwarden Agent (`src/agents/bitwarden_agent.py`)

**Purpose**: Handle credential requests and vault operations

**Responsibilities**:
- Display approval prompt to user
- Collect vault password securely
- Interface with Bitwarden CLI
- Search and retrieve credentials
- Ensure vault locking
- Generate audit logs

**Class Definition**:

```python
class BitwardenAgent:
    """Agent responsible for credential retrieval from Bitwarden vault."""

    def __init__(self, cli: Optional[BitwardenCLI] = None):
        """
        Initialize Bitwarden agent.

        Args:
            cli: BitwardenCLI instance (injected for testing)
        """
        self.cli = cli or BitwardenCLI()
        self.audit_logger = AuditLogger()
        self._session_key: Optional[str] = None

    def request_credential(
        self,
        domain: str,
        reason: str,
        agent_id: str,
        agent_name: str,
        timeout: int = 300
    ) -> CredentialResponse:
        """
        Request credential from user with approval flow.

        Args:
            domain: Domain name (e.g., "aa.com")
            reason: Human-readable reason for request
            agent_id: Unique identifier of requesting agent
            agent_name: Display name of requesting agent
            timeout: Seconds to wait for user approval

        Returns:
            CredentialResponse with status and optional credential
        """
        # Log request (no credentials)
        self.audit_logger.log_request(agent_id, domain, reason)

        # Display approval prompt
        approval = self._prompt_for_approval(
            agent_name=agent_name,
            domain=domain,
            reason=reason,
            timeout=timeout
        )

        if not approval:
            self.audit_logger.log_denial(agent_id, domain)
            return CredentialResponse(
                status=CredentialStatus.DENIED,
                credential=None,
                error_message="User denied credential access"
            )

        # Get vault password
        password = self._get_vault_password()
        if not password:
            return CredentialResponse(
                status=CredentialStatus.ERROR,
                credential=None,
                error_message="No password provided"
            )

        # Retrieve credential with automatic vault locking
        try:
            credential = self._retrieve_credential(domain, password)
            if credential:
                self.audit_logger.log_success(agent_id, domain)
                return CredentialResponse(
                    status=CredentialStatus.APPROVED,
                    credential=credential,
                    error_message=None
                )
            else:
                self.audit_logger.log_not_found(agent_id, domain)
                return CredentialResponse(
                    status=CredentialStatus.NOT_FOUND,
                    credential=None,
                    error_message=f"No credential found for {domain}"
                )
        except BitwardenCLIError as e:
            self.audit_logger.log_error(agent_id, domain, str(e))
            return CredentialResponse(
                status=CredentialStatus.ERROR,
                credential=None,
                error_message=str(e)
            )
        finally:
            # Clear password from memory
            password = "X" * len(password)
            del password

    def _prompt_for_approval(
        self,
        agent_name: str,
        domain: str,
        reason: str,
        timeout: int
    ) -> bool:
        """
        Display approval prompt and get user decision.

        Uses Rich library for formatted output.

        Returns:
            True if approved, False if denied
        """
        console = Console()

        panel = Panel(
            f"[bold cyan]Agent:[/bold cyan] {agent_name}\n"
            f"[bold cyan]Domain:[/bold cyan] {domain}\n"
            f"[bold cyan]Reason:[/bold cyan] {reason}\n\n"
            f"[bold yellow]Allow this agent to access your credentials?[/bold yellow]\n\n"
            f"[green]\\[Y][/green] Approve    [red]\\[N][/red] Deny    [dim]\\[Ctrl+C][/dim] Cancel",
            title="🔐 Credential Access Request",
            border_style="blue"
        )
        console.print(panel)

        response = Prompt.ask(
            "Decision",
            choices=["Y", "y", "N", "n"],
            default="N"
        )

        return response.upper() == "Y"

    def _get_vault_password(self) -> str:
        """
        Securely collect vault password from user.

        Returns:
            Password string (will be cleared after use)
        """
        return getpass.getpass("Enter Bitwarden vault password: ")

    def _retrieve_credential(
        self,
        domain: str,
        password: str
    ) -> Optional[SecureCredential]:
        """
        Unlock vault, retrieve credential, lock vault.

        Args:
            domain: Domain to search for
            password: Vault password

        Returns:
            SecureCredential if found, None otherwise

        Raises:
            BitwardenCLIError: If CLI operations fail
        """
        session_key = None
        try:
            # Unlock vault
            logger.info("Unlocking Bitwarden vault...")
            session_key = self.cli.unlock(password)

            # Search for credential
            logger.info(f"Searching vault for {domain}...")
            items = self.cli.list_items(domain, session_key)

            # Find first login item
            login_item = next(
                (item for item in items if item.get("type") == 1),  # type=1 is login
                None
            )

            if not login_item:
                return None

            # Extract credentials
            username = login_item.get("login", {}).get("username")
            password_value = login_item.get("login", {}).get("password")

            if not username or not password_value:
                raise BitwardenCLIError(
                    f"Credential for {domain} missing username or password"
                )

            return SecureCredential(username, password_value)

        finally:
            # Always lock vault
            if session_key:
                logger.info("Locking vault...")
                self.cli.lock()

    def ensure_locked(self) -> None:
        """Ensure vault is locked (called during cleanup)."""
        try:
            self.cli.lock()
        except Exception as e:
            logger.warning(f"Failed to lock vault during cleanup: {e}")
```

**Files to Create**:
- `src/agents/__init__.py`
- `src/agents/bitwarden_agent.py`

---

### 3. Flight Booking Agent (`src/agents/flight_booking_agent.py`)

**Purpose**: Automate browser interaction with aa.com

**Responsibilities**:
- Launch and manage browser instance
- Navigate to aa.com login page
- Detect login form
- Request credentials from Bitwarden agent
- Fill and submit login form
- Verify login success/failure
- Clear credentials from memory

**Class Definition**:

```python
"""
Flight Booking Agent implementation.

IMPORTANT: Uses playwright-stealth to avoid bot detection on aa.com.
"""
from playwright_stealth import stealth_async  

class FlightBookingAgent:
    """Agent responsible for aa.com login automation."""

    def __init__(
        self,
        bitwarden_agent: BitwardenAgent,
        headless: bool = False
    ):
        """
        Initialize flight booking agent.

        Args:
            bitwarden_agent: BitwardenAgent instance for credential requests
            headless: Whether to run browser in headless mode
        """
        self.bitwarden_agent = bitwarden_agent
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def run(self) -> bool:
        """
        Execute flight booking task (login to aa.com).

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Launch browser
            await self._launch_browser()

            # Navigate to login page
            logger.info("Navigating to aa.com...")
            await self.page.goto("https://www.aa.com/login")

            # Wait for login form
            await self._wait_for_login_form()

            # Request credentials
            logger.info("Requesting credentials from Bitwarden...")
            response = self.bitwarden_agent.request_credential(
                domain="aa.com",
                reason="Logging in to search and book flights",
                agent_id="flight-booking-001",
                agent_name="Flight Booking Agent"
            )

            # Handle response
            if response.status == CredentialStatus.DENIED:
                logger.info("User denied credential access")
                return False

            if response.status == CredentialStatus.NOT_FOUND:
                logger.error(f"Credential not found: {response.error_message}")
                return False

            if response.status == CredentialStatus.ERROR:
                logger.error(f"Error retrieving credential: {response.error_message}")
                return False

            # Fill login form with credential
            with response.credential as cred:
                success = await self._login(cred)

            return success

        finally:
            # Cleanup browser
            await self._cleanup_browser()

    async def _launch_browser(self) -> None:
    """
    Launch Playwright browser with stealth mode.
    
    Uses playwright-stealth to avoid bot detection on aa.com.
    """
    logger.info(f"Launching browser (headless={self.headless})...")
    self.playwright = await async_playwright().start()
    self.browser = await self.playwright.chromium.launch(
        headless=self.headless
    )
    self.page = await self.browser.new_page()
    
    # CRITICAL: Apply stealth mode to avoid bot detection
    await stealth_async(self.page)
    logger.debug("Stealth mode applied to browser")
    
    async def _wait_for_login_form(self) -> None:
        """Wait for login form to appear."""
        logger.info("Waiting for login form...")
        await self.page.wait_for_selector(
            'input[type="email"], input[name="username"]',
            timeout=30000
        )

    async def _login(self, credential: SecureCredential) -> bool:
        """
        Fill login form and submit.

        Args:
            credential: SecureCredential with username/password

        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Filling login form...")

            # Fill username
            await self.page.fill(
                'input[type="email"], input[name="username"]',
                credential.username
            )

            # Fill password
            await self.page.fill(
                'input[type="password"], input[name="password"]',
                credential.password
            )

            # Submit form
            logger.info("Submitting login form...")
            await self.page.click('button[type="submit"]')

            # Wait for navigation or error
            try:
                await self.page.wait_for_url(
                    lambda url: "login" not in url.lower(),
                    timeout=10000
                )
                logger.info("Login successful!")
                return True
            except TimeoutError:
                # Check for error message
                error = await self.page.query_selector('.error, .alert-danger')
                if error:
                    error_text = await error.text_content()
                    logger.error(f"Login failed: {error_text}")
                else:
                    logger.error("Login failed: Still on login page")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def _cleanup_browser(self) -> None:
        """Close browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

**Files to Create**:
- `src/agents/flight_booking_agent.py`

---

### 4. Bitwarden CLI Wrapper (`src/utils/bitwarden_cli.py`)

**Purpose**: Interface with Bitwarden CLI subprocess

**Responsibilities**:
- Execute Bitwarden CLI commands
- Parse JSON output
- Handle CLI errors with meaningful messages
- Validate CLI installation and user login state

**Class Definition**:

```python
class BitwardenCLI:
    """Wrapper for Bitwarden CLI subprocess operations."""

    def __init__(self, cli_path: str = "bw"):
        """
        Initialize Bitwarden CLI wrapper.

        Args:
            cli_path: Path to bw executable (default: "bw" in PATH)
        """
        self.cli_path = cli_path
        self._validate_cli_installed()

    def _validate_cli_installed(self) -> None:
        """
        Verify Bitwarden CLI is installed and accessible.

        Raises:
            BitwardenCLIError: If CLI not found or not logged in
        """
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            logger.debug(f"Bitwarden CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise BitwardenCLIError(
                f"Bitwarden CLI not found at '{self.cli_path}'. "
                "Please install from https://bitwarden.com/help/cli/"
            )
        except subprocess.TimeoutExpired:
            raise BitwardenCLIError("Bitwarden CLI command timed out")

        # Check login status
        self._check_login_status()

    def _check_login_status(self) -> None:
        """
        Verify user is logged into Bitwarden CLI.

        Raises:
            BitwardenCLIError: If user not logged in
        """
        try:
            result = subprocess.run(
                [self.cli_path, "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            status = json.loads(result.stdout)

            if status.get("status") == "unauthenticated":
                raise BitwardenCLIError(
                    "Not logged into Bitwarden CLI. "
                    "Please run 'bw login' first."
                )

        except json.JSONDecodeError as e:
            raise BitwardenCLIError(f"Failed to parse CLI status: {e}")

    def unlock(self, password: str) -> str:
        """
        Unlock Bitwarden vault.

        Args:
            password: Master password

        Returns:
            Session key for subsequent operations

        Raises:
            BitwardenCLIError: If unlock fails
        """
        try:
            result = subprocess.run(
                [self.cli_path, "unlock", password, "--raw"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if "Invalid master password" in result.stderr:
                    raise BitwardenCLIError("Invalid master password")
                else:
                    raise BitwardenCLIError(
                        f"Failed to unlock vault: {result.stderr}"
                    )

            session_key = result.stdout.strip()
            if not session_key:
                raise BitwardenCLIError("Unlock returned empty session key")

            return session_key

        except subprocess.TimeoutExpired:
            raise BitwardenCLIError("Vault unlock timed out")

    def list_items(self, search: str, session_key: str) -> List[Dict]:
        """
        Search vault for items matching domain.

        Args:
            search: Search term (domain name)
            session_key: Session key from unlock()

        Returns:
            List of matching vault items

        Raises:
            BitwardenCLIError: If search fails
        """
        try:
            result = subprocess.run(
                [
                    self.cli_path, "list", "items",
                    "--search", search,
                    "--session", session_key
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            items = json.loads(result.stdout)
            if not isinstance(items, list):
                raise BitwardenCLIError(
                    f"Expected list from CLI, got {type(items)}"
                )

            return items

        except subprocess.CalledProcessError as e:
            raise BitwardenCLIError(f"Failed to list items: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise BitwardenCLIError("Item search timed out")
        except json.JSONDecodeError as e:
            raise BitwardenCLIError(f"Failed to parse CLI output: {e}")

    def lock(self) -> None:
        """
        Lock Bitwarden vault.

        Raises:
            BitwardenCLIError: If lock fails
        """
        try:
            subprocess.run(
                [self.cli_path, "lock"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
        except subprocess.CalledProcessError as e:
            raise BitwardenCLIError(f"Failed to lock vault: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise BitwardenCLIError("Vault lock timed out")

    def status(self) -> Dict:
        """
        Get current Bitwarden CLI status.

        Returns:
            Status dictionary with 'status' key

        Raises:
            BitwardenCLIError: If status check fails
        """
        try:
            result = subprocess.run(
                [self.cli_path, "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return json.loads(result.stdout)
        except Exception as e:
            raise BitwardenCLIError(f"Failed to get status: {e}")


class BitwardenCLIError(Exception):
    """Exception raised for Bitwarden CLI errors."""
    pass
```

**Files to Create**:
- `src/utils/__init__.py`
- `src/utils/bitwarden_cli.py`

---

### 5. Secure Credential Handler (`src/utils/credential_handler.py`)

**Purpose**: Represent credentials with secure handling

**Responsibilities**:
- Store username and password
- Implement context manager for automatic cleanup
- Prevent credential leakage in string representation
- Overwrite memory on cleanup

**Class Definition**:

```python
class SecureCredential:
    """
    Secure credential container with automatic cleanup.

    Usage:
        with credential as cred:
            # Use cred.username and cred.password
        # Credential automatically cleared here
    """

    def __init__(self, username: str, password: str):
        """
        Create secure credential.

        Args:
            username: Account username
            password: Account password
        """
        self._username = username
        self._password = password
        self._cleared = False

    @property
    def username(self) -> str:
        """Get username (raises if cleared)."""
        if self._cleared:
            raise ValueError("Credential has been cleared")
        return self._username

    @property
    def password(self) -> str:
        """Get password (raises if cleared)."""
        if self._cleared:
            raise ValueError("Credential has been cleared")
        return self._password

    def clear(self) -> None:
        """
        Clear credential from memory.

        Overwrites strings with 'X' characters before deletion.
        """
        if self._cleared:
            return

        # Overwrite strings in memory (best effort)
        if self._username:
            self._username = "X" * len(self._username)
        if self._password:
            self._password = "X" * len(self._password)

        self._cleared = True

        # Delete references
        del self._username
        del self._password

    def __enter__(self) -> 'SecureCredential':
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> bool:
        """Exit context manager and clear credential."""
        self.clear()
        return False  # Don't suppress exceptions

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.clear()
        except:
            pass  # Ignore errors in __del__

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        status = "cleared" if self._cleared else "active"
        return f"SecureCredential(status={status})"

    def __str__(self) -> str:
        """Safe string representation without credentials."""
        return self.__repr__()
```

**Files to Create**:
- `src/utils/credential_handler.py`

---

### 6. Audit Logger (`src/utils/audit_logger.py`)

**Purpose**: Log credential access events without logging credentials

**Responsibilities**:
- Log credential requests with metadata
- Log user decisions (approve/deny)
- Log outcomes (success/failure)
- Never log credential values
- Timestamp all entries

**Class Definition**:

```python
class AuditLogger:
    """
    Audit logger for credential access events.

    CRITICAL: Never logs credential values.
    """

    def __init__(self, log_file: str = "credential_audit.log"):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
        """
        self.log_file = log_file
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure audit logger."""
        self.logger = logging.getLogger("credential_audit")
        self.logger.setLevel(logging.INFO)

        # File handler (append mode)
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%SZ'
            )
        )
        self.logger.addHandler(handler)

    def log_request(
        self,
        agent_id: str,
        domain: str,
        reason: str
    ) -> None:
        """
        Log credential request.

        Args:
            agent_id: Requesting agent identifier
            domain: Domain requested
            reason: Reason for request
        """
        self.logger.info(
            f"REQUEST | agent={agent_id} | domain={domain} | reason={reason}"
        )

    def log_denial(self, agent_id: str, domain: str) -> None:
        """Log user denial of credential request."""
        self.logger.info(
            f"DENIED | agent={agent_id} | domain={domain}"
        )

    def log_success(self, agent_id: str, domain: str) -> None:
        """Log successful credential retrieval and use."""
        self.logger.info(
            f"SUCCESS | agent={agent_id} | domain={domain}"
        )

    def log_not_found(self, agent_id: str, domain: str) -> None:
        """Log credential not found in vault."""
        self.logger.warning(
            f"NOT_FOUND | agent={agent_id} | domain={domain}"
        )

    def log_error(
        self,
        agent_id: str,
        domain: str,
        error_message: str
    ) -> None:
        """
        Log error during credential retrieval.

        Args:
            agent_id: Requesting agent identifier
            domain: Domain requested
            error_message: Sanitized error message (no credentials)
        """
        # Sanitize error message (remove any potential credential data)
        safe_message = error_message[:200]  # Limit length
        self.logger.error(
            f"ERROR | agent={agent_id} | domain={domain} | error={safe_message}"
        )
```

**Files to Create**:
- `src/utils/audit_logger.py`

---

## Data Structures and APIs

### CredentialRequest (dataclass)

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CredentialRequest:
    """
    Request for credential from an agent.

    Attributes:
        agent_id: Unique identifier (e.g., "flight-booking-001")
        agent_name: Human-readable name for prompts
        domain: Domain name (e.g., "aa.com")
        reason: Human-readable explanation
        timestamp: When request was made
        timeout: Seconds to wait for approval
    """
    agent_id: str
    agent_name: str
    domain: str
    reason: str
    timestamp: datetime
    timeout: int = 300
```

### CredentialResponse (dataclass)

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class CredentialStatus(Enum):
    """Status of credential request."""
    APPROVED = "approved"      # User approved, credential retrieved
    DENIED = "denied"          # User denied request
    NOT_FOUND = "not_found"    # Credential not in vault
    ERROR = "error"            # Error during retrieval

@dataclass
class CredentialResponse:
    """
    Response to credential request.

    Attributes:
        status: Outcome of request
        credential: SecureCredential if approved, None otherwise
        error_message: Error details if status is ERROR or NOT_FOUND
    """
    status: CredentialStatus
    credential: Optional[SecureCredential]
    error_message: Optional[str]
```

**Files to Create**:
- `src/models/__init__.py`
- `src/models/credential_request.py`
- `src/models/credential_response.py`

---

## Implementation Sequence

### Phase 1: Foundation Setup (Days 1-2)

**Goal**: Establish project infrastructure and validate external dependencies

#### Step 1.1: Project Structure

Create directory structure:
```
AgentCredentialRequest/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── bitwarden_agent.py
│   │   └── flight_booking_agent.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── credential_request.py
│   │   └── credential_response.py
│   └── utils/
│       ├── __init__.py
│       ├── bitwarden_cli.py
│       ├── credential_handler.py
│       └── audit_logger.py
├── tests/
│   ├── __init__.py
│   ├── test_bitwarden_cli.py
│   ├── test_credential_handler.py
│   └── test_agents.py
├── requirements.txt
├── README.md
├── .gitignore
└── credential_audit.log (generated at runtime)
```

**Command**:
```bash
cd /Users/bgentry/Source/repos/AgentCredentialRequest
mkdir -p src/agents src/models src/utils tests
touch src/__init__.py src/agents/__init__.py src/models/__init__.py src/utils/__init__.py tests/__init__.py
```

#### Step 1.2: Dependencies File

Create `requirements.txt`:
```
playwright>=1.40.0
playwright-stealth>=1.0.0
rich>=13.7.0
```

**Command**:
```bash
pip install -r requirements.txt
playwright install chromium

# Verify playwright-stealth installed
python -c "import playwright_stealth; print('playwright-stealth OK')"
```

#### Step 1.3: Git Setup

Create `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# Logs (audit log should be excluded for security)
*.log

# Bitwarden
.bitwarden/

# OS
.DS_Store
Thumbs.db
```

#### Step 1.4: Bitwarden CLI Validation

**Test Commands**:
```bash
# Verify CLI installed
bw --version

# Check login status
bw status

# If not logged in:
bw login

# Create test credential (manual)
# 1. Open Bitwarden web vault or desktop app
# 2. Create new login item:
#    - Name: "American Airlines Test"
#    - Username: "test-user@example.com"
#    - Password: "TestPassword123!"
#    - URI: "aa.com"
# 3. Save item

# Verify credential accessible
bw unlock  # Enter password
export BW_SESSION="<session-key-from-output>"
bw list items --search aa.com
bw lock
```

**Validation Criteria**:
- ✅ `bw --version` returns version number
- ✅ `bw status` shows "authenticated" or "locked"
- ✅ Test credential for aa.com exists in vault
- ✅ Can retrieve credential via CLI

#### Step 1.5: Basic Logging Setup

Create `src/utils/logging_config.py`:
```python
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """
    Configure application logging.

    CRITICAL: Logs must never contain credential values.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Ensure no sensitive data in logs
    logging.getLogger().addFilter(SensitiveDataFilter())

class SensitiveDataFilter(logging.Filter):
    """Filter to block sensitive data from logs."""

    SENSITIVE_PATTERNS = [
        "password", "passwd", "pwd",
        "secret", "token", "key",
        "credential", "auth"
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Block log records that might contain sensitive data."""
        message_lower = record.getMessage().lower()

        # Block if message contains sensitive keywords with "="
        # This catches "password=foo" but not "password input"
        for pattern in self.SENSITIVE_PATTERNS:
            if f"{pattern}=" in message_lower or f'"{pattern}"' in message_lower:
                record.msg = f"[BLOCKED: Message contained sensitive data]"
                return True

        return True
```

---

### Phase 2: Core Components (Days 3-5)

#### Step 2.1: Implement BitwardenCLI Wrapper (Day 3)

**File**: `src/utils/bitwarden_cli.py`

**Implementation Order**:
1. Create `BitwardenCLIError` exception class
2. Implement `__init__` and `_validate_cli_installed()`
3. Implement `_check_login_status()`
4. Implement `unlock()` method
5. Implement `list_items()` method
6. Implement `lock()` method
7. Implement `status()` method

**Testing**:
```python
# tests/test_bitwarden_cli.py
import pytest
from unittest.mock import Mock, patch
from src.utils.bitwarden_cli import BitwardenCLI, BitwardenCLIError

def test_cli_not_installed():
    """Test error when CLI not found."""
    with patch('subprocess.run', side_effect=FileNotFoundError):
        with pytest.raises(BitwardenCLIError, match="not found"):
            BitwardenCLI()

def test_unlock_success():
    """Test successful vault unlock."""
    cli = BitwardenCLI()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test-session-key\n",
            stderr=""
        )
        session_key = cli.unlock("password123")
        assert session_key == "test-session-key"

def test_unlock_wrong_password():
    """Test unlock with wrong password."""
    cli = BitwardenCLI()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Invalid master password"
        )
        with pytest.raises(BitwardenCLIError, match="Invalid master password"):
            cli.unlock("wrongpassword")

# Run tests
pytest tests/test_bitwarden_cli.py -v
```

**Manual Validation**:
```python
# Test with real Bitwarden CLI
from src.utils.bitwarden_cli import BitwardenCLI
import getpass

cli = BitwardenCLI()
password = getpass.getpass("Vault password: ")
session = cli.unlock(password)
print(f"Session key: {session[:10]}...")
items = cli.list_items("aa.com", session)
print(f"Found {len(items)} items")
cli.lock()
print("Vault locked")
```

#### Step 2.2: Implement SecureCredential (Day 3)

**File**: `src/utils/credential_handler.py`

**Implementation**: Use class definition from Component Specifications section

**Testing**:
```python
# tests/test_credential_handler.py
import pytest
from src.utils.credential_handler import SecureCredential

def test_credential_creation():
    """Test creating credential."""
    cred = SecureCredential("user@example.com", "pass123")
    assert cred.username == "user@example.com"
    assert cred.password == "pass123"

def test_credential_context_manager():
    """Test automatic cleanup with context manager."""
    cred = SecureCredential("user", "pass")
    with cred as c:
        assert c.username == "user"
    # After exit, should be cleared
    with pytest.raises(ValueError, match="cleared"):
        _ = cred.username

def test_credential_clear():
    """Test manual clear."""
    cred = SecureCredential("user", "pass")
    cred.clear()
    with pytest.raises(ValueError):
        _ = cred.password

def test_credential_repr_safe():
    """Test __repr__ doesn't leak credentials."""
    cred = SecureCredential("secretuser", "secretpass")
    repr_str = repr(cred)
    assert "secretuser" not in repr_str
    assert "secretpass" not in repr_str
    assert "SecureCredential" in repr_str

pytest tests/test_credential_handler.py -v
```

#### Step 2.3: Implement Data Models (Day 4)

**Files**:
- `src/models/credential_request.py`
- `src/models/credential_response.py`

**Implementation**: Use dataclass definitions from Data Structures section

**Testing**:
```python
# tests/test_models.py
from datetime import datetime
from src.models.credential_request import CredentialRequest
from src.models.credential_response import CredentialResponse, CredentialStatus
from src.utils.credential_handler import SecureCredential

def test_credential_request_creation():
    """Test creating credential request."""
    req = CredentialRequest(
        agent_id="test-001",
        agent_name="Test Agent",
        domain="example.com",
        reason="Testing",
        timestamp=datetime.utcnow(),
        timeout=300
    )
    assert req.domain == "example.com"
    assert req.timeout == 300

def test_credential_response_approved():
    """Test approved response."""
    cred = SecureCredential("user", "pass")
    resp = CredentialResponse(
        status=CredentialStatus.APPROVED,
        credential=cred,
        error_message=None
    )
    assert resp.status == CredentialStatus.APPROVED
    assert resp.credential is not None

def test_credential_response_denied():
    """Test denied response."""
    resp = CredentialResponse(
        status=CredentialStatus.DENIED,
        credential=None,
        error_message="User denied"
    )
    assert resp.status == CredentialStatus.DENIED
    assert resp.credential is None

pytest tests/test_models.py -v
```

#### Step 2.4: Implement AuditLogger (Day 4)

**File**: `src/utils/audit_logger.py`

**Implementation**: Use class definition from Component Specifications section

**Testing**:
```python
# tests/test_audit_logger.py
import os
import pytest
from src.utils.audit_logger import AuditLogger

@pytest.fixture
def temp_audit_log(tmp_path):
    """Create temporary audit log file."""
    log_file = tmp_path / "test_audit.log"
    return str(log_file)

def test_audit_logger_request(temp_audit_log):
    """Test logging credential request."""
    logger = AuditLogger(temp_audit_log)
    logger.log_request("agent-001", "example.com", "Testing")

    with open(temp_audit_log) as f:
        content = f.read()
        assert "REQUEST" in content
        assert "agent=agent-001" in content
        assert "domain=example.com" in content

def test_audit_logger_no_credential_leak(temp_audit_log):
    """Test that audit log never contains credentials."""
    logger = AuditLogger(temp_audit_log)
    logger.log_request("agent-001", "example.com", "password=secret123")
    logger.log_success("agent-001", "example.com")

    with open(temp_audit_log) as f:
        content = f.read()
        # Should contain metadata but not actual credentials
        assert "secret123" not in content  # Should not leak password
        assert "agent-001" in content

pytest tests/test_audit_logger.py -v
```

#### Step 2.5: Implement BitwardenAgent (Day 5)

**File**: `src/agents/bitwarden_agent.py`

**Implementation**: Use class definition from Component Specifications section

**Dependencies**:
```bash
pip install rich  # For formatted prompts
```

**Testing**:
```python
# tests/test_bitwarden_agent.py
import pytest
from unittest.mock import Mock, patch
from src.agents.bitwarden_agent import BitwardenAgent
from src.models.credential_response import CredentialStatus

@pytest.fixture
def mock_cli():
    """Create mock BitwardenCLI."""
    cli = Mock()
    cli.unlock.return_value = "test-session-key"
    cli.list_items.return_value = [
        {
            "type": 1,  # Login type
            "login": {
                "username": "test@example.com",
                "password": "testpass123"
            }
        }
    ]
    return cli

def test_request_credential_user_denies(mock_cli):
    """Test user denial."""
    agent = BitwardenAgent(cli=mock_cli)

    with patch.object(agent, '_prompt_for_approval', return_value=False):
        response = agent.request_credential(
            domain="example.com",
            reason="Testing",
            agent_id="test-001",
            agent_name="Test Agent"
        )

    assert response.status == CredentialStatus.DENIED
    assert response.credential is None

def test_request_credential_success(mock_cli):
    """Test successful credential retrieval."""
    agent = BitwardenAgent(cli=mock_cli)

    with patch.object(agent, '_prompt_for_approval', return_value=True):
        with patch.object(agent, '_get_vault_password', return_value="masterpass"):
            response = agent.request_credential(
                domain="example.com",
                reason="Testing",
                agent_id="test-001",
                agent_name="Test Agent"
            )

    assert response.status == CredentialStatus.APPROVED
    assert response.credential is not None
    assert response.credential.username == "test@example.com"

pytest tests/test_bitwarden_agent.py -v
```

#### Step 2.6: Implement FlightBookingAgent (Day 5)

**CRITICAL PREREQUISITE**: Install playwright-stealth
```bash
pip install playwright-stealth
```

**Why**: aa.com (and most modern websites) use bot detection. Without stealth mode, login attempts may be blocked even with correct credentials, causing the POC to appear broken.

**File**: `src/agents/flight_booking_agent.py`

**Implementation**: Use class definition from Component Specifications section

**Note**: This component requires async/await testing, which is more complex. Start with basic structure, test manually first.

**Manual Testing**:
```python
# test_flight_agent_manual.py
import asyncio
from src.agents.flight_booking_agent import FlightBookingAgent
from src.agents.bitwarden_agent import BitwardenAgent

async def test_navigation():
    """Manual test of browser navigation."""
    bitwarden = BitwardenAgent()
    flight = FlightBookingAgent(bitwarden, headless=False)

    await flight._launch_browser()
    await flight.page.goto("https://www.aa.com/login")
    print("Navigated to aa.com login")

    await asyncio.sleep(5)  # Let us see the page

    await flight._cleanup_browser()
    print("Browser closed")

asyncio.run(test_navigation())
```

---

### Phase 3: Integration (Days 6-7)

#### Step 3.1: Implement Main Orchestrator (Day 6)

**File**: `src/main.py`

**Implementation**:
```python
#!/usr/bin/env python3
"""
AI Agent Credential Request POC - Main Entry Point

This POC demonstrates secure credential management for AI agents
using Bitwarden with human-in-the-loop approval.
"""
import argparse
import asyncio
import logging
import sys
from typing import Optional

from src.agents.bitwarden_agent import BitwardenAgent
from src.agents.flight_booking_agent import FlightBookingAgent
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Agent Credential Request POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with visible browser (default)
  python -m src.main

  # Run in headless mode
  python -m src.main --headless

  # Enable debug logging
  python -m src.main --log-level DEBUG
        """
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='User approval timeout in seconds (default: 300)'
    )

    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )

    return parser.parse_args()


async def run_poc(args: argparse.Namespace) -> bool:
    """
    Run the credential request POC.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if successful, False otherwise
    """
    bitwarden_agent: Optional[BitwardenAgent] = None
    flight_agent: Optional[FlightBookingAgent] = None

    try:
        logger.info("=== AI Agent Credential Request POC ===")
        logger.info("Initializing agents...")

        # Initialize agents
        bitwarden_agent = BitwardenAgent()
        flight_agent = FlightBookingAgent(
            bitwarden_agent=bitwarden_agent,
            headless=args.headless
        )

        # Run flight booking task
        logger.info("Starting flight booking agent...")
        success = await flight_agent.run()

        if success:
            logger.info("✓ POC completed successfully")
            return True
        else:
            logger.warning("✗ POC completed with errors")
            return False

    except KeyboardInterrupt:
        logger.info("User cancelled operation (Ctrl+C)")
        return False

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return False

    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if bitwarden_agent:
            bitwarden_agent.ensure_locked()
        logger.info("Cleanup complete")


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Run POC
    success = asyncio.run(run_poc(args))

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
```

**Testing**:
```bash
# Test with --help
python -m src.main --help

# Test dry run (will prompt for credentials)
python -m src.main --log-level DEBUG

# Test with real credentials (requires Bitwarden setup)
python -m src.main
```

#### Step 3.2: End-to-End Integration Testing (Day 7)

**Test Script**: `tests/integration/test_e2e.py`

```python
"""
End-to-end integration tests.

NOTE: These tests require:
1. Bitwarden CLI installed and logged in
2. Test credential for aa.com in vault
3. User interaction (password input, approval)
"""
import asyncio
import pytest
from src.main import run_poc
import argparse

@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_happy_path():
    """
    Test complete happy path flow.

    Manual steps required:
    1. Ensure test credential exists for aa.com
    2. Approve when prompted
    3. Enter vault password
    """
    args = argparse.Namespace(
        headless=False,
        timeout=300,
        log_level='INFO'
    )

    success = await run_poc(args)
    assert success, "E2E test should complete successfully"

# Run with: pytest tests/integration/test_e2e.py -v -s -m integration
```

**Manual Test Checklist**:
- [ ] Start POC with `python -m src.main`
- [ ] See "Credential Access Request" prompt
- [ ] Approve request (Y)
- [ ] Enter vault password
- [ ] See "Unlocking Bitwarden vault..." message
- [ ] See "Searching vault for aa.com..." message
- [ ] See browser launch and navigate to aa.com
- [ ] See login form auto-fill
- [ ] See login form submit
- [ ] See login success (URL changes from /login)
- [ ] See "Login successful!" message
- [ ] See "Locking vault..." message
- [ ] See "POC completed successfully" message
- [ ] Verify vault locked: `bw status` shows "locked"
- [ ] Verify audit log: `cat credential_audit.log`

---

### Phase 4: Testing and Hardening (Days 8-9)

#### Step 4.1: Security Validation (Day 8)

**Security Test Script**: `tests/security/test_credential_leakage.py`

```python
"""
Security tests to validate no credential leakage.
"""
import os
import pytest
import subprocess
from pathlib import Path

def test_no_credentials_in_logs():
    """Verify credentials never appear in logs."""
    # Run POC (requires manual interaction)
    # Then check logs

    log_files = [
        "credential_audit.log",
        # Add any other log files
    ]

    # Known test credentials (should NOT appear in logs)
    sensitive_patterns = [
        "TestPassword123!",
        "test-user@example.com",
    ]

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        with open(log_file) as f:
            content = f.read()
            for pattern in sensitive_patterns:
                assert pattern not in content, \
                    f"Credential leaked in {log_file}: {pattern}"

def test_vault_locked_after_completion():
    """Verify vault is locked after POC runs."""
    result = subprocess.run(
        ["bw", "status"],
        capture_output=True,
        text=True
    )

    status = result.stdout
    # Vault should be locked or need login
    assert '"locked"' in status or '"unauthenticated"' in status

def test_no_credential_files_created():
    """Verify no credential files written to disk."""
    # Check for common credential file patterns
    credential_files = list(Path(".").rglob("*credential*.txt"))
    credential_files += list(Path(".").rglob("*password*.txt"))
    credential_files += list(Path(".").rglob("*.key"))

    # Filter out legitimate files (this test file, source code)
    suspicious_files = [
        f for f in credential_files
        if f.suffix in ['.txt', '.key', '.secret']
    ]

    assert len(suspicious_files) == 0, \
        f"Found suspicious credential files: {suspicious_files}"

# Run: pytest tests/security/ -v
```

#### Step 4.2: Error Scenario Testing (Day 8)

**Error Test Script**: `tests/integration/test_error_scenarios.py`

```python
"""
Test error handling scenarios.
"""
import pytest
from unittest.mock import Mock, patch
from src.agents.bitwarden_agent import BitwardenAgent
from src.utils.bitwarden_cli import BitwardenCLIError

def test_wrong_vault_password():
    """Test handling of wrong vault password."""
    cli = Mock()
    cli.unlock.side_effect = BitwardenCLIError("Invalid master password")

    agent = BitwardenAgent(cli=cli)

    with patch.object(agent, '_prompt_for_approval', return_value=True):
        with patch.object(agent, '_get_vault_password', return_value="wrongpass"):
            response = agent.request_credential(
                domain="example.com",
                reason="Testing",
                agent_id="test-001",
                agent_name="Test Agent"
            )

    assert response.status.value == "error"
    assert "Invalid master password" in response.error_message

def test_credential_not_found():
    """Test handling of missing credential."""
    cli = Mock()
    cli.unlock.return_value = "session-key"
    cli.list_items.return_value = []  # No items found

    agent = BitwardenAgent(cli=cli)

    with patch.object(agent, '_prompt_for_approval', return_value=True):
        with patch.object(agent, '_get_vault_password', return_value="password"):
            response = agent.request_credential(
                domain="nonexistent.com",
                reason="Testing",
                agent_id="test-001",
                agent_name="Test Agent"
            )

    assert response.status.value == "not_found"
    assert "nonexistent.com" in response.error_message

# Run: pytest tests/integration/test_error_scenarios.py -v
```

#### Step 4.3: Documentation (Day 9)

**Create README.md**:

```markdown
# AI Agent Credential Request System - POC

Secure credential management for AI agents using Bitwarden with human-in-the-loop approval.

## Overview

This POC demonstrates a credential request system where:
1. AI agent needs to log into a website (aa.com)
2. Agent requests credentials from Bitwarden
3. User explicitly approves request
4. Credentials retrieved and used securely
5. Vault locked after use

## Prerequisites

1. **Python 3.8+**
2. **Bitwarden CLI** installed and configured
   ```bash
   # Install Bitwarden CLI
   # macOS: brew install bitwarden-cli
   # Windows: choco install bitwarden-cli
   # Linux: snap install bw

   # Login to Bitwarden
   bw login
   ```

3. **Test Credential** in Bitwarden vault for aa.com
   - Create a login item in your Bitwarden vault
   - Name: "American Airlines Test"
   - Username: test-user@example.com (or your test username)
   - Password: (your test password)
   - URI: aa.com

## Installation

1. Clone repository
   ```bash
   git clone <repo-url>
   cd AgentCredentialRequest
   ```

2. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browser
   ```bash
   playwright install chromium
   ```

## Usage

**Run POC with visible browser** (recommended for first run):
```bash
python -m src.main
```

**Run in headless mode**:
```bash
python -m src.main --headless
```

**Enable debug logging**:
```bash
python -m src.main --log-level DEBUG
```

## What Happens During Execution

1. **Agent starts**: Flight booking agent launches browser
2. **Navigation**: Browser navigates to aa.com login page
3. **Credential request**: Agent requests credentials from Bitwarden
4. **User approval**: You see prompt asking to approve request
5. **Password input**: You enter your Bitwarden vault password (hidden)
6. **Vault unlock**: System unlocks vault with your password
7. **Credential retrieval**: System searches for aa.com credential
8. **Vault locking**: System locks vault immediately
9. **Login**: Browser auto-fills and submits login form
10. **Verification**: System verifies login success
11. **Cleanup**: Credentials cleared from memory, browser closed

## Security Features

✅ **Zero Persistence**: Credentials never written to disk
✅ **Memory Cleanup**: Credentials cleared immediately after use
✅ **Vault Locking**: Vault locked after each credential access
✅ **Audit Trail**: All requests logged (without credential values)
✅ **User Control**: Every access requires explicit approval
✅ **Secure Input**: Password input masked (no echo)

## Audit Log

Credential access events logged to `credential_audit.log`:

```
2025-10-28T18:30:00Z | INFO | REQUEST | agent=flight-booking-001 | domain=aa.com | reason=Logging in to search and book flights
2025-10-28T18:30:15Z | INFO | SUCCESS | agent=flight-booking-001 | domain=aa.com
```

## Troubleshooting

**"Bitwarden CLI not found"**
- Install Bitwarden CLI: https://bitwarden.com/help/cli/
- Ensure `bw` is in your PATH

**"Not logged into Bitwarden CLI"**
- Run `bw login` and enter your account credentials

**"Invalid master password"**
- Double-check your vault password
- System allows retry

**"No credential found for aa.com"**
- Add test credential to Bitwarden vault
- Ensure URI field contains "aa.com"

**"Login failed"**
- Check if test credential is correct
- Website may have changed (update selectors)

## Development

**Run tests**:
```bash
# Unit tests
pytest tests/ -v

# Integration tests (requires manual interaction)
pytest tests/integration/ -v -s -m integration

# Security tests
pytest tests/security/ -v
```

**Project Structure**:
```
src/
├── main.py                    # Entry point
├── agents/
│   ├── bitwarden_agent.py     # Credential management
│   └── flight_booking_agent.py # Browser automation
├── models/
│   ├── credential_request.py   # Request data structure
│   └── credential_response.py  # Response data structure
└── utils/
    ├── bitwarden_cli.py       # CLI wrapper
    ├── credential_handler.py   # Secure credential class
    ├── audit_logger.py        # Audit logging
    └── logging_config.py      # Logging setup
```

## Known Limitations (POC Scope)

- Single credential request per run
- No retry on login failure
- aa.com specific (not generalized)
- No 2FA handling
- No session-based vault unlocking
- No multi-user support

## Future Enhancements

- Session-based vault unlocking (unlock once, multiple requests)
- Support for multiple domains
- Retry logic for transient failures
- 2FA handling
- Generic website login (not aa.com specific)
- Browser extension for approval UI

## License

[Your license here]
```

---

## Security Implementation

### Critical Security Requirements

#### SEC-1: No Credential Persistence

**Rule**: Credentials must NEVER be written to disk

**Implementation Checklist**:
- [ ] No `open()` calls with credential variables
- [ ] No database writes with credentials
- [ ] No cache files with credentials
- [ ] No configuration files with credentials
- [ ] No temporary files with credentials

**Code Review Points**:
```python
# ❌ NEVER DO THIS
with open("cred.txt", "w") as f:
    f.write(f"{username}:{password}")

# ❌ NEVER DO THIS
config = {"password": password}
json.dump(config, open("config.json", "w"))

# ✅ CORRECT: Keep in memory only
credential = SecureCredential(username, password)
with credential as cred:
    use_credential(cred)
# Automatically cleared
```

#### SEC-2: No Credential Logging

**Rule**: Credentials must NEVER appear in logs

**Implementation Checklist**:
- [ ] No `logger.*()` calls with credential variables
- [ ] No `print()` statements with credentials
- [ ] No f-strings with credential variables in log messages
- [ ] Sanitize exception messages before logging
- [ ] Use `SensitiveDataFilter` in logging configuration

**Code Review Points**:
```python
# ❌ NEVER DO THIS
logger.info(f"Retrieved password: {password}")
print(f"Username: {username}")

# ❌ NEVER DO THIS (credential in exception)
raise ValueError(f"Login failed for {username}:{password}")

# ✅ CORRECT: Log metadata only
logger.info(f"Retrieved credential for domain: {domain}")
logger.error(f"Login failed for user: {username[:3]}***")  # Partial ok
```

#### SEC-3: Memory Cleanup

**Rule**: Clear credentials from memory after use

**Implementation Checklist**:
- [ ] Use context managers for credential lifecycle
- [ ] Overwrite strings before deletion
- [ ] Clear credentials in `finally` blocks
- [ ] Implement `__del__` method on SecureCredential
- [ ] Delete credential references explicitly

**Code Review Points**:
```python
# ✅ CORRECT: Use context manager
with credential as cred:
    browser.login(cred.username, cred.password)
# Credential automatically cleared

# ✅ CORRECT: Manual cleanup
try:
    cred = get_credential()
    use_credential(cred)
finally:
    if cred:
        cred.clear()

# ✅ CORRECT: Overwrite before delete
password = "secret123"
# ... use password ...
password = "X" * len(password)  # Overwrite
del password  # Delete reference
```

#### SEC-4: Vault Locking

**Rule**: Vault must be locked after every access

**Implementation Checklist**:
- [ ] Use `try/finally` for vault operations
- [ ] Lock vault in `finally` block
- [ ] Lock vault even on exceptions
- [ ] Implement `ensure_locked()` method
- [ ] Call `ensure_locked()` in cleanup

**Code Review Points**:
```python
# ✅ CORRECT: Always lock vault
session_key = None
try:
    session_key = cli.unlock(password)
    credential = cli.get_credential(domain, session_key)
    return credential
finally:
    if session_key:
        cli.lock()  # Always executes

# ✅ CORRECT: Cleanup handler
def cleanup():
    bitwarden_agent.ensure_locked()

atexit.register(cleanup)
```

#### SEC-5: Secure Password Input

**Rule**: Password input must not echo to terminal

**Implementation**:
```python
import getpass

# ✅ CORRECT: Use getpass
password = getpass.getpass("Enter vault password: ")

# ❌ NEVER DO THIS
password = input("Enter vault password: ")  # Echoes to terminal!
```

#### SEC-6: Audit Logging

**Rule**: Log access events without credential values

**Implementation**:
```python
# ✅ CORRECT: Log metadata
audit_logger.log_request(agent_id="flight-001", domain="aa.com", reason="login")
audit_logger.log_success(agent_id="flight-001", domain="aa.com")

# ❌ NEVER DO THIS
audit_logger.log("User logged in with password: {password}")
```

---

## Error Handling Strategy

### Error Categories

#### 1. Expected User Errors (User-Friendly Messages)

**Scenarios**:
- User denies credential request
- User provides wrong vault password
- User cancels with Ctrl+C
- Credential not found in vault

**Handling**:
- Return `CredentialResponse` with appropriate status
- Display clear, actionable message to user
- Suggest corrective action
- Do not log as ERROR level (use INFO or WARNING)

**Example**:
```python
if response.status == CredentialStatus.DENIED:
    console.print("[yellow]You denied the credential request.[/yellow]")
    console.print("The agent cannot proceed without credentials.")
    return False

if response.status == CredentialStatus.NOT_FOUND:
    console.print(f"[red]No credential found for {domain}[/red]")
    console.print(f"Please add a credential for {domain} to your Bitwarden vault:")
    console.print("  1. Open Bitwarden")
    console.print(f"  2. Create new login item with URI: {domain}")
    console.print("  3. Save and try again")
    return False
```

#### 2. Expected System Errors (Recoverable)

**Scenarios**:
- Bitwarden CLI not installed
- User not logged into Bitwarden
- Network timeout during login
- Browser launch failure

**Handling**:
- Raise custom exception with helpful message
- Catch in main orchestrator
- Display troubleshooting steps
- Return non-zero exit code

**Example**:
```python
try:
    cli = BitwardenCLI()
except BitwardenCLIError as e:
    console.print(f"[red]Error: {e}[/red]")
    console.print("\nTroubleshooting:")
    console.print("  1. Install Bitwarden CLI from https://bitwarden.com/help/cli/")
    console.print("  2. Run 'bw login' to authenticate")
    console.print("  3. Try again")
    return 1
```

#### 3. Unexpected Errors (Fatal)

**Scenarios**:
- JSON parsing failure from CLI
- Playwright crash
- Python runtime error
- Unexpected exception type

**Handling**:
- Log full exception with stack trace
- Display generic error message to user
- Ensure cleanup (vault lock) still happens
- Return non-zero exit code

**Example**:
```python
try:
    success = await flight_agent.run()
except Exception as e:
    logger.error(f"Fatal error: {e}", exc_info=True)
    console.print(f"[red]An unexpected error occurred.[/red]")
    console.print(f"Error: {str(e)}")
    console.print("\nPlease check the logs for details.")
    return 1
finally:
    # Cleanup always runs
    bitwarden_agent.ensure_locked()
```

### Error Mapping Table

| Error Type | Exception/Status | User Message | Action |
|------------|-----------------|--------------|--------|
| User denial | `CredentialStatus.DENIED` | "You denied the request" | Exit gracefully |
| Wrong password | `BitwardenCLIError` | "Invalid password. Try again?" | Retry or exit |
| Not found | `CredentialStatus.NOT_FOUND` | "No credential for X. Add to vault." | Exit with instructions |
| CLI not installed | `BitwardenCLIError` | "Install Bitwarden CLI" | Exit with URL |
| Not logged in | `BitwardenCLIError` | "Run 'bw login' first" | Exit with command |
| Network timeout | `TimeoutError` | "Network timeout. Check connection." | Exit |
| Browser crash | `PlaywrightError` | "Browser error. Try again." | Exit |
| Parse error | `JSONDecodeError` | "CLI output error. Report bug." | Exit with logs |
| Unknown | `Exception` | "Unexpected error occurred" | Exit with logs |

---

## Testing Approach

### Test Pyramid

```
                    ▲
                   ╱ ╲
                  ╱   ╲
                 ╱ E2E ╲           1-2 end-to-end tests
                ╱───────╲
               ╱         ╲
              ╱Integration╲        5-10 integration tests
             ╱─────────────╲
            ╱               ╲
           ╱  Unit Tests     ╲     20-30 unit tests
          ╱───────────────────╲
         ╱                     ╲
        ╱                       ╲
       ───────────────────────────
```

### Unit Tests

**Scope**: Individual functions and classes in isolation

**Tools**: pytest, unittest.mock

**Coverage Target**: >80% for utils and models

**Examples**:
- `test_bitwarden_cli.py`: Test CLI wrapper with mocked subprocess
- `test_credential_handler.py`: Test SecureCredential lifecycle
- `test_models.py`: Test dataclass creation and validation
- `test_audit_logger.py`: Test log entry formatting

**Run**:
```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Integration Tests

**Scope**: Multiple components working together

**Tools**: pytest, real Bitwarden CLI (with test vault)

**Setup Required**:
- Test Bitwarden vault with known credentials
- Bitwarden CLI logged in
- No network mocking (test real CLI interaction)

**Examples**:
- `test_bitwarden_agent_integration.py`: Test agent with real CLI
- `test_browser_navigation.py`: Test Playwright with real browser
- `test_error_scenarios.py`: Test error handling end-to-end

**Run**:
```bash
pytest tests/integration/ -v -s -m integration
```

### End-to-End Tests

**Scope**: Complete POC flow from start to finish

**Tools**: pytest, manual validation

**Setup Required**:
- User interaction (approve request, enter password)
- Real Bitwarden vault with aa.com credential
- Network access to aa.com

**Examples**:
- `test_e2e.py`: Complete happy path flow

**Run**:
```bash
pytest tests/integration/test_e2e.py -v -s -m integration
```

### Security Tests

**Scope**: Validate security requirements

**Tools**: pytest, grep, file inspection

**Examples**:
- `test_credential_leakage.py`: Check logs for credential values
- `test_vault_locking.py`: Verify vault locked after run
- `test_no_persistence.py`: Check for credential files on disk

**Run**:
```bash
pytest tests/security/ -v
```

### Manual Test Checklist

**Before Each Release**:
- [ ] Run POC end-to-end with visible browser
- [ ] Test user denial flow
- [ ] Test wrong password (verify retry)
- [ ] Test missing credential (verify error message)
- [ ] Test Ctrl+C cancellation
- [ ] Verify vault locked after each run: `bw status`
- [ ] Review audit log for completeness
- [ ] Grep logs for test password: `grep -r "TestPassword" .`
- [ ] Check for credential files: `find . -name "*cred*" -o -name "*pass*"`

---

## Acceptance Criteria

### Functional Acceptance Criteria

**AC-1: Agent Can Request Credentials**
- [ ] Flight booking agent navigates to aa.com login page
- [ ] Agent generates credential request with domain, reason, agent ID
- [ ] Request routed to Bitwarden agent
- [ ] Agent receives CredentialResponse object

**AC-2: User Can Approve/Deny Requests**
- [ ] User sees formatted approval prompt with agent name, domain, reason
- [ ] User can approve with Y/y/yes
- [ ] User can deny with N/n/no
- [ ] User can cancel with Ctrl+C
- [ ] Approval prompts for vault password (masked input)
- [ ] Denial aborts without vault access

**AC-3: System Retrieves Credentials from Vault**
- [ ] Vault unlocks using user-provided password
- [ ] System searches vault for credentials matching domain
- [ ] System returns username and password for first match
- [ ] Vault locks immediately after retrieval
- [ ] Wrong password prompts retry (max 3 attempts)
- [ ] Missing credential returns NOT_FOUND status

**AC-4: Agent Logs Into Website**
- [ ] Browser navigates to aa.com login page
- [ ] Stealth mode applied to avoid bot detection
- [ ] System detects username and password input fields
- [ ] System fills fields with credential values
- [ ] System submits login form
- [ ] System waits for navigation indicating success
- [ ] System detects login failure (error messages or still on login page)
- [ ] Credentials cleared from memory after login attempt

**AC-5: System Prevents Credential Leakage**
- [ ] No credentials in any log files
- [ ] No credentials in console output
- [ ] No credentials in error tracebacks
- [ ] No credentials in files on disk
- [ ] Credential objects cleared after use
- [ ] Vault password not stored after vault unlocked
- [ ] Audit log contains domains/agents but not credential values

**AC-6: System Maintains Audit Trail**
- [ ] Log entry created for each credential request
- [ ] Log includes: timestamp, agent_id, domain, reason
- [ ] Log includes user decision (approved/denied)
- [ ] Log includes outcome (success/failure)
- [ ] Log does NOT include credential values or vault password
- [ ] Log entries timestamped with ISO 8601 format
- [ ] Log persists across POC runs (append mode)

### Non-Functional Acceptance Criteria

**AC-7: Performance**
- [ ] Credential retrieval within 30 seconds of user approval
- [ ] Login completion within 60 seconds of credential delivery
- [ ] No blocking operations visible to user

**AC-8: Security**
- [ ] Zero credential persistence (verified by file system check)
- [ ] Zero credential logging (verified by log grep)
- [ ] Vault locked after every run (verified by `bw status`)
- [ ] Secure password input (no echo to terminal)

**AC-9: Usability**
- [ ] Clear, actionable prompts for user decisions
- [ ] Helpful error messages guiding user action
- [ ] Progress indicators during operations
- [ ] README allows new user to setup and run POC

**AC-10: Maintainability**
- [ ] Code has clear module structure
- [ ] Functions have docstrings
- [ ] Security measures documented in comments
- [ ] Unit test coverage >70%
- [ ] Integration tests cover happy path and errors

---

## Additional Technical Documents

See also:
- `architecture_diagram.md` - Visual system architecture
- `data_flow.md` - Detailed data flow diagrams
- `security_review.md` - Security architecture and threat model
- `api_reference.md` - API documentation for each component

---

## Implementation Notes

### Technology Decisions

**Python 3.8+**: Required for async/await and modern type hints

**Playwright**: Chosen for browser automation (async-first, reliable selectors)

**Rich**: For formatted CLI output (optional, can use basic print if needed)

**Bitwarden CLI**: Subprocess interface (no Python SDK available)

### Design Patterns Used

**Context Manager**: For SecureCredential automatic cleanup
- Guarantees cleanup even on exceptions
- Makes credential lifetime explicit

**Layered Architecture**: Clear separation of concerns
- Presentation (CLI) → Agent → Integration → External
- Each layer testable in isolation

**Dependency Injection**: For testing
- Agents accept dependencies in constructor
- Enables mocking for unit tests

**Result Object Pattern**: For expected outcomes
- CredentialResponse encapsulates status + data
- Clearer than exceptions for expected failures

### File Structure Summary

```
AgentCredentialRequest/
├── src/
│   ├── __init__.py
│   ├── main.py                           # Entry point, orchestrator
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── bitwarden_agent.py            # Credential request handler
│   │   └── flight_booking_agent.py       # Browser automation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── credential_request.py         # Request dataclass
│   │   └── credential_response.py        # Response dataclass + enum
│   └── utils/
│       ├── __init__.py
│       ├── bitwarden_cli.py              # CLI subprocess wrapper
│       ├── credential_handler.py         # SecureCredential class
│       ├── audit_logger.py               # Audit logging
│       └── logging_config.py             # App logging setup
├── tests/
│   ├── __init__.py
│   ├── test_bitwarden_cli.py            # Unit tests
│   ├── test_credential_handler.py       # Unit tests
│   ├── test_models.py                   # Unit tests
│   ├── test_audit_logger.py             # Unit tests
│   ├── integration/
│   │   ├── test_bitwarden_agent.py      # Integration tests
│   │   ├── test_error_scenarios.py      # Error handling
│   │   └── test_e2e.py                  # End-to-end
│   └── security/
│       └── test_credential_leakage.py   # Security validation
├── requirements.txt                      # Python dependencies
├── README.md                            # User documentation
├── .gitignore                           # Git ignore rules
└── credential_audit.log                 # Generated at runtime
```

---

## Next Steps for Implementer

The implementer agent should follow this sequence:

1. **Phase 1 (Days 1-2)**: Create project structure, install dependencies, validate Bitwarden CLI
2. **Phase 2 (Days 3-5)**: Implement core components (CLI wrapper, agents, models)
3. **Phase 3 (Days 6-7)**: Integrate components, implement main orchestrator, test end-to-end
4. **Phase 4 (Days 8-9)**: Security validation, error testing, documentation

Refer to component specifications for detailed implementation guidance.

---

## Success Metrics

**Technical Metrics**:
- ✅ All unit tests passing (>70% coverage)
- ✅ All integration tests passing
- ✅ Security tests passing (zero leaks)
- ✅ Vault locked after every run

**Functional Metrics**:
- ✅ POC completes end-to-end successfully
- ✅ User can approve/deny requests
- ✅ Login succeeds with correct credentials
- ✅ Errors handled gracefully with clear messages

**Security Metrics**:
- ✅ Zero credentials in logs (verified by grep)
- ✅ Zero credentials on disk (verified by file check)
- ✅ Vault always locked (verified by `bw status`)
- ✅ Complete audit trail (all events logged)

---

**Document prepared by**: Architect Agent
**Date**: 2025-10-28
**Status**: READY_FOR_IMPLEMENTATION
**Next Phase**: Implementation (Implementer Agent)
