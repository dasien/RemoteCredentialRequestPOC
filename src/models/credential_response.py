"""
Credential response data structures.

This module defines the response structure returned when a credential
is requested from the Bitwarden agent.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from src.utils.credential_handler import SecureCredential


class CredentialStatus(Enum):
    """Status of credential request."""
    APPROVED = "approved"      # User approved, credential retrieved
    DENIED = "denied"          # User denied request
    NOT_FOUND = "not_found"    # Credential not in vault
    ERROR = "error"            # Error during retrieval


@dataclass
class CredentialResponse:
    """
    Response to credential request.

    Attributes:
        status: Outcome of request
        credential: SecureCredential if approved, None otherwise
        error_message: Error details if status is ERROR or NOT_FOUND
    """
    status: CredentialStatus
    credential: Optional[SecureCredential]
    error_message: Optional[str]
