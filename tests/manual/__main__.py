#!/usr/bin/env python3
"""
Manual Integration Test Runner

Runs all manual integration tests or specific test suites.

Usage:
    # Run all tests
    python -m tests.manual

    # Run specific test
    python -m tests.manual --test pairing
    python -m tests.manual --test credential
    python -m tests.manual --test session
    python -m tests.manual --test errors

    # Quick smoke test (pairing + one credential request)
    python -m tests.manual --quick

Prerequisites:
    Terminal 1: python -m src.approval_client (must be running)
    Bitwarden: bw login (must be logged in)
    Vault: Must have credential for "example.com"
"""
import sys
import argparse
from rich.console import Console
from tests.manual.test_pairing import PairingFlowTest
from tests.manual.test_credential_request import CredentialRequestTest
from tests.manual.test_session_management import SessionManagementTest
from tests.manual.test_error_cases import ErrorCasesTest
from tests.manual.base import TestStatus

def print_banner():
    """Print welcome banner."""
    console = Console()
    console.print()
    console.print("=" * 70, style="bold cyan")
    console.print("  REMOTE CREDENTIAL ACCESS - MANUAL INTEGRATION TESTS", style="bold cyan")
    console.print("=" * 70, style="bold cyan")
    console.print()
    console.print("[bold]Test Suite Overview:[/bold]")
    console.print("  1. [cyan]Pairing Flow[/cyan] - PAKE exchange, vault unlock")
    console.print("  2. [cyan]Credential Request[/cyan] - Encrypted requests, NO password prompt")
    console.print("  3. [cyan]Session Management[/cyan] - List, revoke sessions")
    console.print("  4. [cyan]Error Cases[/cyan] - Wrong password, timeouts, not found")
    console.print()
    console.print("[bold yellow]⚠️  PREREQUISITES:[/bold yellow]")
    console.print("  • Terminal 1 must be running: [bold]python -m src.approval_client[/bold]")
    console.print("  • Bitwarden CLI must be logged in: [bold]bw login[/bold]")
    console.print("  • Vault must have credential for: [bold]example.com[/bold]")
    console.print()


def run_quick_test() -> int:
    """
    Run quick smoke test (5 minutes).
    
    Tests:
    - Pairing flow
    - One credential request (approved)
    
    Returns:
        Exit code
    """
    console = Console()
    console.print("[bold cyan]Running Quick Smoke Test[/bold cyan]")
    console.print()
    
    # Test 1: Pairing
    pairing_test = PairingFlowTest()
    if not pairing_test.check_prerequisites():
        console.print("[red]Prerequisites not met - cannot continue[/red]")
        return 1
    
    console.print("[green]✓ Prerequisites met[/green]")
    console.print()
    
    from rich.prompt import Prompt
    response = Prompt.ask("Ready to start quick test?", choices=["y", "n"], default="y")
    if response != "y":
        return 1
    
    # Run pairing
    result1 = pairing_test.test_successful_pairing()
    pairing_test.add_result(result1)
    
    if result1.status != TestStatus.PASSED:
        console.print("[red]✗ Pairing failed - cannot continue[/red]")
        pairing_test.print_summary()
        return 1
    
    # Run one credential request
    console.print()
    console.print("[cyan]Moving to credential request...[/cyan]")
    console.print()
    
    cred_test = CredentialRequestTest()
    cred_test.client = pairing_test.client  # Reuse paired client
    
    result2 = cred_test.test_credential_request_approved()
    cred_test.add_result(result2)
    
    # Combined summary
    console.print()
    console.print("=" * 70, style="cyan")
    console.print("  QUICK TEST SUMMARY", style="bold cyan")
    console.print("=" * 70, style="cyan")
    console.print()
    
    all_results = pairing_test.results + cred_test.results
    
    for result in all_results:
        if result.status == TestStatus.PASSED:
            console.print(f"[green]✓[/green] {result.test_name}: {result.message}")
        else:
            console.print(f"[red]✗[/red] {result.test_name}: {result.message}")
    
    console.print()
    
    failed = sum(1 for r in all_results if r.status != TestStatus.PASSED)
    if failed == 0:
        console.print("[bold green]✓ QUICK TEST PASSED[/bold green]")
        console.print()
        console.print("[bold]Key validations:[/bold]")
        console.print("  ✓ PAKE protocol works")
        console.print("  ✓ Vault unlocked during pairing")
        console.print("  ✓ NO password prompt during credential request")
        console.print()
        return 0
    else:
        console.print(f"[bold red]✗ {failed} TEST(S) FAILED[/bold red]")
        return 1


