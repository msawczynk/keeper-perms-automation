"""
Logging adapter - provides structured logging interface.
Wraps the existing logger module with clean interface.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from ..logger import init_logger

class LoggingAdapter:
    """Adapter for structured logging operations."""
    
    def __init__(self, run_id: Optional[str] = None, log_dir: Optional[Path] = None, vault_storage: bool = False):
        self.logger = init_logger(run_id=run_id, log_dir=log_dir, vault_storage=vault_storage)
    
    def info(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log info level event."""
        self.logger.info(event, data)
    
    def warning(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log warning level event."""
        self.logger.warning(event, data)
    
    def error(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log error level event."""
        self.logger.error(event, data)
    
    def log_operation(self, operation: str, **kwargs: Any):
        """Log a specific operation."""
        self.logger.log_operation(operation, **kwargs)
    
    def log_validation_result(self, is_valid: bool, error_count: int, warning_count: int, row_count: int):
        """Log validation results."""
        self.logger.log_validation_result(is_valid, error_count, warning_count, row_count)
    
    def log_apply_summary(self, success: bool, total_operations: int, failed_operations: int):
        """Log apply operation summary."""
        self.logger.log_apply_summary(success, total_operations, failed_operations)
    
    def create_operation_report(self, operation_type: str, success: bool, 
                              total_operations: int, failed_operations: int,
                              additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a comprehensive operation report."""
        return self.logger.create_operation_report(operation_type, success, total_operations, failed_operations, additional_data)
    
    @property
    def run_id(self) -> str:
        """Get the run ID."""
        return self.logger.run_id
    
    @property
    def log_file(self) -> Path:
        """Get the log file path."""
        return self.logger.log_file

def create_logging_adapter(run_id: Optional[str] = None, log_dir: Optional[Path] = None, vault_storage: bool = False) -> LoggingAdapter:
    """Factory function to create logging adapter."""
    return LoggingAdapter(run_id=run_id, log_dir=log_dir, vault_storage=vault_storage) 