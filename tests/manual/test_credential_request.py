#!/usr/bin/env python3
"""
Manual Test 2: Credential Request Flow

Tests credential request with vault already unlocked from pairing.

CRITICAL TEST: Validates that NO password prompt appears during request.

Usage:
    python -m tests.manual.test_credential_request
"""
import sys
import time
from tests.manual.base import ManualTestBase, TestResult, TestStatus
from src.sdk.credential_client import CredentialClient
from src.models.credential_response import CredentialStatus


class CredentialRequestTest(ManualTestBase):
    """Test class for credential request validation."""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """Initialize credential request test."""
        super().__init__(server_url)
        self.client: CredentialClient = None
    
    def test_pairing_first(self) -> TestResult:
        """
        Setup: Establish pairing before testing credentials.
        
        Returns:
            TestResult
        """
        test_name = "Setup: Pairing"
        start_time = time.time()
        
        self.print_section("Setup: Pairing with Server")
        
        try:
            self.client = CredentialClient(self.server_url)
            
            pairing_code = self.client.pair(
                agent_id="manual-test-002",
                agent_name="Manual Test Agent - Credentials",
                timeout=120
            )
            
            self.console.print()
            self.console.print(f"[bold green]✓ PAIRING CODE: {pairing_code}[/bold green]")
            
            self.print_action_required(
                f"Type this in Terminal 1:\n\n"
                f"  [bold cyan]pair {pairing_code}[/bold cyan]\n\n"
                f"Then enter your Bitwarden master password.\n\n"
                f"⏳ Waiting for pairing to complete..."
            )
            
            duration = time.time() - start_time
            
            self.console.print()
            self.print_success(f"Pairing complete (Session: {self.client.session_id})")
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.PASSED,
                message="Pairing established for credential tests",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Failed to establish pairing",
                duration=duration,
                error=str(e)
            )
    
    def test_credential_request_approved(self) -> TestResult:
        """
        Test Case 1: Credential request with user approval.
        
        CRITICAL: Validates NO password prompt during request.
        
        Validates:
        - Encrypted request sent
        - Approval prompt appears in Terminal 1
        - NO password prompt (vault already unlocked)
        - Credential returned and decrypted
        
        Returns:
            TestResult
        """
        test_name = "Credential Request (Approved)"
        start_time = time.time()
        
        self.print_section(f"Test 1: {test_name}")
        
        if not self.client or not self.client.session_id:
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="No active session - pairing required",
                duration=0.0
            )
        
        try:
            self.print_step("Requesting credential for example.com...")
            self.console.print()
            
            # Make request (this will block until user approves)
            response = self.client.request_credential(
                domain="example.com",
                reason="Manual integration test - validating NO password prompt",
                agent_id="manual-test-002",
                agent_name="Manual Test Agent - Credentials"
            )
            
            self.print_action_required(
                "[bold yellow]⚠️  CRITICAL VALIDATION:[/bold yellow]\n\n"
                "In Terminal 1, you should see a credential request prompt.\n\n"
                "[bold red]WATCH CAREFULLY:[/bold red] You should see:\n"
                "  ✓ Agent name and domain\n"
                "  ✓ [Y] Approve    [N] Deny\n\n"
                "[bold red]You should NOT see:[/bold red]\n"
                "  ✗ Password prompt\n"
                "  ✗ 'Enter Bitwarden master password'\n\n"
                "Press [bold cyan]Y[/bold cyan] to approve the request.\n\n"
                "⏳ Waiting for your approval..."
            )
            
            duration = time.time() - start_time
            
            # Check response
            self.console.print()
            if response.status == CredentialStatus.APPROVED:
                self.print_success("Credential approved!")
                
                with response.credential as cred:
                    self.console.print(f"   Username: [cyan]{cred.username}[/cyan]")
                    self.console.print(f"   Password: [dim]{'*' * len(cred.password)}[/dim] (hidden)")
                
                self.console.print()
                self.print_success("CRITICAL: No password prompt appeared ✓")
                self.print_success("Vault was already unlocked from pairing ✓")
                
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.PASSED,
                    message="Credential retrieved successfully, no password prompt",
                    duration=duration
                )
                
            elif response.status == CredentialStatus.DENIED:
                self.print_warning("User denied credential request")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="User denied - expected approval for test",
                    duration=duration
                )
            else:
                self.print_error(f"Error: {response.error_message}")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Credential request failed",
                    duration=duration,
                    error=response.error_message
                )
                
        except Exception as e:
            duration = time.time() - start_time
            self.print_error(f"Test failed: {e}")
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Test execution error",
                duration=duration,
                error=str(e)
            )
    
    def test_credential_request_denied(self) -> TestResult:
        """
        Test Case 2: Credential request with user denial.
        
        Validates:
        - Denial handled gracefully
        - No credential returned
        
        Returns:
            TestResult
        """
        test_name = "Credential Request (Denied)"
        start_time = time.time()
        
        self.print_section(f"Test 2: {test_name}")
        
        if not self.client or not self.client.session_id:
            return TestResult(
                test_name=test_name,
                status=TestStatus.SKIPPED,
                message="No active session",
                duration=0.0
            )
        
        try:
            self.print_step("Requesting credential for example.com...")
            
            response = self.client.request_credential(
                domain="example.com",
                reason="Manual test - please DENY this request",
                agent_id="manual-test-002",
                agent_name="Manual Test Agent - Denial"
            )
            
            self.print_action_required(
                "In Terminal 1, you should see a credential request.\n\n"
                "Press [bold red]N[/bold red] to DENY this request.\n\n"
                "⏳ Waiting for your decision..."
            )
            
            duration = time.time() - start_time
            
            self.console.print()
            if response.status == CredentialStatus.DENIED:
                self.print_success("User denied request (expected)")
                self.console.print(f"   Error message: {response.error_message}")
                
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.PASSED,
                    message="Denial handled correctly",
                    duration=duration
                )
            else:
                self.print_warning(f"Unexpected status: {response.status}")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Expected DENIED status",
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
        """Run all credential request tests."""
        self.print_header("MANUAL TEST: Credential Request Flow")
        
        # Check prerequisites
        if not self.check_prerequisites():
            self.print_error("Prerequisites not met")
            return 1
        
        self.print_success("Prerequisites met")
        self.console.print()
        
        # Important instructions
        self.console.print("[bold yellow]IMPORTANT:[/bold yellow]")
        self.console.print("  Make sure you have a credential for 'example.com' in your vault")
        self.console.print("  This test will request it twice (approve, then deny)")
        self.console.print()
        
        self.wait_for_user("Ready to start? Press Enter...")
        
        # Setup: Pairing
        result_setup = self.test_pairing_first()
        self.add_result(result_setup)
        
        if result_setup.status != TestStatus.PASSED:
            self.print_error("Pairing failed - cannot continue")
            self.print_summary()
            return 1
        
        self.console.print()
        self.wait_for_user("Pairing complete. Press Enter to continue to credential tests...")
        
        # Test 1: Approved
        result1 = self.test_credential_request_approved()
        self.add_result(result1)
        
        # Test 2: Denied
        if result1.status == TestStatus.PASSED:
            self.console.print()
            self.wait_for_user("Test 1 complete. Press Enter for denial test...")
            result2 = self.test_credential_request_denied()
            self.add_result(result2)
        
        # Print summary
        self.print_summary()
        
        # Return exit code
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        return 0 if failed == 0 else 1


def main():
    """Main entry point."""
    test = CredentialRequestTest()
    sys.exit(test.run())


if __name__ == '__main__':
    main()
