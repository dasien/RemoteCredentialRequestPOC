"""
Base class for manual integration tests.

Provides common utilities for test execution, user interaction,
and result reporting.

Location: tests/manual/base.py
"""
import sys
import time
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class TestResult:
    """Result of a test execution."""
    test_name: str
    status: TestStatus
    message: str
    duration: float = 0.0
    error: Optional[str] = None


class ManualTestBase:
    """
    Base class for manual integration tests.
    
    Provides common functionality for terminal coordination,
    user prompts, and result reporting.
    """
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        Initialize manual test base.
        
        Args:
            server_url: URL of approval server (default: http://localhost:5000)
        """
        self.server_url = server_url
        self.console = Console()
        self.results: List[TestResult] = []
        
        # Setup logging to show only errors
        logging.basicConfig(
            level=logging.ERROR,
            format='%(levelname)s: %(message)s'
        )
    
    def print_header(self, title: str):
        """Print test header."""
        self.console.print()
        self.console.print("=" * 70, style="cyan")
        self.console.print(f"  {title}", style="bold cyan")
        self.console.print("=" * 70, style="cyan")
        self.console.print()
    
    def print_section(self, title: str):
        """Print section header."""
        self.console.print()
        self.console.print(f"[bold yellow]{title}[/bold yellow]")
        self.console.print("-" * 70)
    
    def print_step(self, step: str):
        """Print test step."""
        self.console.print(f"[cyan]→[/cyan] {step}")
    
    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        self.console.print(f"[red]✗[/red] {message}")
    
    def print_warning(self, message: str):
        """Print warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")
    
    def print_action_required(self, message: str):
        """Print action required for user."""
        panel = Panel(
            message,
            title="🔵 ACTION REQUIRED IN TERMINAL 1",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print()
        self.console.print(panel)
        self.console.print()
    
    def wait_for_user(self, message: str = "Press Enter when ready..."):
        """Wait for user confirmation."""
        self.console.print()
        Prompt.ask(f"[dim]{message}[/dim]")
    
    def check_prerequisites(self) -> bool:
        """
        Check if prerequisites are met for manual testing.
        
        Returns:
            True if all prerequisites met, False otherwise
        """
        self.print_section("Checking Prerequisites")
        
        all_ok = True
        
        # Check 1: Approval server running
        self.print_step("Checking approval server...")
        try:
            import requests
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                self.print_success("Approval server is running")
            else:
                self.print_error("Approval server returned error")
                all_ok = False
        except Exception as e:
            self.print_error(f"Approval server not reachable: {e}")
            self.print_info("Make sure approval client is running in Terminal 1")
            self.print_info("Run: python -m src.approval_client")
            all_ok = False
        
        # Check 2: Bitwarden CLI
        self.print_step("Checking Bitwarden CLI...")
        try:
            import subprocess
            result = subprocess.run(
                ['bw', 'status'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.print_success("Bitwarden CLI is available")
            else:
                self.print_error("Bitwarden CLI status check failed")
                all_ok = False
        except FileNotFoundError:
            self.print_error("Bitwarden CLI not found")
            self.print_info("Install: https://bitwarden.com/help/cli/")
            all_ok = False
        except Exception as e:
            self.print_warning(f"Could not verify Bitwarden CLI: {e}")
        
        self.console.print()
        return all_ok
    
    def add_result(self, result: TestResult):
        """Add test result to results list."""
        self.results.append(result)
    
    def print_summary(self):
        """Print test execution summary."""
        self.console.print()
        self.console.print("=" * 70, style="cyan")
        self.console.print("  TEST SUMMARY", style="bold cyan")
        self.console.print("=" * 70, style="cyan")
        self.console.print()
        
        if not self.results:
            self.console.print("[yellow]No tests executed[/yellow]")
            return
        
        # Create summary table
        table = Table(title="Test Results")
        table.add_column("Test", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration", style="yellow")
        table.add_column("Message")
        
        passed = 0
        failed = 0
        skipped = 0
        
        for result in self.results:
            if result.status == TestStatus.PASSED:
                status_str = "[green]✓ PASSED[/green]"
                passed += 1
            elif result.status == TestStatus.FAILED:
                status_str = "[red]✗ FAILED[/red]"
                failed += 1
            elif result.status == TestStatus.SKIPPED:
                status_str = "[yellow]⊘ SKIPPED[/yellow]"
                skipped += 1
            else:
                status_str = "[dim]○ PENDING[/dim]"
            
            duration_str = f"{result.duration:.2f}s"
            
            message = result.message
            if result.error:
                message = f"{message}\n[red]{result.error}[/red]"
            
            table.add_row(
                result.test_name,
                status_str,
                duration_str,
                message
            )
        
        self.console.print(table)
        self.console.print()
        
        # Print counts
        total = len(self.results)
        self.console.print(f"[bold]Total:[/bold] {total} tests")
        self.console.print(f"[green]Passed:[/green] {passed}")
        self.console.print(f"[red]Failed:[/red] {failed}")
        self.console.print(f"[yellow]Skipped:[/yellow] {skipped}")
        self.console.print()
        
        # Overall status
        if failed == 0 and passed > 0:
            self.console.print("[bold green]✓ ALL TESTS PASSED[/bold green]")
        elif failed > 0:
            self.console.print(f"[bold red]✗ {failed} TEST(S) FAILED[/bold red]")
        else:
            self.console.print("[yellow]No tests passed[/yellow]")
        
        self.console.print()
    
    def run(self) -> int:
        """
        Run the test suite.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        raise NotImplementedError("Subclasses must implement run()")
