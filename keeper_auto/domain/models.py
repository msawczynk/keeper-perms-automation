"""
Core domain models for Keeper Permissions Automation.
Atomic models with single responsibilities and built-in validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import re
from pathlib import Path

class PermissionLevel(Enum):
    """Enumeration of permission levels according to design specification."""
    READ_ONLY = "ro"
    READ_WRITE = "rw"
    READ_WRITE_SHARE = "rws"
    MANAGE_RECORDS = "mgr"
    ADMIN = "admin"
    
    @classmethod
    def from_string(cls, value: str) -> Optional['PermissionLevel']:
        """Create PermissionLevel from string value."""
        try:
            for level in cls:
                if level.value == value.lower().strip():
                    return level
        except (AttributeError, ValueError):
            pass
        return None
    
    def to_permissions(self) -> Dict[str, bool]:
        """Convert to detailed permission mapping per design specification."""
        mapping = {
            self.READ_ONLY: {"can_edit": False, "can_share": False, "manage_records": False, "manage_users": False},
            self.READ_WRITE: {"can_edit": True, "can_share": False, "manage_records": False, "manage_users": False},
            self.READ_WRITE_SHARE: {"can_edit": True, "can_share": True, "manage_records": False, "manage_users": False},
            self.MANAGE_RECORDS: {"can_edit": True, "can_share": True, "manage_records": True, "manage_users": False},
            self.ADMIN: {"can_edit": True, "can_share": True, "manage_records": True, "manage_users": True}
        }
        return mapping[self]

@dataclass(frozen=True)
class EntityUID:
    """Value object for entity UIDs with validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("EntityUID must be a non-empty string")
        # Basic UID validation (alphanumeric, hyphens, underscores)
        if not re.match(r'^[A-Za-z0-9_-]+$', self.value.strip()):
            raise ValueError(f"Invalid UID format: {self.value}")
        object.__setattr__(self, 'value', self.value.strip())
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class Team:
    """Atomic team model."""
    uid: EntityUID
    name: str
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Team name cannot be empty")
        object.__setattr__(self, 'name', self.name.strip())
    
    @classmethod
    def create(cls, uid: str, name: str) -> 'Team':
        """Factory method for creating Team instances."""
        return cls(uid=EntityUID(uid), name=name)

@dataclass(frozen=True)
class Record:
    """Atomic record model."""
    uid: EntityUID
    title: str
    folder_path: str = ""
    
    def __post_init__(self):
        if not self.title or not self.title.strip():
            raise ValueError("Record title cannot be empty")
        object.__setattr__(self, 'title', self.title.strip())
        object.__setattr__(self, 'folder_path', self.folder_path.strip())
    
    @classmethod
    def create(cls, uid: str, title: str, folder_path: str = "") -> 'Record':
        """Factory method for creating Record instances."""
        return cls(uid=EntityUID(uid), title=title, folder_path=folder_path)

@dataclass(frozen=True)
class Folder:
    """Atomic folder model."""
    uid: EntityUID
    name: str
    path: str
    is_shared: bool = False
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Folder name cannot be empty")
        object.__setattr__(self, 'name', self.name.strip())
        object.__setattr__(self, 'path', self.path.strip())
    
    @classmethod
    def create(cls, uid: str, name: str, path: str, is_shared: bool = False) -> 'Folder':
        """Factory method for creating Folder instances."""
        return cls(uid=EntityUID(uid), name=name, path=path, is_shared=is_shared)

@dataclass(frozen=True)
class Permission:
    """Atomic permission assignment."""
    team: Team
    record: Record
    level: PermissionLevel
    
    def to_detailed_permissions(self) -> Dict[str, bool]:
        """Convert to detailed permissions for Keeper SDK."""
        return self.level.to_permissions()
    
    @classmethod
    def create(cls, team: Team, record: Record, permission_value: str) -> 'Permission':
        """Factory method for creating Permission instances."""
        level = PermissionLevel.from_string(permission_value)
        if level is None:
            raise ValueError(f"Invalid permission value: {permission_value}")
        return cls(team=team, record=record, level=level)

@dataclass
class ConfigRecord:
    """Configuration record model with validation."""
    root_folder_name: str = "[Perms]"
    included_teams: Optional[List[str]] = None
    included_folders: Optional[List[str]] = None
    excluded_folders: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.root_folder_name or not self.root_folder_name.strip():
            raise ValueError("Root folder name cannot be empty")
        self.root_folder_name = self.root_folder_name.strip()
        
        # Ensure excluded_folders is not None
        if self.excluded_folders is None:
            self.excluded_folders = []
    
    def is_team_included(self, team_uid: str) -> bool:
        """Check if a team should be included based on configuration."""
        if self.included_teams is None:
            return True  # Include all teams if no filter specified
        return team_uid in self.included_teams
    
    def is_folder_included(self, folder_uid: str) -> bool:
        """Check if a folder should be included based on configuration."""
        if folder_uid in self.excluded_folders:
            return False
        if self.included_folders is None:
            return True  # Include all folders if no filter specified
        return folder_uid in self.included_folders

