"""
Manual integration tests for remote credential access.

These tests require two terminals and human interaction to validate
the complete pairing and credential request flows.

Usage:
    # Run all tests
    python -m tests.manual

    # Run specific test
    python -m tests.manual.test_pairing
    python -m tests.manual.test_credential_request
    python -m tests.manual.test_session_management
    python -m tests.manual.test_error_cases

Requirements:
    - Terminal 1: Approval client must be running (python -m src.approval_client)
    - Terminal 2: Run test scripts
    - Bitwarden CLI: Logged in (bw login)
    - Test credential: "example.com" must exist in vault
"""
from .base import ManualTestBase, TestResult

__all__ = ['ManualTestBase', 'TestResult']
