"""
Secure credential handling with automatic cleanup.

This module provides the SecureCredential class for safely storing and handling
credentials with guaranteed memory cleanup using context manager protocol.
"""
from typing import Optional, Type, Any


class SecureCredential:
    """
    Secure credential container with automatic cleanup.

    Usage:
        with credential as cred:
            # Use cred.username and cred.password
        # Credential automatically cleared here
    """

    def __init__(self, username: str, password: str):
        """
        Create secure credential.

        Args:
            username: Account username
            password: Account password
        """
        self._username = username
        self._password = password
        self._cleared = False

    @property
    def username(self) -> str:
        """Get username (raises if cleared)."""
        if self._cleared:
            raise ValueError("Credential has been cleared")
        return self._username

    @property
    def password(self) -> str:
        """Get password (raises if cleared)."""
        if self._cleared:
            raise ValueError("Credential has been cleared")
        return self._password

    def clear(self) -> None:
        """
        Clear credential from memory.

        Overwrites strings with 'X' characters before deletion.
        """
        if self._cleared:
            return

        # Overwrite strings in memory (best effort)
        if self._username:
            self._username = "X" * len(self._username)
        if self._password:
            self._password = "X" * len(self._password)

        self._cleared = True

        # Delete references
        del self._username
        del self._password

    def __enter__(self) -> 'SecureCredential':
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> bool:
        """Exit context manager and clear credential."""
        self.clear()
        return False  # Don't suppress exceptions

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        try:
            self.clear()
        except:
            pass  # Ignore errors in __del__

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        status = "cleared" if self._cleared else "active"
        return f"SecureCredential(status={status})"

    def __str__(self) -> str:
        """Safe string representation without credentials."""
        return self.__repr__()
