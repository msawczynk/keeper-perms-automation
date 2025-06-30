"""
Atomic operations for business logic.
Each operation has a single responsibility and clear interface.
"""

from typing import List, Dict, Any, Optional, Protocol
from pathlib import Path
import csv

from .models import (
    CSVRow, VaultData, Permission, Team, Record, CSVTemplate,
    OperationResult, ValidationResult
)
from .validators import CompositeValidator, CSVStructureValidator, CSVContentValidator, TeamValidator, BaseValidator

class OperationInterface(Protocol):
    """Protocol for all operations."""
    
    def execute(self, *args: Any, **kwargs: Any) -> OperationResult:
        """Execute the operation."""
        ...

class CSVParserOperation:
    """Atomic operation for parsing CSV files into domain objects."""
    
    def execute(self, csv_path: Path) -> OperationResult:
        """Parse CSV file into CSVRow objects."""
        try:
            rows: List[CSVRow] = []
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
                
                required_fields = {'record_uid', 'title', 'folder_path'}
                team_columns = [h for h in headers if h.lower().strip() not in required_fields]
                
                for row_data in reader:
                    # Extract team permissions
                    team_permissions: Dict[str, str] = {}
                    for team_col in team_columns:
                        perm_value = row_data.get(team_col, '').strip()
                        if perm_value:
                            team_permissions[team_col] = perm_value
                    
                    # Create CSVRow
                    try:
                        csv_row = CSVRow(
                            record_uid=row_data.get('record_uid', ''),
                            title=row_data.get('title', ''),
                            folder_path=row_data.get('folder_path', ''),
                            team_permissions=team_permissions
                        )
                        rows.append(csv_row)
                    except ValueError as e:
                        return OperationResult.error_result(f"Invalid row data: {e}")
            
            return OperationResult.success_result(
                f"Parsed {len(rows)} rows from CSV",
                data={'rows': rows, 'team_columns': team_columns}
            )
            
        except Exception as e:
            return OperationResult.error_result(f"Failed to parse CSV: {e}")

class ValidationOperation:
    """Atomic operation for comprehensive CSV validation."""
    
    def __init__(self, vault_data: Optional[VaultData] = None):
        self.vault_data = vault_data
    
    def execute(self, csv_path: Path, max_records: int = 5000) -> OperationResult:
        """Validate CSV file comprehensively."""
        validators: List[BaseValidator] = [
            CSVStructureValidator(),
            CSVContentValidator()
        ]
        
        if self.vault_data:
            validators.append(TeamValidator())
        
        composite_validator = CompositeValidator(validators)
        
        # Run validation
        if self.vault_data:
            result = composite_validator.validate(csv_path, self.vault_data)
        else:
            result = composite_validator.validate(csv_path)
        
        # Check max records
        row_count = result.metadata.get('rows', 0)
        if row_count > max_records:
            # Create new result with max records warning
            errors = list(result.errors)
            warnings = list(result.warnings)
            warnings.append(f"CSV file has {row_count} rows, exceeding max-records limit of {max_records}")
            
            result = ValidationResult(
                is_valid=result.is_valid,
                errors=errors,
                warnings=warnings,
                metadata=result.metadata
            )
        
        if result.is_valid:
            return OperationResult.success_result(
                "CSV validation successful",
                data={'validation_result': result}
            )
        else:
            return OperationResult.error_result(
                "CSV validation failed",
                errors=result.errors
            )

class PermissionExtractionOperation:
    """Atomic operation for extracting permissions from CSV rows."""
    
    def __init__(self, vault_data: VaultData):
        self.vault_data = vault_data
    
    def execute(self, csv_rows: List[CSVRow]) -> OperationResult:
        """Extract Permission objects from CSV rows."""
        try:
            all_permissions: List[Permission] = []
            errors: List[str] = []
            
            for i, row in enumerate(csv_rows, 1):
                try:
                    permissions = row.get_permissions(self.vault_data)
                    all_permissions.extend(permissions)
                except Exception as e:
                    errors.append(f"Row {i}: Failed to extract permissions: {e}")
            
            if errors:
                return OperationResult.warning_result(
                    f"Extracted {len(all_permissions)} permissions with some errors",
                    warnings=errors,
                    data={'permissions': all_permissions}
                )
            else:
                return OperationResult.success_result(
                    f"Extracted {len(all_permissions)} permissions",
                    data={'permissions': all_permissions}
                )
                
        except Exception as e:
            return OperationResult.error_result(f"Permission extraction failed: {e}")