def run_all_tests() -> int:
    """
    Run all manual integration tests.
    
    Returns:
        Exit code
    """
    console = Console()
    console.print("[bold cyan]Running All Manual Tests[/bold cyan]")
    console.print()
    
    # Test 1: Pairing
    console.print("[bold]Test Suite 1: Pairing Flow[/bold]")
    pairing_test = PairingFlowTest()
    exit_code1 = pairing_test.run()
    
    if exit_code1 != 0:
        console.print("[red]Pairing tests failed - stopping[/red]")
        return exit_code1
    
    console.print()
    console.print("[green]✓ Pairing tests passed[/green]")
    console.print()
    from rich.prompt import Prompt
    response = Prompt.ask("Continue to credential tests?", choices=["y", "n"], default="y")
    if response != "y":
        return 0
    
    # Test 2: Credential requests
    console.print()
    console.print("[bold]Test Suite 2: Credential Requests[/bold]")
    cred_test = CredentialRequestTest()
    exit_code2 = cred_test.run()
    
    if exit_code2 != 0:
        console.print("[red]Credential tests failed - stopping[/red]")
        return exit_code2
    
    console.print()
    console.print("[green]✓ Credential tests passed[/green]")
    console.print()
    response = Prompt.ask("Continue to session management tests?", choices=["y", "n"], default="y")
    if response != "y":
        return 0
    
    # Test 3: Session management
    console.print()
    console.print("[bold]Test Suite 3: Session Management[/bold]")
    session_test = SessionManagementTest()
    exit_code3 = session_test.run()
    
    if exit_code3 != 0:
        console.print("[red]Session tests failed - stopping[/red]")
        return exit_code3
    
    console.print()
    console.print("[green]✓ Session tests passed[/green]")
    console.print()
    response = Prompt.ask("Continue to error case tests?", choices=["y", "n"], default="y")
    if response != "y":
        return 0
    
    # Test 4: Error cases
    console.print()
    console.print("[bold]Test Suite 4: Error Cases[/bold]")
    error_test = ErrorCasesTest()
    exit_code4 = error_test.run()
    
    # Final summary
    console.print()
    console.print("=" * 70, style="bold cyan")
    console.print("  ALL TESTS COMPLETE", style="bold cyan")
    console.print("=" * 70, style="bold cyan")
    console.print()
    
    all_passed = all(code == 0 for code in [exit_code1, exit_code2, exit_code3, exit_code4])
    
    if all_passed:
        console.print("[bold green]✓ ALL TEST SUITES PASSED[/bold green]")
        console.print()
        console.print("[bold]Validated:[/bold]")
        console.print("  ✓ PAKE protocol implementation")
        console.print("  ✓ Vault unlock timing (once during pairing)")
        console.print("  ✓ Encrypted credential requests")
        console.print("  ✓ Session management")
        console.print("  ✓ Error handling")
        console.print()
        return 0
    else:
        console.print("[bold red]✗ SOME TESTS FAILED[/bold red]")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manual Integration Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--test',
        choices=['pairing', 'credential', 'session', 'errors'],
        help='Run specific test suite'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick smoke test (5 minutes)'
    )
    
    parser.add_argument(
        '--server',
        default='http://localhost:5000',
        help='Approval server URL (default: http://localhost:5000)'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Run requested tests
    if args.quick:
        return run_quick_test()
    
    elif args.test == 'pairing':
        test = PairingFlowTest(args.server)
        return test.run()
    
    elif args.test == 'credential':
        test = CredentialRequestTest(args.server)
        return test.run()
    
    elif args.test == 'session':
        test = SessionManagementTest(args.server)
        return test.run()
    
    elif args.test == 'errors':
        test = ErrorCasesTest(args.server)
        return test.run()
    
    else:
        # Run all tests
        return run_all_tests()


if __name__ == '__main__':
    sys.exit(main())
