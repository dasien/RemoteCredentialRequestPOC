"""
Audit logging for credential access events.

This module provides audit logging functionality that tracks credential
requests and outcomes WITHOUT logging any credential values.
"""
import logging


class AuditLogger:
    """
    Audit logger for credential access events.

    CRITICAL: Never logs credential values.
    """

    def __init__(self, log_file: str = "credential_audit.log"):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
        """
        self.log_file = log_file
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure audit logger."""
        self.logger = logging.getLogger("credential_audit")
        self.logger.setLevel(logging.INFO)

        # File handler (append mode)
        handler = logging.FileHandler(self.log_file, mode='a')
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%SZ'
            )
        )
        self.logger.addHandler(handler)

    def log_request(
        self,
        agent_id: str,
        domain: str,
        reason: str
    ) -> None:
        """
        Log credential request.

        Args:
            agent_id: Requesting agent identifier
            domain: Domain requested
            reason: Reason for request
        """
        self.logger.info(
            f"REQUEST | agent={agent_id} | domain={domain} | reason={reason}"
        )

    def log_denial(self, agent_id: str, domain: str) -> None:
        """Log user denial of credential request."""
        self.logger.info(
            f"DENIED | agent={agent_id} | domain={domain}"
        )

    def log_success(self, agent_id: str, domain: str) -> None:
        """Log successful credential retrieval and use."""
        self.logger.info(
            f"SUCCESS | agent={agent_id} | domain={domain}"
        )

    def log_not_found(self, agent_id: str, domain: str) -> None:
        """Log credential not found in vault."""
        self.logger.warning(
            f"NOT_FOUND | agent={agent_id} | domain={domain}"
        )

    def log_error(
        self,
        agent_id: str,
        domain: str,
        error_message: str
    ) -> None:
        """
        Log error during credential retrieval.

        Args:
            agent_id: Requesting agent identifier
            domain: Domain requested
            error_message: Sanitized error message (no credentials)
        """
        # Sanitize error message (remove any potential credential data)
        safe_message = error_message[:200]  # Limit length
        self.logger.error(
            f"ERROR | agent={agent_id} | domain={domain} | error={safe_message}"
        )
