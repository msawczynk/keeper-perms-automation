"""Exception classes for Keeper Permissions Automation Tool."""

from typing import Dict, Any, Optional


class KeeperAutomationError(Exception):
    """Base exception for all Keeper automation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        return self.message


class AuthenticationError(KeeperAutomationError):
    """Raised when authentication fails."""
    pass


class ConfigurationError(KeeperAutomationError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(KeeperAutomationError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {"field": field, "value": value}
        super().__init__(message, details)
        self.field = field
        self.value = value


class CSVError(KeeperAutomationError):
    """Raised when CSV operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, line_number: Optional[int] = None):
        details = {"file_path": file_path, "line_number": line_number}
        super().__init__(message, details)
        self.file_path = file_path
        self.line_number = line_number


class APIError(KeeperAutomationError):
    """Raised when Keeper API operations fail."""
    
    def __init__(self, message: str, response: Optional[Dict[str, Any]] = None, command: Optional[str] = None, error_code: Optional[str] = None):
        """Initialize APIError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        response : dict | None
            Raw JSON response from Keeper (if available).
        command : str | None
            KeeperCommander command that triggered the error.
        error_code : str | None
            Optional short error code identifier. Accepted for backward-compatibility with older tests and
            wrappers. If provided it is stored on the instance and also included in the ``details`` mapping so it
            shows up when the exception is serialised.
        """
        details = {"response": response, "command": command, "error_code": error_code}
        super().__init__(message, details)
        self.response = response
        self.command = command
        self.error_code = error_code


class PermissionError(KeeperAutomationError):
    """Raised when permission operations fail."""
    pass


class FolderError(KeeperAutomationError):
    """Raised when folder operations fail."""
    pass


class TeamError(KeeperAutomationError):
    """Raised when team operations fail."""
    
    def __init__(self, message: str, team_uid: Optional[str] = None, team_name: Optional[str] = None):
        details = {"team_uid": team_uid, "team_name": team_name}
        super().__init__(message, details)
        self.team_uid = team_uid
        self.team_name = team_name


class RecordError(KeeperAutomationError):
    """Raised when record operations fail."""
    pass


def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    if isinstance(error, KeeperAutomationError):
        return str(error)
    else:
        return f"Unexpected error: {error}"


# Additional generic error wrappers for backwards-compatibility with older test-suites
class OperationError(KeeperAutomationError):
    """Raised when a generic operation fails (deprecated)."""


class DataError(KeeperAutomationError):
    """Raised when a data-processing operation fails (deprecated)."""


class NetworkError(KeeperAutomationError):
    """Raised for networking/I-O problems (deprecated).""" 