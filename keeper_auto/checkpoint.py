"""
Checkpoint and resume functionality for idempotent operations.
Implements checkpoint-<runID>.json files as specified in design document.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class OperationType(Enum):
    """Types of operations that can be checkpointed."""
    CREATE_FOLDER = "create_folder"
    SHARE_RECORD = "share_record"
    SET_PERMISSIONS = "set_permissions"
    ENSURE_FOLDER_PATH = "ensure_folder_path"

@dataclass
class CheckpointOperation:
    """Individual operation in a checkpoint."""
    operation_type: str
    record_uid: Optional[str] = None
    folder_uid: Optional[str] = None
    folder_path: Optional[str] = None
    team_uid: Optional[str] = None
    team_name: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None
    completed: bool = False
    error: Optional[str] = None
    timestamp: Optional[str] = None

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

class CheckpointManager:
    """
    Manages checkpoint files for idempotent operations.
    
    According to design:
    - Files written to ./runs/YYYY-MM-DD/
    - Named checkpoint-<runID>.json  
    - Captures created folders & links
    - Supports --resume <file> flag
    """
    
    def __init__(self, run_id: Optional[str] = None, checkpoint_dir: Optional[Path] = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.checkpoint_dir = checkpoint_dir or Path("./runs") / datetime.now().strftime("%Y-%m-%d")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint-{self.run_id}.json"
        self.checkpoint: Optional[Checkpoint] = None
    
    def create_checkpoint(self, context: Dict[str, Any]) -> str:
        """Create a new checkpoint and return the file path."""
        self.checkpoint = Checkpoint(
            run_id=self.run_id,
            csv_file=context.get('csv_path', 'unknown'),
            start_time=datetime.now().isoformat(),
            total_operations=0  # Simplified for this refactoring
        )
        self._save_checkpoint()
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
    
    def add_operation(self, operation_type: OperationType, **kwargs: Any) -> CheckpointOperation:
        """Add a new operation to the checkpoint."""
        if not self.checkpoint:
            raise ValueError("Checkpoint not initialized")
        
        operation = CheckpointOperation(
            operation_type=operation_type.value,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )
        
        if self.checkpoint.operations is None:
            self.checkpoint.operations = []
        
        self.checkpoint.operations.append(operation)
        self._save_checkpoint()
        return operation
    
    def complete_operation(self, operation_index: int, success: bool = True, error: Optional[str] = None):
        """Mark an operation as completed."""
        if not self.checkpoint or not self.checkpoint.operations or operation_index >= len(self.checkpoint.operations):
            return
        
        operation = self.checkpoint.operations[operation_index]
        operation.completed = success
        operation.error = error
        
        if success:
            self.checkpoint.completed_operations += 1
        
        self._save_checkpoint()
    
    def get_pending_operations(self) -> List[CheckpointOperation]:
        """Get operations that haven't been completed yet."""
        if not self.checkpoint or not self.checkpoint.operations:
            return []
        
        return [op for op in self.checkpoint.operations if not op.completed]
    
    def get_completed_operations(self) -> List[CheckpointOperation]:
        """Get operations that have been completed."""
        if not self.checkpoint or not self.checkpoint.operations:
            return []
        
        return [op for op in self.checkpoint.operations if op.completed]
    
    def complete_checkpoint(self):
        """Mark checkpoint as complete."""
        if self.checkpoint:
            self.checkpoint.completion_time = datetime.now().isoformat()
            self._save_checkpoint()
    
    def _save_checkpoint(self):
        """Save checkpoint to file."""
        if self.checkpoint:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint.to_dict(), f, indent=2)
    
    def cleanup_old_checkpoints(self, days_to_keep: int = 30):
        """Clean up checkpoint files older than specified days."""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        for checkpoint_file in self.checkpoint_dir.glob("checkpoint-*.json"):
            if checkpoint_file.stat().st_mtime < cutoff_date:
                try:
                    checkpoint_file.unlink()
                except Exception as e:
                    print(f"Failed to delete old checkpoint {checkpoint_file}: {e}")

def create_checkpoint_manager(run_id: Optional[str] = None, checkpoint_dir: Optional[Path] = None) -> CheckpointManager:
    """Factory function to create checkpoint manager."""
    return CheckpointManager(run_id=run_id, checkpoint_dir=checkpoint_dir) 