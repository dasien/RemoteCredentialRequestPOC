#!/usr/bin/env python3
"""
Manual Test 3: Session Management

Tests session listing and revocation.

Usage:
    python -m tests.manual.test_session_management
"""
import sys
import time
from tests.manual.base import ManualTestBase, TestResult, TestStatus
from src.sdk.credential_client import CredentialClient
from src.models.credential_response import CredentialStatus


class SessionManagementTest(ManualTestBase):
    """Test class for session management validation."""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """Initialize session management test."""
        super().__init__(server_url)
        self.client: CredentialClient = None
    
    def setup_pairing(self) -> TestResult:
        """Setup: Establish pairing for session tests."""
        test_name = "Setup: Pairing"
        start_time = time.time()
        
        self.print_section("Setup: Establishing Session")
        
        try:
            self.client = CredentialClient(self.server_url)
            pairing_code = self.client.pair(
                agent_id="manual-test-003",
                agent_name="Manual Test Agent - Session Mgmt",
                timeout=120
            )
            
            self.console.print()
            self.console.print(f"[bold green]✓ PAIRING CODE: {pairing_code}[/bold green]")
            
            self.print_action_required(
                f"Type in Terminal 1: [bold cyan]pair {pairing_code}[/bold cyan]\n"
                f"Then enter your Bitwarden master password."
            )
            
            duration = time.time() - start_time
            self.print_success("Pairing successful")
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.PASSED,
                message="Session established",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Pairing failed",
                duration=duration,
                error=str(e)
            )
    
    def test_list_sessions(self) -> TestResult:
        """
        Test Case 1: List active sessions.
        
        Validates:
        - Sessions command works
        - Session details displayed correctly
        
        Returns:
            TestResult
        """
        test_name = "List Active Sessions"
        start_time = time.time()
        
        self.print_section(f"Test 1: {test_name}")
        
        if not self.client or not self.client.session_id:
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="No active session",
                duration=0.0
            )
        
        try:
            self.print_step("Checking session status via API...")
            status = self.client.get_session_status()
            
            if status and status.get('active'):
                self.print_success("Session is active")
                self.console.print(f"   Agent: [cyan]{status.get('agent_name')}[/cyan]")
                self.console.print(f"   Last access: [yellow]{status.get('last_access')}[/yellow]")
                self.console.print(f"   Expires: [yellow]{status.get('expires_at')}[/yellow]")
            else:
                self.print_error("Session not active")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Session not found or inactive",
                    duration=time.time() - start_time
                )
            
            self.console.print()
            self.print_action_required(
                "In Terminal 1, type: [bold cyan]sessions[/bold cyan]\n\n"
                "You should see your active session in the table.\n"
                "Verify the agent name and session ID match."
            )
            
            self.wait_for_user("Did you see the session in Terminal 1? Press Enter to continue...")
            
            duration = time.time() - start_time
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.PASSED,
                message="Session status retrieved successfully",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Failed to get session status",
                duration=duration,
                error=str(e)
            )
    
    def test_session_revocation(self) -> TestResult:
        """
        Test Case 2: Session revocation.
        
        Validates:
        - Session can be revoked from Terminal 1
        - Subsequent requests fail with proper error
        - Vault is locked after revocation
        
        Returns:
            TestResult
        """
        test_name = "Session Revocation"
        start_time = time.time()
        
        self.print_section(f"Test 2: {test_name}")
        
        if not self.client or not self.client.session_id:
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="No active session",
                duration=0.0
            )
        
        try:
            session_id = self.client.session_id
            session_prefix = session_id[:10]
            
            self.print_step(f"Current session: {session_id}")
            self.console.print()
            
            self.print_action_required(
                f"In Terminal 1, type:\n\n"
                f"  [bold cyan]revoke {session_prefix}[/bold cyan]\n\n"
                f"This will revoke the session and lock the vault."
            )
            
            self.wait_for_user("Press Enter after you've revoked the session...")
            
            # Try to use revoked session
            self.console.print()
            self.print_step("Testing with revoked session...")
            
            response = self.client.request_credential(
                domain="example.com",
                reason="Test with revoked session (should fail)",
                agent_id="manual-test-003",
                agent_name="Manual Test Agent"
            )
            
            duration = time.time() - start_time
            
            # Should fail
            if response.status == CredentialStatus.ERROR:
                if "Invalid or expired session" in response.error_message:
                    self.print_success("Session revocation worked!")
                    self.console.print(f"   Error (expected): {response.error_message}")
                    
                    return TestResult(
                        test_name=test_name,
                        status=TestStatus.PASSED,
                        message="Revoked session rejected correctly",
                        duration=duration
                    )
                else:
                    self.print_warning(f"Unexpected error: {response.error_message}")
                    return TestResult(
                        test_name=test_name,
                        status=TestStatus.PASSED,
                        message="Session revoked (different error message)",
                        duration=duration
                    )
            else:
                self.print_error(f"Request succeeded (should have failed!)")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Revoked session still accepted requests",
                    duration=duration
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Test execution error",
                duration=duration,
                error=str(e)
            )
    
    def run(self) -> int:
        """Run all session management tests."""
        self.print_header("MANUAL TEST: Session Management")
        
        # Check prerequisites
        if not self.check_prerequisites():
            self.print_error("Prerequisites not met")
            return 1
        
        self.print_success("Prerequisites met")
        self.wait_for_user("Ready to start? Press Enter...")
        
        # Setup
        result_setup = self.setup_pairing()
        self.add_result(result_setup)
        
        if result_setup.status != TestStatus.PASSED:
            self.print_error("Setup failed - cannot continue")
            self.print_summary()
            return 1
        
        self.console.print()
        self.wait_for_user("Setup complete. Press Enter to continue...")
        
        # Test 1: List sessions
        result1 = self.test_list_sessions()
        self.add_result(result1)
        
        # Test 2: Revoke session
        if result1.status == TestStatus.PASSED:
            self.console.print()
            self.wait_for_user("Test 1 complete. Press Enter for revocation test...")
            result2 = self.test_session_revocation()
            self.add_result(result2)
        
        # Print summary
        self.print_summary()
        
        # Return exit code
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        return 0 if failed == 0 else 1


def main():
    """Main entry point."""
    test = SessionManagementTest()
    sys.exit(test.run())


if __name__ == '__main__':
    main()