class TemplateGenerationOperation:
    """Atomic operation for generating CSV templates."""
    
    def __init__(self, vault_data: VaultData):
        self.vault_data = vault_data
    
    def execute(self, output_path: Path, filter_config: Optional[Dict[str, Any]] = None) -> OperationResult:
        """Generate CSV template from vault data."""
        try:
            # Filter teams and records based on config
            teams = list(self.vault_data.teams_by_uid.values())
            records = list(self.vault_data.records_by_uid.values())
            
            if filter_config:
                teams = self._filter_teams(teams, filter_config)
                records = self._filter_records(records, filter_config)
            
            # Create template
            template = CSVTemplate()
            
            # Add rows for each record
            for record in records:
                csv_row = CSVRow(
                    record_uid=record.uid.value,
                    title=record.title,
                    folder_path=record.folder_path,
                    team_permissions={}  # Empty permissions for template
                )
                template.add_row(csv_row)
            
            # Generate CSV content
            csv_content = template.to_csv_content(teams)
            
            # Write to file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            
            return OperationResult.success_result(
                f"Template generated with {len(records)} records and {len(teams)} teams",
                data={'records_count': len(records), 'teams_count': len(teams)}
            )
            
        except Exception as e:
            return OperationResult.error_result(f"Template generation failed: {e}")
    
    def _filter_teams(self, teams: List[Team], config: Dict[str, Any]) -> List[Team]:
        """Filter teams based on configuration."""
        included_teams = config.get('included_teams')
        if included_teams is None:
            return teams
        
        return [team for team in teams if team.uid.value in included_teams]
    
    def _filter_records(self, records: List[Record], config: Dict[str, Any]) -> List[Record]:
        """Filter records based on configuration."""
        included_folders = config.get('included_folders')
        excluded_folders = config.get('excluded_folders', [])
        
        filtered_records: List[Record] = []
        for record in records:
            # Skip excluded folders
            if record.folder_path in excluded_folders:
                continue
            
            # Include only specified folders if filter exists
            if included_folders is not None:
                if record.folder_path not in included_folders:
                    continue
            
            filtered_records.append(record)
        
        return filtered_records

class DryRunOperation:
    """Atomic operation for dry run simulation."""
    
    def __init__(self, vault_data: VaultData):
        self.vault_data = vault_data
    
    def execute(self, permissions: List[Permission]) -> OperationResult:
        """Simulate applying permissions without making changes."""
        try:
            operations: List[str] = []
            
            # Group permissions by record and folder
            folder_operations: Dict[str, str] = {}
            permission_operations: List[str] = []
            
            for permission in permissions:
                # Simulate folder creation
                folder_path = f"[Perms]/{permission.record.folder_path}"
                if folder_path not in folder_operations:
                    folder_operations[folder_path] = f"Ensure folder path: {folder_path}"
                
                # Simulate record sharing
                share_op = f"Share record '{permission.record.title}' to folder '{folder_path}'"
                if share_op not in operations:
                    operations.append(share_op)
                
                # Simulate permission setting
                perm_op = (f"Set '{permission.level.value}' permissions for team "
                          f"'{permission.team.name}' on record '{permission.record.title}'")
                permission_operations.append(perm_op)
            
            # Combine all operations
            all_operations = list(folder_operations.values()) + operations + permission_operations
            
            return OperationResult.success_result(
                f"Dry run completed: {len(all_operations)} operations planned",
                data={'operations': all_operations}
            )
            
        except Exception as e:
            return OperationResult.error_result(f"Dry run failed: {e}")

class FolderPathOperation:
    """Atomic operation for folder path processing."""
    
    def __init__(self, root_folder: str = "[Perms]"):
        self.root_folder = root_folder
    
    def get_target_folder_path(self, record_folder_path: str) -> str:
        """Get target folder path for a record."""
        clean_path = record_folder_path.strip('/')
        if clean_path:
            return f"{self.root_folder}/{clean_path}"
        return self.root_folder
    
    def parse_folder_components(self, folder_path: str) -> List[str]:
        """Parse folder path into components."""
        if not folder_path or folder_path == self.root_folder:
            return [self.root_folder]
        
        # Remove root folder prefix if present
        if folder_path.startswith(f"{self.root_folder}/"):
            remaining_path = folder_path[len(f"{self.root_folder}/"):]
            components = [self.root_folder]
            if remaining_path:
                components.extend([c.strip() for c in remaining_path.split('/') if c.strip()])
            return components
        
        # If it doesn't start with root folder, treat as relative path
        components = [self.root_folder]
        components.extend([c.strip() for c in folder_path.split('/') if c.strip()])
        return components 