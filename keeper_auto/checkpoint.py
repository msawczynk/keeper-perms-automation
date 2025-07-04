"""
Checkpoint management for idempotent operations.
Enhanced with vault storage integration.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

@dataclass
class CheckpointOperation:
    """Individual operation within a checkpoint."""
    operation_type: str  # 'create_folder', 'share_record', 'add_team'
    target_uid: str  # UID of the target (folder, record, etc.)
    target_name: str  # Human-readable name
    status: str  # 'pending', 'completed', 'failed'
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
    
    def mark_completed(self):
        """Mark operation as completed."""
        self.status = 'completed'
        self.timestamp = datetime.now().isoformat()
    
    def mark_failed(self, error: str):
        """Mark operation as failed with error message."""
        self.status = 'failed'
        self.error_message = error
        self.timestamp = datetime.now().isoformat()

@dataclass
class Checkpoint:
    """Checkpoint file structure according to design."""
    run_id: str
    csv_file: str
    start_time: str
    completion_time: Optional[str] = None
    total_operations: int = 0
    completed_operations: int = 0
    operations: Optional[List[CheckpointOperation]] = None
    vault_record_uid: Optional[str] = None  # UID of checkpoint record in vault
    
    def __post_init__(self):
        if self.operations is None:
            self.operations = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create checkpoint from dictionary."""
        operations = [CheckpointOperation(**op) for op in data.get('operations', [])]
        data['operations'] = operations
        return cls(**data)
    
    def add_operation(self, operation: CheckpointOperation):
        """Add an operation to the checkpoint."""
        if self.operations is None:
            self.operations = []
        self.operations.append(operation)
        self.total_operations = len(self.operations)
    
    def mark_operation_completed(self, target_uid: str):
        """Mark a specific operation as completed."""
        if self.operations:
            for op in self.operations:
                if op.target_uid == target_uid and op.status == 'pending':
                    op.mark_completed()
                    self.completed_operations = sum(1 for op in self.operations if op.status == 'completed')
                    break
    
    def mark_operation_failed(self, target_uid: str, error: str):
        """Mark a specific operation as failed."""
        if self.operations:
            for op in self.operations:
                if op.target_uid == target_uid and op.status == 'pending':
                    op.mark_failed(error)
                    break
    
    def get_pending_operations(self) -> List[CheckpointOperation]:
        """Get all pending operations."""
        return [op for op in (self.operations or []) if op.status == 'pending']
    
    def is_completed(self) -> bool:
        """Check if all operations are completed."""
        if not self.operations:
            return True
        return all(op.status in ['completed', 'failed'] for op in self.operations)
    
    def mark_completed(self):
        """Mark the entire checkpoint as completed."""
        self.completion_time = datetime.now().isoformat()
        self.completed_operations = sum(1 for op in (self.operations or []) if op.status == 'completed')