@dataclass
class VaultData:
    """Immutable vault data snapshot."""
    teams_by_uid: Dict[str, Team] = field(default_factory=dict)
    records_by_uid: Dict[str, Record] = field(default_factory=dict)
    folders_by_uid: Dict[str, Folder] = field(default_factory=dict)
    
    def get_team_by_uid(self, uid: str) -> Optional[Team]:
        """Safely get team by UID."""
        return self.teams_by_uid.get(uid)
    
    def get_record_by_uid(self, uid: str) -> Optional[Record]:
        """Safely get record by UID."""
        return self.records_by_uid.get(uid)
    
    def get_folder_by_uid(self, uid: str) -> Optional[Folder]:
        """Safely get folder by UID."""
        return self.folders_by_uid.get(uid)
    
    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Find team by name."""
        for team in self.teams_by_uid.values():
            if team.name == name:
                return team
        return None

@dataclass
class CSVRow:
    """Atomic CSV row model with validation."""
    record_uid: str
    title: str
    folder_path: str
    team_permissions: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate required fields
        if not self.record_uid or not self.record_uid.strip():
            raise ValueError("record_uid is required")
        if not self.title or not self.title.strip():
            raise ValueError("title is required")
        
        # Clean up data
        self.record_uid = self.record_uid.strip()
        self.title = self.title.strip()
        self.folder_path = self.folder_path.strip()
        
        # Clean team permissions (remove empty values)
        self.team_permissions = {
            team: perm.strip() for team, perm in self.team_permissions.items()
            if perm and perm.strip()
        }
    
    def get_permissions(self, vault_data: VaultData) -> List[Permission]:
        """Convert row to Permission objects."""
        permissions: List[Permission] = []
        record = Record.create(self.record_uid, self.title, self.folder_path)
        
        for team_name, perm_value in self.team_permissions.items():
            team = vault_data.get_team_by_name(team_name)
            if team:
                try:
                    permission = Permission.create(team, record, perm_value)
                    permissions.append(permission)
                except ValueError as e:
                    # Log invalid permission but continue
                    print(f"Warning: Invalid permission '{perm_value}' for team '{team_name}': {e}")
        
        return permissions

@dataclass
class CSVTemplate:
    """CSV template model."""
    headers: List[str] = field(default_factory=list)
    rows: List[CSVRow] = field(default_factory=list)
    
    def generate_headers(self, teams: List[Team]) -> List[str]:
        """Generate CSV headers according to design specification."""
        headers = ['record_uid', 'title', 'folder_path']
        headers.extend([team.name for team in teams])
        return headers
    
    def add_row(self, row: CSVRow) -> None:
        """Add a row to the template."""
        self.rows.append(row)
    
    def to_csv_content(self, teams: List[Team]) -> str:
        """Generate CSV content string."""
        headers = self.generate_headers(teams)
        lines = [','.join(headers)]
        
        for row in self.rows:
            line_parts = [row.record_uid, row.title, row.folder_path]
            for team in teams:
                perm_value = row.team_permissions.get(team.name, '')
                line_parts.append(perm_value)
            lines.append(','.join(line_parts))
        
        return '\n'.join(lines)

# Value objects for results
@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation result."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str):
        """Add an error (creates new instance for immutability)."""
        # Since this is frozen, we need to handle this differently
        # This method should not be used on frozen instances
        raise NotImplementedError("Use ValidationResultBuilder for mutable operations")
    
    def add_warning(self, warning: str):
        """Add a warning (creates new instance for immutability)."""
        raise NotImplementedError("Use ValidationResultBuilder for mutable operations")

@dataclass
class ValidationResultBuilder:
    """Mutable builder for ValidationResult."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> 'ValidationResultBuilder':
        """Add an error."""
        self.errors.append(error)
        return self
    
    def add_warning(self, warning: str) -> 'ValidationResultBuilder':
        """Add a warning."""
        self.warnings.append(warning)
        return self
    
    def set_metadata(self, key: str, value: Any) -> 'ValidationResultBuilder':
        """Set metadata."""
        self.metadata[key] = value
        return self
    
    def build(self) -> ValidationResult:
        """Build the final ValidationResult."""
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            metadata=self.metadata.copy()
        )

@dataclass(frozen=True)
class OperationResult:
    """Immutable operation result."""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def success_result(cls, message: str, data: Any = None) -> 'OperationResult':
        """Create a successful result."""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_result(cls, message: str, errors: Optional[List[str]] = None) -> 'OperationResult':
        """Create an error result."""
        return cls(success=False, message=message, errors=errors or [])
    
    @classmethod
    def warning_result(cls, message: str, warnings: Optional[List[str]] = None, data: Any = None) -> 'OperationResult':
        """Create a result with warnings."""
        return cls(success=True, message=message, data=data, warnings=warnings or []) 