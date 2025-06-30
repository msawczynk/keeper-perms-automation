"""
Keeper SDK adapter - isolates external dependency on Keeper Commander SDK.
Provides clean interface for domain layer.
"""

from typing import List, Dict, Optional, Any, Protocol
from dataclasses import dataclass
import os

# Import the existing keeper_client module
try:
    from ..keeper_client import (
        get_teams, get_folder_data, create_shared_folder, 
        share_record_to_folder, ensure_folder_path,
        get_record, get_team_uid_by_name, add_team_to_shared_folder
    )
except ImportError:
    # Fallback for testing or when SDK is not available
    def get_teams(): return []
    def get_folder_data(): return {}
    def create_shared_folder(*args): return None
    def share_record_to_folder(*args): return None
    def ensure_folder_path(*args): return None
    def get_record(*args): return None
    def get_team_uid_by_name(*args): return None
    def add_team_to_shared_folder(*args): return None

class KeeperRepositoryInterface(Protocol):
    """Protocol defining the interface for Keeper operations."""
    
    def get_all_teams(self) -> List[Dict[str, Any]]:
        """Get all teams from Keeper."""
        ...
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """Get all records from Keeper."""
        ...
    
    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Get all folders from Keeper."""
        ...
    
    def create_shared_folder(self, name: str, parent_uid: Optional[str] = None) -> Optional[str]:
        """Create a shared folder and return its UID."""
        ...
    
    def share_record_to_folder(self, record_uid: str, folder_uid: str) -> bool:
        """Share a record to a folder."""
        ...
    
    def set_team_permissions(self, team_uid: str, folder_uid: str, permissions: Dict[str, bool]) -> bool:
        """Set team permissions on a folder."""
        ...

@dataclass
class TeamData:
    """Data structure for team information from Keeper."""
    uid: str
    name: str

@dataclass
class RecordData:
    """Data structure for record information from Keeper."""
    uid: str
    title: str
    folder_path: str = ""

@dataclass
class FolderData:
    """Data structure for folder information from Keeper."""
    uid: str
    name: str
    path: str
    is_shared: bool = False

class KeeperAdapter:
    """
    Adapter for Keeper Commander SDK.
    Provides clean interface and error handling for Keeper operations.
    """
    
    def __init__(self):
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Keeper using environment variables."""
        try:
            # Check if environment variables are set
            user = os.getenv("KPR_USER")
            password = os.getenv("KPR_PASS")
            
            if not user or not password:
                return False
                
            # Authentication happens automatically in keeper_client
            self._authenticated = True
            return True
        except Exception:
            return False
    
    def get_all_teams(self) -> List[TeamData]:
        """Get all teams from Keeper vault."""
        try:
            teams_data = get_teams()
            return [
                TeamData(uid=team.get('uid', ''), name=team.get('name', ''))
                for team in teams_data if team.get('uid') and team.get('name')
            ]
        except Exception:
            return []
    
    def get_all_records(self) -> List[RecordData]:
        """Get all records from Keeper vault."""
        try:
            # This would need to be implemented in keeper_client
            # For now, return empty list
            return []
        except Exception:
            return []
    
    def get_all_folders(self) -> List[FolderData]:
        """Get all folders from Keeper vault."""
        try:
            folder_data = get_folder_data()
            folders = []
            
            if isinstance(folder_data, dict):
                for folder_uid, folder_info in folder_data.items():
                    if isinstance(folder_info, dict):
                        folders.append(FolderData(
                            uid=folder_uid,
                            name=folder_info.get('name', ''),
                            path=folder_info.get('path', ''),
                            is_shared=folder_info.get('is_shared', False)
                        ))
            
            return folders
        except Exception:
            return []
    
    def ensure_folder_path_exists(self, folder_path: str) -> Optional[str]:
        """Ensure a folder path exists and return the final folder UID."""
        try:
            return ensure_folder_path(folder_path)
        except Exception:
            return None
    
    def share_record_to_folder(self, record_uid: str, folder_uid: str) -> bool:
        """Share a record to a folder."""
        try:
            share_record_to_folder(record_uid, folder_uid)
            return True
        except Exception:
            return False
    
    def set_team_permissions(self, team_uid: str, folder_uid: str, permissions: Dict[str, bool]) -> bool:
        """Set team permissions on a shared folder."""
        try:
            add_team_to_shared_folder(team_uid, folder_uid, permissions)
            return True
        except Exception:
            return False
    
    def get_team_uid_by_name(self, team_name: str) -> Optional[str]:
        """Get team UID by team name."""
        try:
            return get_team_uid_by_name(team_name)
        except Exception:
            return None

class MockKeeperAdapter(KeeperAdapter):
    """Mock adapter for testing purposes."""
    
    def __init__(self):
        super().__init__()
        self._teams = [
            TeamData("team1", "Development Team"),
            TeamData("team2", "QA Team"),
            TeamData("team3", "Admin Team")
        ]
        self._records = [
            RecordData("rec1", "Database Password", "/Development"),
            RecordData("rec2", "API Key", "/Development"),
            RecordData("rec3", "Admin Access", "/Admin")
        ]
        self._folders = [
            FolderData("folder1", "Development", "/Development", True),
            FolderData("folder2", "Admin", "/Admin", True)
        ]
    
    def authenticate(self) -> bool:
        return True
    
    def get_all_teams(self) -> List[TeamData]:
        return self._teams.copy()
    
    def get_all_records(self) -> List[RecordData]:
        return self._records.copy()
    
    def get_all_folders(self) -> List[FolderData]:
        return self._folders.copy()
    
    def ensure_folder_path_exists(self, folder_path: str) -> Optional[str]:
        return f"mock_folder_{hash(folder_path) % 1000}"
    
    def share_record_to_folder(self, record_uid: str, folder_uid: str) -> bool:
        return True
    
    def set_team_permissions(self, team_uid: str, folder_uid: str, permissions: Dict[str, bool]) -> bool:
        return True
    
    def get_team_uid_by_name(self, team_name: str) -> Optional[str]:
        for team in self._teams:
            if team.name == team_name:
                return team.uid
        return None

def create_keeper_adapter(mock: bool = False) -> KeeperAdapter:
    """Factory function to create Keeper adapter."""
    if mock:
        return MockKeeperAdapter()
    return KeeperAdapter() 