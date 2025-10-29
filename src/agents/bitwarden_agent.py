"""
Bitwarden agent for credential retrieval with user approval.

This agent handles the entire credential request flow including user
prompts, vault operations, and audit logging.
"""
import getpass
import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.models.credential_response import CredentialResponse, CredentialStatus
from src.utils.bitwarden_cli import BitwardenCLI, BitwardenCLIError
from src.utils.credential_handler import SecureCredential
from src.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


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
            if password:
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
