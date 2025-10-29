"""
Credential request data structures.

This module defines the structure for credential requests made by agents
to the Bitwarden credential management system.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CredentialRequest:
    """
    Request for credential from an agent.

    Attributes:
        agent_id: Unique identifier (e.g., "flight-booking-001")
        agent_name: Human-readable name for prompts
        domain: Domain name (e.g., "aa.com")
        reason: Human-readable explanation
        timestamp: When request was made
        timeout: Seconds to wait for approval
    """
    agent_id: str
    agent_name: str
    domain: str
    reason: str
    timestamp: datetime
    timeout: int = 300
