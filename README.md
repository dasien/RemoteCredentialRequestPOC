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
   cd /Users/bgentry/Source/repos/AgentCredentialRequest
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

## Documentation

- **Implementation Plan**: `enhancements/credential-request/architect/implementation_plan.md`
- **Test Plan**: `enhancements/credential-request/implementer/test_plan.md`
- **Implementation Summary**: `enhancements/credential-request/implementer/implementation_summary.md`

## Status

**Status**: READY_FOR_TESTING
**Implementation**: Complete
**Next Phase**: Testing and validation

## License

[Your license here]
