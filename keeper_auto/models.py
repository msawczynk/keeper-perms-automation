"""
Atomic Models for Keeper Automation
Clean, reusable data structures
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PermissionLevel(Enum):
    """Permission levels for teams."""
    NONE = "none"
    VIEW = "view"
    EDIT = "edit"
    SHARE = "share"
    MANAGE_RECORDS = "manage_records"
    MANAGE_USERS = "manage_users"


@dataclass
class ConfigRecord:
    """Configuration record for the provisioning system."""
    root_folder_name: str = "[Perms]"
    included_teams: Optional[List[str]] = None  # List of team UIDs, None means all
    included_folders: Optional[List[str]] = None  # List of folder UIDs, None means all
    excluded_folders: List[str] = field(default_factory=list)  # Always includes the root management folder UID


@dataclass
class VaultFolder:
    """Represents a folder in the vault."""
    uid: str
    name: str
    parent_uid: Optional[str] = None
    subfolders: List['VaultFolder'] = field(default_factory=list)
    records: List['Record'] = field(default_factory=list)
    
    def __str__(self) -> str:
        return self.name
    
    def __hash__(self) -> int:
        return hash(self.uid)


@dataclass
class Record:
    """Atomic record model."""
    uid: str
    title: str
    folder_path: str = ""
    
    def __str__(self) -> str:
        return self.title
    
    def __hash__(self) -> int:
        return hash(self.uid)


@dataclass
class Team:
    """Atomic team model."""
    uid: str
    name: str
    
    def __str__(self) -> str:
        return self.name
    
    def __hash__(self) -> int:
        return hash(self.uid)


@dataclass
class Permission:
    """Atomic permission model."""
    team: Team
    record: Record
    can_edit: bool = False
    can_share: bool = False
    manage_records: bool = False
    manage_users: bool = False
    
    @classmethod
    def from_permission_value(cls, team: Team, record: Record, permission_value: str) -> 'Permission':
        """
        Create Permission from simple permission value according to design mapping:
        - ro (read-only): all permissions false
        - rw (read/write): can_edit=true, others false  
        - rws (read/write/share): can_edit=true, can_share=true, others false
        - mgr (manage records): can_edit=true, can_share=true, manage_records=true, manage_users=false
        - admin (manage users): all permissions true
        """
        perm_value = permission_value.strip().lower()
        
        if perm_value == "ro":
            return cls(team=team, record=record, can_edit=False, can_share=False, manage_records=False, manage_users=False)
        elif perm_value == "rw":
            return cls(team=team, record=record, can_edit=True, can_share=False, manage_records=False, manage_users=False)
        elif perm_value == "rws":
            return cls(team=team, record=record, can_edit=True, can_share=True, manage_records=False, manage_users=False)
        elif perm_value == "mgr":
            return cls(team=team, record=record, can_edit=True, can_share=True, manage_records=True, manage_users=False)
        elif perm_value == "admin":
            return cls(team=team, record=record, can_edit=True, can_share=True, manage_records=True, manage_users=True)
        else:
            # Empty or invalid - no permissions
            return cls(team=team, record=record, can_edit=False, can_share=False, manage_records=False, manage_users=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'team_uid': self.team.uid,
            'team_name': self.team.name,
            'record_uid': self.record.uid,
            'record_title': self.record.title,
            'can_edit': self.can_edit,
            'can_share': self.can_share,
            'manage_records': self.manage_records,
            'manage_users': self.manage_users
        }
    
    @classmethod
    def from_csv_row(cls, teams: Dict[str, Team], records: Dict[str, Record], 
                     record_uid: str, row: Dict[str, str]) -> List['Permission']:
        """Create permissions from CSV row."""
        permissions: List[Permission] = []
        
        if record_uid not in records:
            return permissions
            
        record = records[record_uid]
        
        # Parse team permissions from row
        for key, value in row.items():
            if '_can_' in key or '_manage_' in key:
                parts = key.split('_', 2)
                if len(parts) >= 3:
                    team_name = parts[0]
                    perm_type = f"{parts[1]}_{parts[2]}"
                    
                    # Find team by name
                    team = None
                    for t in teams.values():
                        if t.name == team_name:
                            team = t
                            break
                    
                    if team and value.strip().lower() in ['true', 'false']:
                        # Find existing permission or create new one
                        existing = None
                        for p in permissions:
                            if p.team.uid == team.uid and p.record.uid == record.uid:
                                existing = p
                                break
                        
                        if not existing:
                            existing = Permission(team=team, record=record)
                            permissions.append(existing)
                        
                        # Set the specific permission
                        perm_value = value.strip().lower() == 'true'
                        if perm_type == 'can_edit':
                            existing.can_edit = perm_value
                        elif perm_type == 'can_share':
                            existing.can_share = perm_value
                        elif perm_type == 'manage_records':
                            existing.manage_records = perm_value
                        elif perm_type == 'manage_users':
                            existing.manage_users = perm_value
        
        return permissions


@dataclass
class ValidationResult:
    """Result of validation operations."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)
    
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.errors) > 0 or len(self.warnings) > 0


