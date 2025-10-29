"""
Terminal-based approval client for credential requests.

This is a simplified approval client that runs the server and handles
pairing/credential requests without an interactive command loop to avoid
threading conflicts with stdin.

Usage:
    python -m src.approval_client

The client will:
- Display pairing codes when agents initiate pairing
- Prompt for pairing code + master password
- Prompt for credential approvals (Y/N only, no password)
- Run until Ctrl+C

To pair:
    When you see a pairing code, you'll be prompted to enter it.

To quit:
    Press Ctrl+C
"""
import logging
import sys
import threading
import getpass
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from src.server.approval_server import run_server, pairing_manager

logger = logging.getLogger(__name__)


class ApprovalCallbackHandler:
    """Callback handler for PairingManager to interact with UI."""

    def __init__(self):
        """Initialize callback handler."""
        self.console = Console()
        self.pending_pairings = []

    def on_pairing_created(self, pairing_state):
        """
        Notify user of new pairing request.

        Args:
            pairing_state: PairingState object with agent details and code
        """
        self.console.print()
        panel = Panel(
            f"[bold cyan]Agent:[/bold cyan] {pairing_state.agent_name}\n"
            f"[bold cyan]Agent ID:[/bold cyan] {pairing_state.agent_id}\n\n"
            f"[bold yellow]Pairing code:[/bold yellow] [bold green]{pairing_state.pairing_code}[/bold green]\n\n"
            f"A pairing request has been received.\n"
            f"You will be prompted to enter the code and master password.",
            title="🔗 New Pairing Request",
            border_style="blue"
        )
        self.console.print(panel)
        self.console.print()

        # Store for processing
        self.pending_pairings.append(pairing_state)

    def handle_credential_request(self, session, domain, reason):
        """
        Prompt user for approval of credential request.

        CRITICAL: Vault is already unlocked (during pairing). No password prompt here.

        Args:
            session: Session object with agent details
            domain: Domain name being requested
            reason: Reason provided by agent

        Returns:
            Dict with 'approved' bool
        """
        self.console.print()
        self.console.print("[bold yellow]═══ Incoming Credential Request ═══[/bold yellow]")
        self.console.print()

        panel = Panel(
            f"[bold cyan]Agent:[/bold cyan] {session.agent_name}\n"
            f"[bold cyan]Domain:[/bold cyan] {domain}\n"
            f"[bold cyan]Reason:[/bold cyan] {reason}\n\n"
            f"[bold yellow]Allow this agent to access your credentials?[/bold yellow]",
            title="🔐 Credential Access Request",
            border_style="blue"
        )
        self.console.print(panel)
        self.console.print()

        # Simple Y/N prompt
        approved = Confirm.ask("[bold]Approve?[/bold]", default=False)

        if approved:
            self.console.print("[green]✓[/green] Approved - retrieving credential...")
            self.console.print()
            return {"approved": True}
        else:
            self.console.print("[red]✗[/red] Denied")
            self.console.print()
            return {"approved": False}


class ApprovalClient:
    """Simplified approval client without interactive command loop."""

    def __init__(self):
        """Initialize approval client."""
        self.console = Console()
        self.callback_handler = ApprovalCallbackHandler()
        self.running = True

    def run(self, host='127.0.0.1', port=5000):
        """
        Run approval client.

        Args:
            host: Host to bind server to (default: 127.0.0.1)
            port: Port to bind server to (default: 5000)
        """
        # Register callback handler
        pairing_manager.set_callback_handler(self.callback_handler)

        # Start Flask server in background thread
        server_thread = threading.Thread(
            target=run_server,
            args=(host, port),
            daemon=True
        )
        server_thread.start()
        logger.info(f"Flask server started on {host}:{port}")

        # Give server time to start
        time.sleep(1)

        # Display welcome
        self.console.print()
        self.console.print("[bold cyan]═══════════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold cyan]    Credential Approval Client - Remote Mode[/bold cyan]")
        self.console.print("[bold cyan]═══════════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print()
        self.console.print(f"[green]✓[/green] Server running on {host}:{port}")
        self.console.print()
        self.console.print("[bold yellow]Waiting for pairing requests...[/bold yellow]")
        self.console.print("[dim]Press Ctrl+C to quit[/dim]")
        self.console.print()

        try:
            # Simple loop that checks for pending pairings
            while self.running:
                # Check for pending pairings
                if self.callback_handler.pending_pairings:
                    pairing = self.callback_handler.pending_pairings.pop(0)
                    self._handle_pairing_prompt(pairing)

                # Sleep briefly to avoid busy-wait
                time.sleep(0.5)

        except KeyboardInterrupt:
            self.console.print()
            self.console.print("[yellow]Shutting down...[/yellow]")

    def _handle_pairing_prompt(self, pairing_state):
        """
        Prompt user to accept pairing.

        Args:
            pairing_state: PairingState object
        """
        self.console.print()
        self.console.print(f"[bold]Enter the pairing code shown above:[/bold]")
        code = Prompt.ask("[cyan]Pairing code[/cyan]")

        if code != pairing_state.pairing_code:
            self.console.print("[red]✗[/red] Code mismatch - ignoring")
            self.console.print()
            return

        # Get master password
        self.console.print()
        master_password = getpass.getpass("Bitwarden master password: ")

        if not master_password:
            self.console.print("[red]✗[/red] Password required")
            self.console.print()
            return

        # Process pairing
        success = pairing_manager.mark_user_entered_code(code, master_password)

        if success:
            self.console.print("[green]✓[/green] Pairing successful - vault unlocked")
            self.console.print("[yellow]Waiting for credential requests...[/yellow]")
            self.console.print()
        else:
            self.console.print("[red]✗[/red] Pairing failed (incorrect password or expired code)")
            self.console.print()


def main():
    """Main entry point for approval client."""
    from src.utils.logging_config import setup_logging

    # Setup logging
    setup_logging(level="INFO")

    # Create and run client
    client = ApprovalClient()
    try:
        client.run()
    except Exception as e:
        logger.error(f"Approval client error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()