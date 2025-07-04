"""
Vault Storage Adapter - stores all system data in Keeper vault records.
Provides centralized, secure storage for logs, checkpoints, configurations, and reports.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict

from ..keeper_client import get_client, get_record, create_record, update_record, find_records_by_title
from ..models import ConfigRecord
from ..logger import LogEntry
from ..checkpoint import Checkpoint

@dataclass
class VaultStorageRecord:
    """Represents a record stored in the vault for system data."""
    record_uid: str
    title: str
    record_type: str  # 'log', 'checkpoint', 'config', 'report', 'template'
    data: Dict[str, Any]
    created_time: str
    updated_time: str
    run_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VaultStorageRecord':
        """Create from dictionary."""
        return cls(**data)

class VaultStorageAdapter:
    """
    Adapter for storing all system data in Keeper vault.
    
    Storage Organization:
    - [Perms-System] folder contains all system records
    - [Perms-System]/Logs/YYYY-MM-DD/ - Daily log records
    - [Perms-System]/Checkpoints/YYYY-MM-DD/ - Checkpoint records
    - [Perms-System]/Reports/YYYY-MM-DD/ - Operation reports
    - [Perms-System]/Templates/ - CSV templates
    - [Perms-System]/Configurations/ - System configurations
    """
    
    def __init__(self, system_folder_name: str = "[Perms-System]"):
        self.system_folder_name = system_folder_name
        self.client = get_client()
        self._system_folder_uid: Optional[str] = None
        self._folder_cache: Dict[str, str] = {}  # path -> folder_uid
        
    def _ensure_system_folder_structure(self) -> str:
        """Ensure the system folder structure exists and return system folder UID."""
        if self._system_folder_uid:
            return self._system_folder_uid
            
        # Create or find system folder
        from ..keeper_client import ensure_folder_path
        
        # Create main system folder
        self._system_folder_uid = ensure_folder_path(self.system_folder_name)
        
        # Create subfolders
        subfolders = [
            "Logs",
            "Checkpoints", 
            "Reports",
            "Templates",
            "Configurations"
        ]
        
        for subfolder in subfolders:
            subfolder_path = f"{self.system_folder_name}/{subfolder}"
            folder_uid = ensure_folder_path(subfolder_path)
            self._folder_cache[subfolder] = folder_uid
            
        return self._system_folder_uid
    
    def _get_daily_folder_uid(self, base_folder: str, date: datetime) -> str:
        """Get or create daily folder UID."""
        date_str = date.strftime("%Y-%m-%d")
        daily_path = f"{base_folder}/{date_str}"
        
        if daily_path not in self._folder_cache:
            from ..keeper_client import ensure_folder_path
            folder_path = f"{self.system_folder_name}/{daily_path}"
            folder_uid = ensure_folder_path(folder_path)
            self._folder_cache[daily_path] = folder_uid
            
        return self._folder_cache[daily_path]
    
    def store_log_entry(self, log_entry: LogEntry) -> str:
        """Store a single log entry in the vault."""
        self._ensure_system_folder_structure()
        
        # Create daily log folder
        log_date = datetime.fromisoformat(log_entry.ts.replace('Z', '+00:00'))
        daily_folder_uid = self._get_daily_folder_uid("Logs", log_date)
        
        # Create or update daily log record
        record_title = f"Perms-Log-{log_date.strftime('%Y%m%d')}"
        
        # Try to find existing log record for the day
        existing_records = find_records_by_title(record_title)
        
        if existing_records:
            # Append to existing log record
            record_uid = existing_records[0]['record_uid']
            record = get_record(record_uid)
            
            # Get existing log entries
            existing_logs = []
            if record and hasattr(record, 'data'):
                for field in record.data:
                    if field.type == 'multiline' and field.label == 'log_entries':
                        try:
                            existing_logs = json.loads(field.value)
                        except json.JSONDecodeError:
                            existing_logs = []
                        break
            
            # Add new log entry
            existing_logs.append(asdict(log_entry))
            
            # Update record
            record_data = {
                'title': record_title,
                'fields': [
                    {
                        'type': 'multiline',
                        'label': 'log_entries',
                        'value': json.dumps(existing_logs, indent=2)
                    },
                    {
                        'type': 'text',
                        'label': 'run_id',
                        'value': log_entry.run_id
                    },
                    {
                        'type': 'text',
                        'label': 'last_updated',
                        'value': datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
            
            update_record(record_uid, record_data)
            return record_uid
        else:
            # Create new log record
            record_data = {
                'title': record_title,
                'fields': [
                    {
                        'type': 'multiline',
                        'label': 'log_entries',
                        'value': json.dumps([asdict(log_entry)], indent=2)
                    },
                    {
                        'type': 'text',
                        'label': 'run_id',
                        'value': log_entry.run_id
                    },
                    {
                        'type': 'text',
                        'label': 'created',
                        'value': datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
            
            record_uid = create_record(record_data, daily_folder_uid)
            return record_uid
    
    def store_checkpoint(self, checkpoint: Checkpoint) -> str:
        """Store checkpoint data in the vault."""
        self._ensure_system_folder_structure()
        
        # Create daily checkpoint folder
        checkpoint_date = datetime.fromisoformat(checkpoint.start_time)
        daily_folder_uid = self._get_daily_folder_uid("Checkpoints", checkpoint_date)
        
        # Create checkpoint record
        record_title = f"Checkpoint-{checkpoint.run_id}"
        
        record_data = {
            'title': record_title,
            'fields': [
                {
                    'type': 'multiline',
                    'label': 'checkpoint_data',
                    'value': json.dumps(checkpoint.to_dict(), indent=2)
                },
                {
                    'type': 'text',
                    'label': 'run_id',
                    'value': checkpoint.run_id
                },
                {
                    'type': 'text',
                    'label': 'csv_file',
                    'value': checkpoint.csv_file
                },
                {
                    'type': 'text',
                    'label': 'status',
                    'value': 'completed' if checkpoint.completion_time else 'in_progress'
                }
            ]
        }
        
        record_uid = create_record(record_data, daily_folder_uid)
        return record_uid
    
    def store_operation_report(self, report_data: Dict[str, Any], run_id: str) -> str:
        """Store operation report in the vault."""
        self._ensure_system_folder_structure()
        
        # Create daily report folder
        report_date = datetime.now()
        daily_folder_uid = self._get_daily_folder_uid("Reports", report_date)
        
        # Create report record
        record_title = f"Operation-Report-{run_id}"
        
        record_data = {
            'title': record_title,
            'fields': [
                {
                    'type': 'multiline',
                    'label': 'report_data',
                    'value': json.dumps(report_data, indent=2)
                },
                {
                    'type': 'text',
                    'label': 'run_id',
                    'value': run_id
                },
                {
                    'type': 'text',
                    'label': 'operation_type',
                    'value': report_data.get('operation_type', 'unknown')
                },
                {
                    'type': 'text',
                    'label': 'success',
                    'value': str(report_data.get('success', False))
                },
                {
                    'type': 'text',
                    'label': 'created',
                    'value': datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        record_uid = create_record(record_data, daily_folder_uid)
        return record_uid
    
    def store_csv_template(self, template_data: str, template_name: str) -> str:
        """Store CSV template in the vault."""
        self._ensure_system_folder_structure()
        
        # Get templates folder
        templates_folder_uid = self._folder_cache.get("Templates")
        if not templates_folder_uid:
            from ..keeper_client import ensure_folder_path
            folder_path = f"{self.system_folder_name}/Templates"
            templates_folder_uid = ensure_folder_path(folder_path)
            self._folder_cache["Templates"] = templates_folder_uid
        
        # Create template record
        record_title = f"CSV-Template-{template_name}"
        
        record_data = {
            'title': record_title,
            'fields': [
                {
                    'type': 'multiline',
                    'label': 'csv_content',
                    'value': template_data
                },
                {
                    'type': 'text',
                    'label': 'template_name',
                    'value': template_name
                },
                {
                    'type': 'text',
                    'label': 'created',
                    'value': datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        record_uid = create_record(record_data, templates_folder_uid)
        return record_uid
    
    def store_configuration(self, config: ConfigRecord, config_name: str = "default") -> str:
        """Store configuration in the vault."""
        self._ensure_system_folder_structure()
        
        # Get configurations folder
        config_folder_uid = self._folder_cache.get("Configurations")
        if not config_folder_uid:
            from ..keeper_client import ensure_folder_path
            folder_path = f"{self.system_folder_name}/Configurations"
            config_folder_uid = ensure_folder_path(folder_path)
            self._folder_cache["Configurations"] = config_folder_uid
        
        # Create or update configuration record
        record_title = f"Perms-Config-{config_name}"
        
        # Try to find existing config record
        existing_records = find_records_by_title(record_title)
        
        config_data = {
            'root_folder_name': config.root_folder_name,
            'included_teams': config.included_teams,
            'included_folders': config.included_folders,
            'excluded_folders': config.excluded_folders
        }
        
        record_data = {
            'title': record_title,
            'fields': [
                {
                    'type': 'multiline',
                    'label': 'config_data',
                    'value': json.dumps(config_data, indent=2)
                },
                {
                    'type': 'text',
                    'label': 'config_name',
                    'value': config_name
                },
                {
                    'type': 'text',
                    'label': 'updated',
                    'value': datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        
        if existing_records:
            # Update existing record
            record_uid = existing_records[0]['record_uid']
            update_record(record_uid, record_data)
            return record_uid
        else:
            # Create new record
            record_uid = create_record(record_data, config_folder_uid)
            return record_uid
    
    def load_configuration(self, config_name: str = "default") -> Optional[ConfigRecord]:
        """Load configuration from the vault."""
        record_title = f"Perms-Config-{config_name}"
        
        # Find configuration record
        existing_records = find_records_by_title(record_title)
        
        if not existing_records:
            return None
        
        record_uid = existing_records[0]['record_uid']
        record = get_record(record_uid)
        
        if not record or not hasattr(record, 'data'):
            return None
        
        # Extract configuration data
        for field in record.data:
            if field.type == 'multiline' and field.label == 'config_data':
                try:
                    config_data = json.loads(field.value)
                    return ConfigRecord(
                        root_folder_name=config_data.get('root_folder_name', '[Perms]'),
                        included_teams=config_data.get('included_teams'),
                        included_folders=config_data.get('included_folders'),
                        excluded_folders=config_data.get('excluded_folders', [])
                    )
                except json.JSONDecodeError:
                    return None
        
        return None
    
    def load_checkpoint(self, run_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from the vault."""
        record_title = f"Checkpoint-{run_id}"
        
        # Find checkpoint record
        existing_records = find_records_by_title(record_title)
        
        if not existing_records:
            return None
        
        record_uid = existing_records[0]['record_uid']
        record = get_record(record_uid)
        
        if not record or not hasattr(record, 'data'):
            return None
        
        # Extract checkpoint data
        for field in record.data:
            if field.type == 'multiline' and field.label == 'checkpoint_data':
                try:
                    checkpoint_data = json.loads(field.value)
                    return Checkpoint.from_dict(checkpoint_data)
                except json.JSONDecodeError:
                    return None
        
        return None
    
    def get_daily_logs(self, date: datetime) -> List[LogEntry]:
        """Get all log entries for a specific date."""
        record_title = f"Perms-Log-{date.strftime('%Y%m%d')}"
        
        # Find log record
        existing_records = find_records_by_title(record_title)
        
        if not existing_records:
            return []
        
        record_uid = existing_records[0]['record_uid']
        record = get_record(record_uid)
        
        if not record or not hasattr(record, 'data'):
            return []
        
        # Extract log entries
        for field in record.data:
            if field.type == 'multiline' and field.label == 'log_entries':
                try:
                    log_entries_data = json.loads(field.value)
                    return [LogEntry(**entry) for entry in log_entries_data]
                except json.JSONDecodeError:
                    return []
        
        return []
    
    def list_checkpoints(self, date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """List all checkpoints, optionally filtered by date range."""
        # This would require a more complex search implementation
        # For now, return empty list as placeholder
        return []
    
    def cleanup_old_data(self, retention_days: int = 30) -> Dict[str, int]:
        """Clean up old data based on retention policy."""
        # This would implement the cleanup logic
        # For now, return empty stats as placeholder
        return {
            'logs_deleted': 0,
            'checkpoints_deleted': 0,
            'reports_deleted': 0
        }
    
    def export_system_data(self, date_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Export system data for backup or analysis."""
        # This would implement comprehensive data export
        # For now, return empty data as placeholder
        return {
            'export_date': datetime.now(timezone.utc).isoformat(),
            'date_range': date_range,
            'logs': [],
            'checkpoints': [],
            'reports': [],
            'configurations': []
        } 