class CheckpointManager:
    """
    Enhanced checkpoint manager with vault storage integration.
    
    According to design:
    - Files written to ./runs/YYYY-MM-DD/
    - Named checkpoint-<runID>.json  
    - Captures created folders & links
    - Supports --resume <file> flag
    - Optional vault storage for centralized management
    """
    
    def __init__(self, run_id: Optional[str] = None, checkpoint_dir: Optional[Path] = None,
                 vault_storage: bool = False):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.checkpoint_dir = checkpoint_dir or Path("./runs") / datetime.now().strftime("%Y-%m-%d")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint-{self.run_id}.json"
        self.checkpoint: Optional[Checkpoint] = None
        
        # Vault storage integration
        self.vault_storage = vault_storage
        self._vault_adapter = None
        
        if self.vault_storage:
            try:
                from .infrastructure.vault_storage_adapter import VaultStorageAdapter
                self._vault_adapter = VaultStorageAdapter()
            except ImportError:
                print("Warning: Vault storage adapter not available, falling back to file storage")
                self.vault_storage = False
    
    def create_checkpoint(self, context: Dict[str, Any]) -> str:
        """Create a new checkpoint and return the file path."""
        self.checkpoint = Checkpoint(
            run_id=self.run_id,
            csv_file=context.get('csv_path', 'unknown'),
            start_time=datetime.now().isoformat(),
            total_operations=0  # Will be updated as operations are added
        )
        
        # Save to local file
        self._save_checkpoint()
        
        # Save to vault if enabled
        if self.vault_storage and self._vault_adapter:
            try:
                vault_record_uid = self._vault_adapter.store_checkpoint(self.checkpoint)
                self.checkpoint.vault_record_uid = vault_record_uid
                self._save_checkpoint()  # Update local file with vault UID
            except Exception as e:
                print(f"Warning: Failed to store checkpoint in vault: {e}")
        
        return str(self.checkpoint_file)
    
    def load_checkpoint(self, checkpoint_file: Path) -> Optional[Checkpoint]:
        """Load existing checkpoint for resume."""
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.checkpoint = Checkpoint.from_dict(data)
                self.checkpoint_file = checkpoint_file
                return self.checkpoint
        except Exception as e:
            print(f"Failed to load checkpoint: {e}")
        return None
    
    def load_checkpoint_from_vault(self, run_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from vault by run_id."""
        if not self.vault_storage or not self._vault_adapter:
            return None
        
        try:
            checkpoint = self._vault_adapter.load_checkpoint(run_id)
            if checkpoint:
                self.checkpoint = checkpoint
                self.run_id = run_id
                return checkpoint
        except Exception as e:
            print(f"Failed to load checkpoint from vault: {e}")
        return None
    
    def add_operation(self, operation_type: str, target_uid: str, target_name: str) -> CheckpointOperation:
        """Add a new operation to the checkpoint."""
        if not self.checkpoint:
            raise Exception("No checkpoint created. Call create_checkpoint first.")
        
        operation = CheckpointOperation(
            operation_type=operation_type,
            target_uid=target_uid,
            target_name=target_name,
            status='pending'
        )
        
        self.checkpoint.add_operation(operation)
        self._save_checkpoint()
        
        return operation
    
    def mark_operation_completed(self, target_uid: str):
        """Mark an operation as completed."""
        if self.checkpoint:
            self.checkpoint.mark_operation_completed(target_uid)
            self._save_checkpoint()
            
            # Update vault if enabled
            if self.vault_storage and self._vault_adapter and self.checkpoint.vault_record_uid:
                try:
                    self._vault_adapter.store_checkpoint(self.checkpoint)
                except Exception as e:
                    print(f"Warning: Failed to update checkpoint in vault: {e}")
    
    def mark_operation_failed(self, target_uid: str, error: str):
        """Mark an operation as failed."""
        if self.checkpoint:
            self.checkpoint.mark_operation_failed(target_uid, error)
            self._save_checkpoint()
            
            # Update vault if enabled
            if self.vault_storage and self._vault_adapter and self.checkpoint.vault_record_uid:
                try:
                    self._vault_adapter.store_checkpoint(self.checkpoint)
                except Exception as e:
                    print(f"Warning: Failed to update checkpoint in vault: {e}")
    
    def complete_checkpoint(self):
        """Mark the checkpoint as completed."""
        if self.checkpoint:
            self.checkpoint.mark_completed()
            self._save_checkpoint()
            
            # Update vault if enabled
            if self.vault_storage and self._vault_adapter and self.checkpoint.vault_record_uid:
                try:
                    self._vault_adapter.store_checkpoint(self.checkpoint)
                except Exception as e:
                    print(f"Warning: Failed to update checkpoint in vault: {e}")
    
    def get_pending_operations(self) -> List[CheckpointOperation]:
        """Get all pending operations from the checkpoint."""
        if self.checkpoint:
            return self.checkpoint.get_pending_operations()
        return []
    
    def _save_checkpoint(self):
        """Save checkpoint to local file."""
        if self.checkpoint:
            try:
                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(self.checkpoint.to_dict(), f, indent=2)
            except Exception as e:
                print(f"Failed to save checkpoint: {e}")
    
    def get_checkpoint_summary(self) -> Dict[str, Any]:
        """Get a summary of the checkpoint status."""
        if not self.checkpoint:
            return {"error": "No checkpoint available"}
        
        summary = {
            "run_id": self.checkpoint.run_id,
            "csv_file": self.checkpoint.csv_file,
            "start_time": self.checkpoint.start_time,
            "completion_time": self.checkpoint.completion_time,
            "total_operations": self.checkpoint.total_operations,
            "completed_operations": self.checkpoint.completed_operations,
            "pending_operations": len(self.checkpoint.get_pending_operations()),
            "is_completed": self.checkpoint.is_completed(),
            "vault_stored": self.checkpoint.vault_record_uid is not None
        }
        
        if self.checkpoint.operations:
            failed_ops = [op for op in self.checkpoint.operations if op.status == 'failed']
            summary["failed_operations"] = len(failed_ops)
            if failed_ops:
                summary["failed_operation_details"] = [
                    {
                        "operation_type": op.operation_type,
                        "target_name": op.target_name,
                        "error": op.error_message
                    }
                    for op in failed_ops
                ]
        
        return summary 