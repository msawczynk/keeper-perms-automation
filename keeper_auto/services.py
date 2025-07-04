"""
Services for Keeper Automation.
These services contain the core business logic and interact with the Keeper vault.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Optional, Set

from .models import (
    VaultData, ValidationResult, ConfigRecord
)
from .keeper_client import (
    get_teams, get_folder_data, get_record,
    ensure_team_folder_path, share_record_to_folder, add_team_to_shared_folder,
    get_team_uid_by_name
)
from .logger import StructuredLogger

# NOTE: We hard-code the allowed simple permission tokens per design.
_ALLOWED_PERMISSION_TOKENS: Set[str] = {"ro", "rw", "rws", "mgr", "admin"}


class ConfigService:
    """Service for configuration management."""

    def load_config(self, record_uid: Optional[str] = None) -> Optional[ConfigRecord]:
        """Fetches the configuration record from the vault and parses it into the ConfigRecord model."""
        try:
            if record_uid:
                # Use provided record UID
                config_record_uid = record_uid
            else:
                # Find by title
                config_record_uid = self._find_config_record_by_title()
            
            if not config_record_uid:
                # Return default config if not found
                return ConfigRecord()

            record = get_record(config_record_uid)
            if record and hasattr(record, 'data') and record.data:
                for field in record.data:
                    if field.type == 'json':
                        try:
                            json_config = json.loads(str(field.value))
                            return ConfigRecord(
                                root_folder_name=json_config.get('root_folder_name', '[Perms]'),
                                included_teams=json_config.get('included_teams'),
                                included_folders=json_config.get('included_folders'),
                                excluded_folders=json_config.get('excluded_folders', [])
                            )
                        except json.JSONDecodeError:
                            return None  # Failed to parse
            return ConfigRecord()  # Return default if empty or no JSON
        except Exception:
            return None

    def save_config(self, config: ConfigRecord) -> bool:
        """Saves the configuration record to the vault."""
        # Note: This is a placeholder implementation.
        # A full implementation would require updating a record in the vault.
        return True

    def _find_config_record_by_title(self, title: str = "Perms-Config") -> Optional[str]:
        """Find a configuration record by title."""
        try:
            from keeper_auto.keeper_client import get_records
            records = get_records()
            for record in records:
                if record.get('title') == title:
                    return record.get('uid')
        except Exception:
            return None
        return None


class VaultService:
    """Service for vault operations."""

    def __init__(self, config: ConfigRecord):
        self.config = config
        self.vault_data = VaultData()

    def load_vault_data(self, force_reload: bool = False) -> Optional[VaultData]:
        """Load vault data from Keeper with optional filtering based on configuration."""
        if self.vault_data.is_loaded() and not force_reload:
            return self.vault_data

        try:
            from keepercommander.subfolder import find_folders  # type: ignore
            
            self.vault_data.clear()
            folder_data = get_folder_data()
            
            # Load teams
            teams_list = get_teams()
            for team_info in teams_list:
                team_uid = team_info.get('team_uid')
                team_name = team_info.get('team_name')
                if team_uid and team_name:
                    if self.config.included_teams and team_uid not in self.config.included_teams:
                        continue
                    self.vault_data.add_team(team_uid, team_name)
            
            # Load folders first so we can build paths
            for folder_info in folder_data.get('folders', []):
                folder_uid = folder_info.get('uid')
                folder_name = folder_info.get('name')
                if folder_uid and folder_name:
                    self.vault_data.add_folder(folder_uid, folder_name, folder_info.get('parent_uid'))

            # Load records with proper folder paths
            for record_info in folder_data.get('records', []):
                record_uid = record_info.get('uid')
                record_title = record_info.get('title')
                if record_uid and record_title:
                    # Build folder path using find_folders
                    folder_path = self._build_folder_path_from_record(record_uid)
                    self.vault_data.add_record(record_uid, record_title, folder_path)
            
            self.vault_data.mark_loaded()
            return self.vault_data
        except Exception:
            return None

    def _build_folder_path_from_record(self, record_uid: str) -> str:
        """Build the full folder path for a record using find_folders."""
        try:
            from keeper_auto.keeper_client import get_client  # type: ignore
            from keepercommander.subfolder import find_folders  # type: ignore
            
            sdk = get_client()
            folder_uids = list(find_folders(sdk, record_uid))
            
            if not folder_uids:
                return ""
            
            # Use the first folder (records can be in multiple folders)
            folder_uid = folder_uids[0]
            return self._build_folder_path(folder_uid)
        except Exception:
            return ""

    def _build_folder_path(self, folder_uid: Optional[str]) -> str:
        """Build the full folder path for a given folder UID."""
        if not folder_uid:
            return ""
        path_parts: List[str] = []
        current_uid = folder_uid
        while current_uid:
            folder = self.vault_data.find_folder_by_uid(current_uid)
            if folder:
                path_parts.insert(0, folder.name)
                current_uid = folder.parent_uid
            else:
                break
        return "/" + "/".join(path_parts) if path_parts else ""


class TemplateService:
    """Service for template operations."""

    def __init__(self, vault_data: VaultData, config: ConfigRecord):
        self.vault_data = vault_data
        self.config = config

    def generate_template(self, output_path: Path) -> None:
        """Generate a CSV template from filtered vault data."""
        if not self.vault_data.teams_by_uid:
            raise ValueError("No teams found in vault data.")
        
        teams = list(self.vault_data.teams_by_uid.values())
        records = list(self.vault_data.records_by_uid.values())
        
        # Create headers with format "TeamName (uid)" instead of just team name
        team_headers = []
        for team in teams:
            # Format: "TeamName (uid)" but only show the actual name part
            team_name = team.name
            if team_name.startswith('Team '):
                # If it's still a placeholder, use the UID
                team_headers.append(f"{team_name}")
            else:
                # Use actual team name with UID for clarity
                team_headers.append(f"{team_name} ({team.uid})")
        
        headers = ['record_uid', 'title', 'folder_path'] + team_headers
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in records:
                row = [str(rec.uid), rec.title, rec.folder_path]
                row.extend(['' for _ in teams])
                writer.writerow(row)


class ProvisioningService:
    """Service for provisioning operations."""

    def __init__(self, vault_data: VaultData, config: ConfigRecord, logger: StructuredLogger):
        self.vault_data = vault_data
        self.config = config
        self.logger = logger

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_csv_rows(self, csv_path: Path) -> List[Dict[str, str]]:
        """Return list of row dicts (whitespace-stripped)."""
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows: List[Dict[str, str]] = []
            for raw in reader:
                cleaned = {k.strip(): (v or '').strip() for k, v in raw.items()}
                rows.append(cleaned)
            return rows

    def _permission_token_to_flags(self, token: str) -> Dict[str, bool]:
        """Convert simple token (ro/rw/…) to Keeper flag dict."""
        token = token.lower().strip()
        mapping = {
            "ro": {"can_edit": False, "can_share": False, "manage_records": False, "manage_users": False},
            "rw": {"can_edit": True,  "can_share": False, "manage_records": False, "manage_users": False},
            "rws": {"can_edit": True,  "can_share": True,  "manage_records": False, "manage_users": False},
            "mgr": {"can_edit": True,  "can_share": True,  "manage_records": True,  "manage_users": False},
            "admin": {"can_edit": True,  "can_share": True,  "manage_records": True,  "manage_users": True},
        }
        return mapping.get(token, {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dry_run(self, csv_path: Path) -> List[str]:
        """Return a human-readable list of operations that *would* be executed."""
        operations: List[str] = []
        for row in self._iter_csv_rows(csv_path):
            record_uid = row['record_uid']
            folder_path = row['folder_path'].lstrip('/')
            
            # Process each team that has permissions on this record
            for col, token in row.items():
                if col in ('record_uid', 'title', 'folder_path'):
                    continue
                token = token.lower().strip()
                if not token:
                    continue
                
                # Extract team name from column header
                team_name = col
                if ' (' in team_name and team_name.endswith(')'):
                    team_name = team_name.split(' (')[0]
                
                team_folder_path = f"{self.config.root_folder_name}/{team_name}/{folder_path}"
                operations.append(f"Ensure team folder path {team_folder_path}")
                operations.append(f"Link record {record_uid} → {team_folder_path}")
                operations.append(f"Add team '{team_name}' with '{token}' permissions to their shared folder")
        return operations

    def apply_changes(self, csv_path: Path, max_records: int, force: bool) -> bool:
        """Apply changes according to CSV using per-team folder structure. Returns True on full success."""

        rows = self._iter_csv_rows(csv_path)
        if not force and len(rows) > max_records:
            self.logger.error("max_records_exceeded", {"record_count": len(rows), "max_records": max_records})
            return False

        success = True

        for row in rows:
            record_uid = row['record_uid']
            folder_path = row['folder_path'].lstrip('/')  # Remove leading slash
            
            # Process each team that has permissions on this record
            for col, token in row.items():
                if col in ('record_uid', 'title', 'folder_path'):
                    continue
                token = token.lower().strip()
                if not token:
                    continue  # blank → no access

                # Extract team name from column header (remove UID part if present)
                team_name = col
                if ' (' in team_name and team_name.endswith(')'):
                    team_name = team_name.split(' (')[0]  # Remove UID part

                # 1. Create team-specific folder structure: [Perms]/TeamName/folder_path
                team_folder_uid = ensure_team_folder_path(team_name, folder_path, self.config.root_folder_name)
                if not team_folder_uid:
                    self.logger.error("team_folder_creation_failed", {"team": team_name, "path": folder_path})
                    success = False
                    continue

                # 2. Share record to the team's folder
                try:
                    share_record_to_folder(record_uid, team_folder_uid)
                    self.logger.info("record_shared", {"record_uid": record_uid, "team": team_name, "folder_uid": team_folder_uid})
                except Exception as e:
                    self.logger.error("share_record_failed", {"record_uid": record_uid, "team": team_name, "folder_uid": team_folder_uid, "error": str(e)})
                    success = False
                    continue

                # 3. Add team to their shared folder (the team folder itself, not the subfolder)
                # We need to find the team's shared folder UID (parent of the final folder)
                team_shared_folder_uid = self._find_team_shared_folder(team_name)
                if not team_shared_folder_uid:
                    self.logger.error("team_shared_folder_not_found", {"team": team_name})
                    success = False
                    continue

                team_uid = get_team_uid_by_name(col)  # Use original column name for team lookup
                if not team_uid:
                    self.logger.warning("unknown_team", {"team_name": col})
                    continue

                flags = self._permission_token_to_flags(token)
                if not flags:
                    self.logger.error("invalid_token", {"token": token, "team": col})
                    success = False
                    continue

                try:
                    add_team_to_shared_folder(team_uid, team_shared_folder_uid, flags)
                    self.logger.info("team_permissions_added", {"team_uid": team_uid, "team": team_name, "folder_uid": team_shared_folder_uid, "permissions": token})
                except Exception as e:
                    self.logger.error("add_team_failed", {"team_uid": team_uid, "team": team_name, "folder_uid": team_shared_folder_uid, "error": str(e)})
                    success = False

        return success

    def _find_team_shared_folder(self, team_name: str) -> Optional[str]:
        """Find the shared folder UID for a team under the root [Perms] folder."""
        try:
            from .keeper_client import find_folder_by_name
            
            # Find root folder
            root_folder = find_folder_by_name(self.config.root_folder_name, parent_uid=None)
            if not root_folder:
                return None
            
            root_folder_uid = root_folder.get('uid')
            
            # Find team folder under root
            team_folder = find_folder_by_name(team_name, parent_uid=root_folder_uid)
            if not team_folder:
                return None
            
            return team_folder.get('uid')
        except Exception:
            return None


class ValidationService:
    """Service for validation operations."""

    def validate_csv(self, csv_path: Path, max_records: int) -> ValidationResult:
        """Validate a CSV file against design rules."""

        result = ValidationResult(is_valid=True)

        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames:
                    result.add_error("CSV file is empty or missing headers.")
                    return result

                # Normalize headers (case-insensitive, strip)
                headers = [h.strip() for h in reader.fieldnames]

                required_columns = {"record_uid", "title", "folder_path"}
                missing_required = required_columns - {h.lower() for h in headers}
                if missing_required:
                    result.add_error(f"Missing required column(s): {', '.join(sorted(missing_required))}.")

                seen_record_uids: Set[str] = set()
                row_idx = 1  # start after header

                for row in reader:
                    row_idx += 1
                    uid_raw = (row.get('record_uid') or '').strip()
                    if not uid_raw:
                        result.add_error(f"Row {row_idx}: 'record_uid' is blank.")
                    else:
                        if uid_raw in seen_record_uids:
                            result.add_error(f"Duplicate record_uid '{uid_raw}' at row {row_idx}.")
                        seen_record_uids.add(uid_raw)

                    # Iterate team permission cells
                    for col, val in row.items():
                        if col in ('record_uid', 'title', 'folder_path'):
                            continue
                        token = (val or '').strip().lower()
                        if token and token not in _ALLOWED_PERMISSION_TOKENS:
                            result.add_error(f"Row {row_idx}: invalid permission token '{val}' in column '{col}'.")

                row_count = row_idx - 1
                result.metadata['row_count'] = row_count

                if row_count > max_records:
                    result.add_warning(f"CSV has {row_count} records, exceeding max-records limit of {max_records}.")

        except Exception as e:
            result.add_error(f"Failed to read or validate CSV: {e}")

        return result 