"""
Structured logging module for Keeper Permissions Automation.
Implements .jsonl logging format with run_id as specified in design document.
Enhanced with vault storage integration.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class LogEntry:
    """Structured log entry according to design specification."""
    ts: str  # RFC3339 UTC timestamp
    run_id: str  # Unique identifier for CLI command invocation
    level: str  # info, warning, error
    event: str  # Event type (e.g., share_record, create_folder)
    data: Optional[Dict[str, Any]] = None  # Arbitrary event data
    
    def to_json(self) -> str:
        """Convert to JSON string for .jsonl format."""
        return json.dumps(asdict(self), separators=(',', ':'))

class StructuredLogger:
    """
    Enhanced structured logger implementing design requirements:
    - Newline-delimited JSON (.jsonl) format
    - Keys: ts (RFC3339 UTC), run_id, level, event, data
    - Files named: perms-apply-YYYYMMDD.log.jsonl
    - Optional vault storage integration
    """
    
    def __init__(self, log_dir: Optional[Path] = None, run_id: Optional[str] = None, 
                 vault_storage: bool = False):
        self.run_id = run_id or str(uuid.uuid4())[:8]  # Short run ID
        self.log_dir = log_dir or Path("./runs") / datetime.now().strftime("%Y-%m-%d")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file name according to design
        log_filename = f"perms-apply-{datetime.now().strftime('%Y%m%d')}.log.jsonl"
        self.log_file = self.log_dir / log_filename
        
        # Vault storage integration
        self.vault_storage = vault_storage
        self._vault_adapter = None
        
        if self.vault_storage:
            try:
                from .infrastructure.vault_storage_adapter import VaultStorageAdapter
                self._vault_adapter = VaultStorageAdapter()
            except ImportError:
                print("Warning: Vault storage adapter not available, falling back to file logging")
                self.vault_storage = False
        
    def _log(self, level: str, event: str, data: Optional[Dict[str, Any]] = None):
        """Internal logging method with dual storage support."""
        entry = LogEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            level=level,
            event=event,
            data=data
        )
        
        # Always write to local .jsonl file for backup
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry.to_json() + '\n')
        
        # Also store in vault if enabled
        if self.vault_storage and self._vault_adapter:
            try:
                self._vault_adapter.store_log_entry(entry)
            except Exception as e:
                # Don't fail the main operation if vault storage fails
                print(f"Warning: Failed to store log entry in vault: {e}")
    
    def info(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log info level event."""
        self._log("info", event, data)
    
    def warning(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log warning level event."""
        self._log("warning", event, data)
    
    def error(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log error level event."""
        self._log("error", event, data)
    
    def log_operation(self, operation: str, record_uid: Optional[str] = None, folder_uid: Optional[str] = None, **kwargs: Any):
        """Log a specific operation with standard data fields."""
        data = {"operation": operation}
        if record_uid:
            data["record_uid"] = record_uid
        if folder_uid:
            data["folder_uid"] = folder_uid
        data.update(kwargs)
        
        self.info("operation", data)
    
    def log_validation_result(self, is_valid: bool, error_count: int, warning_count: int, row_count: int):
        """Log CSV validation results."""
        self.info("validation_complete", {
            "is_valid": is_valid,
            "error_count": error_count,
            "warning_count": warning_count,
            "row_count": row_count
        })
    
    def log_apply_summary(self, success: bool, total_operations: int, failed_operations: int):
        """Log apply operation summary."""
        self.info("apply_complete", {
            "success": success,
            "total_operations": total_operations,
            "failed_operations": failed_operations
        })
    
    def log_vault_storage_event(self, event_type: str, record_uid: str, success: bool, error: Optional[str] = None):
        """Log vault storage specific events."""
        data = {
            "event_type": event_type,
            "record_uid": record_uid,
            "success": success
        }
        if error:
            data["error"] = error
        
        if success:
            self.info("vault_storage", data)
        else:
            self.error("vault_storage_failed", data)
    
    def create_operation_report(self, operation_type: str, success: bool, 
                              total_operations: int, failed_operations: int,
                              additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a comprehensive operation report."""
        report = {
            "operation_type": operation_type,
            "run_id": self.run_id,
            "success": success,
            "total_operations": total_operations,
            "failed_operations": failed_operations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_file": str(self.log_file)
        }
        
        if additional_data:
            report.update(additional_data)
        
        # Store report in vault if enabled
        if self.vault_storage and self._vault_adapter:
            try:
                report_uid = self._vault_adapter.store_operation_report(report, self.run_id)
                report["vault_record_uid"] = report_uid
                self.log_vault_storage_event("operation_report", report_uid, True)
            except Exception as e:
                self.log_vault_storage_event("operation_report", "", False, str(e))
        
        return report

# Global logger instance
_logger: Optional[StructuredLogger] = None

def init_logger(run_id: Optional[str] = None, log_dir: Optional[Path] = None, 
                vault_storage: bool = False) -> StructuredLogger:
    """Initialize logger with specific configuration."""
    global _logger
    _logger = StructuredLogger(log_dir=log_dir, run_id=run_id, vault_storage=vault_storage)
    return _logger

def get_logger() -> StructuredLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = init_logger()
    return _logger

def log_info(event: str, data: Optional[Dict[str, Any]] = None):
    """Convenience function for info logging."""
    get_logger().info(event, data)

def log_warning(event: str, data: Optional[Dict[str, Any]] = None):
    """Convenience function for warning logging."""
    get_logger().warning(event, data)

def log_error(event: str, data: Optional[Dict[str, Any]] = None):
    """Convenience function for error logging."""
    get_logger().error(event, data) 