@dataclass
class OperationResult:
    """Result of operations."""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CSVTemplate:
    """CSV template structure."""
    headers: List[str] = field(default_factory=list)
    teams: List[Team] = field(default_factory=list)
    records: List[Record] = field(default_factory=list)
    
    def generate_headers(self) -> List[str]:
        """
        Generate CSV headers according to design specification:
        - record_uid (required)
        - title (required) 
        - folder_path (required)
        - One column per team name (for simple permission values: ro, rw, rws, mgr, admin)
        """
        headers = ['record_uid', 'title', 'folder_path']
        
        # Add team columns - simple team names, not complex permission fields
        for team in self.teams:
            headers.append(team.name)
        
        return headers
    
    def generate_row(self, record: Record) -> Dict[str, str]:
        """Generate a CSV row for a record."""
        row = {
            'record_uid': record.uid,
            'title': record.title,
            'folder_path': record.folder_path
        }
        
        # Add empty permission columns for each team (to be filled by user)
        for team in self.teams:
            row[team.name] = ""  # User will fill with: ro, rw, rws, mgr, admin
        
        return row
    
    def validate_csv_structure(self, headers: List[str]) -> ValidationResult:
        """
        Validate CSV structure against design requirements.
        """
        result = ValidationResult(is_valid=True)
        
        # Check required headers
        required_headers = {'record_uid', 'title', 'folder_path'}
        header_set = set(headers)
        
        missing_headers = required_headers - header_set
        if missing_headers:
            result.add_error(f"Missing required headers: {missing_headers}")
        
        # Check for team columns
        team_columns = header_set - required_headers
        if not team_columns:
            result.add_warning("No team columns found. You'll need team columns to assign permissions.")
        
        # Validate that team names don't contain invalid characters
        for team_col in team_columns:
            if any(char in team_col for char in ['_can_', '_manage_']):
                result.add_warning(f"Team column '{team_col}' contains legacy format. Use simple team names instead.")
        
        return result


@dataclass
class VaultData:
    """Represents all relevant data loaded from the vault."""
    teams_by_uid: Dict[str, Team] = field(default_factory=dict)
    records_by_uid: Dict[str, Record] = field(default_factory=dict)
    folders_by_uid: Dict[str, VaultFolder] = field(default_factory=dict)
    
    _loaded: bool = False

    def __init__(self):
        """Initializes the VaultData object."""
        self.clear()

    def add_team(self, uid: str, name: str) -> Team:
        """Adds a team to the vault data."""
        if uid not in self.teams_by_uid:
            self.teams_by_uid[uid] = Team(uid=uid, name=name)
        return self.teams_by_uid[uid]

    def add_record(self, uid: str, title: str, folder_path: str = "") -> Record:
        """Adds a record to the vault data."""
        if uid not in self.records_by_uid:
            self.records_by_uid[uid] = Record(uid=uid, title=title, folder_path=folder_path)
        return self.records_by_uid[uid]

    def add_folder(self, uid: str, name: str, parent_uid: Optional[str] = None) -> VaultFolder:
        """Adds a folder to the vault data."""
        if uid not in self.folders_by_uid:
            folder = VaultFolder(uid=uid, name=name, parent_uid=parent_uid)
            self.folders_by_uid[uid] = folder
            
            # Link to parent
            if parent_uid and parent_uid in self.folders_by_uid:
                self.folders_by_uid[parent_uid].subfolders.append(folder)
        
        return self.folders_by_uid[uid]

    def find_folder_by_uid(self, uid: str) -> Optional[VaultFolder]:
        """Finds a folder by its UID."""
        return self.folders_by_uid.get(uid)

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Finds a team by its name."""
        for team in self.teams_by_uid.values():
            if team.name.lower() == name.lower():
                return team
        return None

    def get_team_by_uid(self, uid: str) -> Optional[Team]:
        """Gets a team by its UID."""
        return self.teams_by_uid.get(uid)

    def get_record_by_uid(self, uid: str) -> Optional[Record]:
        """Gets a record by its UID."""
        return self.records_by_uid.get(uid)

    def is_loaded(self) -> bool:
        """Checks if the data has been loaded."""
        return self._loaded

    def mark_loaded(self) -> None:
        """Marks the data as loaded."""
        self._loaded = True

    def clear(self) -> None:
        """Clears all data."""
        self.teams_by_uid.clear()
        self.records_by_uid.clear()
        self.folders_by_uid.clear()
        self._loaded = False

    def summary(self) -> Dict[str, int]:
        """Returns a summary of the loaded data."""
        return {
            "teams": len(self.teams_by_uid),
            "records": len(self.records_by_uid),
            "folders": len(self.folders_by_uid),
        } 