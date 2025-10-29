"""
Bitwarden CLI wrapper for vault operations.

This module provides a Python interface to the Bitwarden CLI tool,
handling subprocess execution, error handling, and JSON parsing.
"""
import json
import logging
import subprocess
from typing import List, Dict

logger = logging.getLogger(__name__)


class BitwardenCLIError(Exception):
    """Exception raised for Bitwarden CLI errors."""
    pass


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
