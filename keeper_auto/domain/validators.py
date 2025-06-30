"""
Atomic validators for domain models.
Each validator has a single responsibility and can be composed.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import csv
import re

from .models import (
    ValidationResultBuilder, ValidationResult, CSVRow, VaultData, 
    PermissionLevel, EntityUID
)

class BaseValidator:
    """Base validator interface."""
    
    def validate(self, *args: Any, **kwargs: Any) -> ValidationResult:
        """Validate and return result."""
        raise NotImplementedError

class CSVStructureValidator(BaseValidator):
    """Validates CSV file structure and format."""
    
    REQUIRED_HEADERS = ['record_uid', 'title', 'folder_path']
    
    def validate(self, csv_path: Path, vault_data: Optional[VaultData] = None) -> ValidationResult:
        """Validate CSV file structure."""
        builder = ValidationResultBuilder()
        
        if not csv_path.exists():
            return builder.add_error(f"CSV file not found: {csv_path}").build()
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
                rows = list(reader)
            
            # Validate headers
            self._validate_headers(headers, builder)
            
            # Validate row count
            self._validate_row_count(len(rows), builder)
            
            # Set metadata
            team_columns = [h for h in headers if h.lower().strip() not in 
                          [h.lower() for h in self.REQUIRED_HEADERS]]
            
            builder.set_metadata('headers', len(headers))
            builder.set_metadata('rows', len(rows))
            builder.set_metadata('team_columns', len(team_columns))
            
        except Exception as e:
            builder.add_error(f"Failed to read CSV file: {e}")
        
        return builder.build()
    
    def _validate_headers(self, headers: List[str], builder: ValidationResultBuilder) -> None:
        """Validate CSV headers."""
        if not headers:
            builder.add_error("CSV file has no headers")
            return
        
        # Case-insensitive header checking
        headers_lower = [h.lower().strip() for h in headers]
        missing_headers = [h for h in self.REQUIRED_HEADERS if h not in headers_lower]
        
        if missing_headers:
            builder.add_error(f"Missing required headers: {missing_headers}")
    
    def _validate_row_count(self, row_count: int, builder: ValidationResultBuilder) -> None:
        """Validate row count."""
        if row_count == 0:
            builder.add_warning("CSV file is empty")
        elif row_count > 1000:
            builder.add_warning(f"Large CSV file ({row_count} rows)")

class CSVContentValidator(BaseValidator):
    """Validates CSV content and data integrity."""
    
    def validate(self, csv_path: Path, vault_data: Optional[VaultData] = None) -> ValidationResult:
        """Validate CSV content."""
        builder = ValidationResultBuilder()
        
        try:
            rows = self._parse_csv_rows(csv_path)
            
            # Validate for duplicates
            self._validate_duplicates(rows, builder)
            
            # Validate individual rows
            self._validate_rows(rows, builder, vault_data)
            
            builder.set_metadata('total_rows', len(rows))
            
        except Exception as e:
            builder.add_error(f"CSV content validation failed: {e}")
        
        return builder.build()
    
    def _parse_csv_rows(self, csv_path: Path) -> List[Dict[str, str]]:
        """Parse CSV into row dictionaries."""
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def _validate_duplicates(self, rows: List[Dict[str, str]], builder: ValidationResultBuilder) -> None:
        """Validate for duplicate record_uid values."""
        record_uids: List[str] = []
        duplicate_uids: List[str] = []
        
        for i, row in enumerate(rows, 2):  # Start at 2 for header
            record_uid = row.get('record_uid', '').strip()
            if not record_uid:
                builder.add_error(f"Row {i}: Missing record_uid")
                continue
            
            if record_uid in record_uids:
                if record_uid not in duplicate_uids:
                    duplicate_uids.append(record_uid)
                builder.add_error(f"Row {i}: Duplicate record_uid '{record_uid}'")
            else:
                record_uids.append(record_uid)
        
        if duplicate_uids:
            builder.add_error(f"Found {len(duplicate_uids)} duplicate record_uid values: {duplicate_uids}")
        
        builder.set_metadata('duplicate_uids', len(duplicate_uids))
    
    def _validate_rows(self, rows: List[Dict[str, str]], builder: ValidationResultBuilder, vault_data: Optional[VaultData] = None) -> None:
        """Validate individual rows."""
        required_fields = ['record_uid', 'title', 'folder_path']
        
        for i, row in enumerate(rows, 2):  # Start at 2 for header
            # Validate required fields
            for field in required_fields:
                if not row.get(field, '').strip():
                    builder.add_error(f"Row {i}: Missing {field}")
            
            # Validate permission values
            self._validate_permissions(row, i, builder)
            
            # Validate against vault data if provided
            if vault_data:
                self._validate_against_vault(row, i, builder, vault_data)
    
    def _validate_permissions(self, row: Dict[str, str], row_num: int, builder: ValidationResultBuilder) -> None:
        """Validate permission values in a row."""
        required_fields = {'record_uid', 'title', 'folder_path'}
        
        for key, value in row.items():
            if key.lower().strip() not in required_fields and value.strip():
                perm_value = value.strip().lower()
                if not PermissionLevel.from_string(perm_value):
                    valid_values = [level.value for level in PermissionLevel]
                    builder.add_error(
                        f"Row {row_num}: Invalid permission value '{value}' for '{key}'. "
                        f"Valid values: {valid_values}"
                    )
    
    def _validate_against_vault(self, row: Dict[str, str], row_num: int, builder: ValidationResultBuilder, vault_data: VaultData) -> None:
        """Validate row against vault data for drift detection."""
        record_uid = row.get('record_uid', '').strip()
        if not record_uid:
            return
        
        record = vault_data.get_record_by_uid(record_uid)
        if not record:
            builder.add_error(f"Row {row_num}: Record UID '{record_uid}' not found in vault")
            return
        
        # Check for title mismatch
        csv_title = row.get('title', '').strip()
        if csv_title != record.title:
            builder.add_warning(
                f"Row {row_num}: Title mismatch for {record_uid} "
                f"('{csv_title}' vs '{record.title}')"
            )
        
        # Check for folder path mismatch
        csv_folder_path = row.get('folder_path', '').strip()
        if csv_folder_path != record.folder_path:
            builder.add_warning(
                f"Row {row_num}: Folder path mismatch for {record_uid} "
                f"('{csv_folder_path}' vs '{record.folder_path}')"
            )

class TeamValidator(BaseValidator):
    """Validates team columns against vault teams."""
    
    def validate(self, csv_path: Path, vault_data: VaultData) -> ValidationResult:
        """Validate team columns."""
        builder = ValidationResultBuilder()
        
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
            
            required_fields = {'record_uid', 'title', 'folder_path'}
            team_columns = [h for h in headers if h.lower().strip() not in required_fields]
            
            if not team_columns:
                builder.add_warning("No team permission columns found")
                return builder.build()
            
            # Validate team columns against vault teams
            vault_team_names = {team.name for team in vault_data.teams_by_uid.values()}
            unknown_teams = [team for team in team_columns if team not in vault_team_names]
            
            if unknown_teams:
                builder.add_error(f"Unknown teams in CSV headers: {unknown_teams}")
            
            builder.set_metadata('team_columns', team_columns)
            builder.set_metadata('unknown_teams', unknown_teams)
            
        except Exception as e:
            builder.add_error(f"Team validation failed: {e}")
        
        return builder.build()

class ConfigValidator(BaseValidator):
    """Validates configuration records."""
    
    def validate(self, config_data: Dict[str, Any], vault_data: Optional[VaultData] = None) -> ValidationResult:
        """Validate configuration data."""
        builder = ValidationResultBuilder()
        
        # Validate root_folder_name
        root_folder = config_data.get('root_folder_name', '')
        if not root_folder or not root_folder.strip():
            builder.add_error("root_folder_name cannot be empty")
        
        # Validate team UIDs format
        included_teams = config_data.get('included_teams')
        if included_teams is not None:
            self._validate_uid_list(included_teams, 'included_teams', builder)
        
        # Validate folder UIDs format
        included_folders = config_data.get('included_folders')
        if included_folders is not None:
            self._validate_uid_list(included_folders, 'included_folders', builder)
        
        # Validate excluded folders
        excluded_folders = config_data.get('excluded_folders', [])
        if excluded_folders:
            self._validate_uid_list(excluded_folders, 'excluded_folders', builder)
        
        return builder.build()
    
    def _validate_uid_list(self, uid_list: List[str], field_name: str, builder: ValidationResultBuilder) -> None:
        """Validate a list of UIDs."""
        if not isinstance(uid_list, list):
            builder.add_error(f"{field_name} must be a list")
            return
        
        for i, uid in enumerate(uid_list):
            try:
                EntityUID(uid)  # This will validate the UID format
            except ValueError as e:
                builder.add_error(f"{field_name}[{i}]: {e}")

class CompositeValidator(BaseValidator):
    """Composes multiple validators for comprehensive validation."""
    
    def __init__(self, validators: List[BaseValidator]):
        self.validators = validators
    
    def validate(self, *args: Any, **kwargs: Any) -> ValidationResult:
        """Run all validators and combine results."""
        all_errors: List[str] = []
        all_warnings: List[str] = []
        combined_metadata: Dict[str, Any] = {}
        
        for validator in self.validators:
            result = validator.validate(*args, **kwargs)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            combined_metadata.update(result.metadata)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            metadata=combined_metadata
        ) 