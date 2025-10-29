#!/usr/bin/env python3
"""
Manual Test 4: Error Cases

Tests various error scenarios and recovery mechanisms.

Usage:
    python -m tests.manual.test_error_cases
"""
import sys
import time
from tests.manual.base import ManualTestBase, TestResult, TestStatus
from src.sdk.credential_client import CredentialClient
from src.models.credential_response import CredentialStatus


class ErrorCasesTest(ManualTestBase):
    """Test class for error case validation."""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """Initialize error cases test."""
        super().__init__(server_url)
    
    def test_wrong_password(self) -> TestResult:
        """
        Test Case 1: Wrong master password during pairing.
        
        Validates:
        - Wrong password detected
        - Clear error message
        - Pairing fails gracefully
        
        Returns:
            TestResult
        """
        test_name = "Wrong Master Password"
        start_time = time.time()
        
        self.print_section(f"Test 1: {test_name}")
        
        try:
            client = CredentialClient(self.server_url)
            
            pairing_code = client.pair(
                agent_id="manual-test-error-001",
                agent_name="Error Test - Wrong Password",
                timeout=120
            )
            
            self.console.print()
            self.console.print(f"[bold green]✓ PAIRING CODE: {pairing_code}[/bold green]")
            
            self.print_action_required(
                f"Type in Terminal 1: [bold cyan]pair {pairing_code}[/bold cyan]\n\n"
                f"[bold red]⚠️  When prompted for password:[/bold red]\n"
                f"Enter an INCORRECT password (intentionally wrong)\n\n"
                f"Expected result: Pairing should fail with clear error message"
            )
            
            self.wait_for_user("Did pairing fail with 'Incorrect password' message? (y/n): ")
            
            # Since we expect failure, client won't get session_id
            # We're testing the error message in Terminal 1, not here
            
            duration = time.time() - start_time
            
            self.console.print()
            response = Prompt.ask(
                "[bold]Did Terminal 1 show a clear error about incorrect password?[/bold]",
                choices=["y", "n"],
                default="n"
            )
            
            if response == "y":
                self.print_success("Wrong password detected correctly")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.PASSED,
                    message="Incorrect password detected with clear error",
                    duration=duration
                )
            else:
                self.print_error("Error message not clear or pairing succeeded")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Expected clear error about wrong password",
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
    
    def test_expired_pairing_code(self) -> TestResult:
        """
        Test Case 2: Expired pairing code.
        
        Validates:
        - Expired codes rejected
        - Clear timeout message
        
        Returns:
            TestResult
        """
        test_name = "Expired Pairing Code"
        start_time = time.time()
        
        self.print_section(f"Test 2: {test_name}")
        
        try:
            client = CredentialClient(self.server_url)
            
            pairing_code = client.pair(
                agent_id="manual-test-error-002",
                agent_name="Error Test - Expired Code",
                timeout=10  # Very short timeout
            )
            
            self.console.print()
            self.console.print(f"[bold green]✓ PAIRING CODE: {pairing_code}[/bold green]")
            self.console.print()
            
            self.print_warning("DO NOT enter this code in Terminal 1")
            self.print_step("Waiting 10 seconds for timeout...")
            
            # Wait for timeout (the pair() call above will timeout)
            # This should raise TimeoutError
            
            duration = time.time() - start_time
            
            # If we get here, timeout didn't work
            self.print_error("Pairing succeeded (should have timed out!)")
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Timeout mechanism failed",
                duration=duration
            )
            
        except TimeoutError as e:
            duration = time.time() - start_time
            self.print_success("Pairing timed out as expected")
            self.console.print(f"   Error: {e}")
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.PASSED,
                message="Timeout after 10 seconds (expected)",
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Unexpected error",
                duration=duration,
                error=str(e)
            )
    
    def test_request_with_no_pairing(self) -> TestResult:
        """
        Test Case 3: Credential request without pairing.
        
        Validates:
        - Requests fail without session
        - Clear error message
        
        Returns:
            TestResult
        """
        test_name = "Request Without Pairing"
        start_time = time.time()
        
        self.print_section(f"Test 3: {test_name}")
        
        try:
            # Create client without pairing
            client = CredentialClient(self.server_url)
            
            self.print_step("Attempting request without pairing...")
            
            # Should raise RuntimeError
            response = client.request_credential(
                domain="example.com",
                reason="Test without pairing",
                agent_id="test",
                agent_name="Test"
            )
            
            # Should not reach here
            duration = time.time() - start_time
            self.print_error("Request succeeded (should have failed!)")
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Request without pairing should fail",
                duration=duration
            )
            
        except RuntimeError as e:
            duration = time.time() - start_time
            
            if "Must call pair() first" in str(e):
                self.print_success("Request blocked correctly")
                self.console.print(f"   Error: {e}")
                
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.PASSED,
                    message="Clear error about required pairing",
                    duration=duration
                )
            else:
                self.print_warning(f"Unexpected error message: {e}")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.PASSED,
                    message="Request blocked (different error)",
                    duration=duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                message="Unexpected error type",
                duration=duration,
                error=str(e)
            )
    
    def test_credential_not_found(self) -> TestResult:
        """
        Test Case 4: Request credential that doesn't exist in vault.
        
        Validates:
        - Not found handled gracefully
        - Clear error message
        
        Returns:
            TestResult
        """
        test_name = "Credential Not Found"
        start_time = time.time()
        
        self.print_section(f"Test 4: {test_name}")
        
        if not self.client or not self.client.session_id:
            # Need to pair first
            self.print_step("Need to establish pairing first...")
            setup = self.setup_pairing()
            if setup.status != TestStatus.PASSED:
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Could not establish pairing",
                    duration=time.time() - start_time
                )
        
        try:
            self.print_step("Requesting credential for nonexistent.com...")
            
            response = self.client.request_credential(
                domain="nonexistent.com",
                reason="Test credential not found",
                agent_id="manual-test-error-003",
                agent_name="Error Test - Not Found"
            )
            
            self.print_action_required(
                "When the approval prompt appears in Terminal 1,\n"
                "Press [bold cyan]Y[/bold cyan] to approve.\n\n"
                "Expected: Error because 'nonexistent.com' not in vault"
            )
            
            duration = time.time() - start_time
            
            self.console.print()
            if response.status == CredentialStatus.ERROR:
                if "not found" in response.error_message.lower():
                    self.print_success("'Not found' error handled correctly")
                    self.console.print(f"   Error: {response.error_message}")
                    
                    return TestResult(
                        test_name=test_name,
                        status=TestStatus.PASSED,
                        message="Credential not found error handled",
                        duration=duration
                    )
                else:
                    self.print_warning(f"Different error: {response.error_message}")
                    return TestResult(
                        test_name=test_name,
                        status=TestStatus.PASSED,
                        message="Error returned (different message)",
                        duration=duration
                    )
            else:
                self.print_error(f"Unexpected status: {response.status}")
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.FAILED,
                    message="Expected ERROR status for nonexistent domain",
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
        """Run all error case tests."""
        self.print_header("MANUAL TEST: Error Cases")
        
        # Check prerequisites
        if not self.check_prerequisites():
            self.print_error("Prerequisites not met")
            return 1
        
        self.print_success("Prerequisites met")
        self.console.print()
        
        # Instructions
        self.console.print("[bold yellow]This test will validate error handling:[/bold yellow]")
        self.console.print("  1. Wrong master password")
        self.console.print("  2. Expired pairing code (10s timeout)")
        self.console.print("  3. Request without pairing")
        self.console.print("  4. Credential not found in vault")
        self.console.print()
        
        self.wait_for_user("Ready to start? Press Enter...")
        
        # Test 1: Wrong password
        result1 = self.test_wrong_password()
        self.add_result(result1)
        
        self.console.print()
        self.wait_for_user("Test 1 complete. Press Enter for timeout test...")
        
        # Test 2: Timeout
        result2 = self.test_expired_pairing_code()
        self.add_result(result2)
        
        self.console.print()
        self.wait_for_user("Test 2 complete. Press Enter for no-pairing test...")
        
        # Test 3: No pairing
        result3 = self.test_request_with_no_pairing()
        self.add_result(result3)
        
        self.console.print()
        self.wait_for_user("Test 3 complete. Press Enter for not-found test...")
        
        # Test 4: Not found (needs pairing first)
        result4 = self.test_credential_not_found()
        self.add_result(result4)
        
        # Print summary
        self.print_summary()
        
        # Return exit code
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        return 0 if failed == 0 else 1


def main():
    """Main entry point."""
    test = ErrorCasesTest()
    sys.exit(test.run())


if __name__ == '__main__':
    main()
