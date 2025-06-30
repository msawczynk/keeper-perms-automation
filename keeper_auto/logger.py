"""
Structured logging module for Keeper Permissions Automation.
Implements .jsonl logging format with run_id as specified in design document.
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
    Structured logger implementing design requirements:
    - Newline-delimited JSON (.jsonl) format
    - Keys: ts (RFC3339 UTC), run_id, level, event, data
    - Files named: perms-apply-YYYYMMDD.log.jsonl
    """
    
    def __init__(self, log_dir: Optional[Path] = None, run_id: Optional[str] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]  # Short run ID
        self.log_dir = log_dir or Path("./runs") / datetime.now().strftime("%Y-%m-%d")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file name according to design
        log_filename = f"perms-apply-{datetime.now().strftime('%Y%m%d')}.log.jsonl"
        self.log_file = self.log_dir / log_filename
        
    def _log(self, level: str, event: str, data: Optional[Dict[str, Any]] = None):
        """Internal logging method."""
        entry = LogEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            level=level,
            event=event,
            data=data
        )
        
        # Write to .jsonl file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(entry.to_json() + '\n')
    
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

# Global logger instance
_logger: Optional[StructuredLogger] = None

def get_logger(run_id: Optional[str] = None) -> StructuredLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None or (run_id and _logger.run_id != run_id):
        _logger = StructuredLogger(run_id=run_id)
    return _logger

def init_logger(run_id: Optional[str] = None, log_dir: Optional[Path] = None) -> StructuredLogger:
    """Initialize logger with specific configuration."""
    global _logger
    _logger = StructuredLogger(log_dir=log_dir, run_id=run_id)
    return _logger 