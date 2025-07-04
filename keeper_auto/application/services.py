"""
Atomic application services - Clean implementation.
Coordinates domain operations with infrastructure adapters.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import csv

# Import from atomic domain models
from ..domain.models import ConfigRecord, VaultData, Team, Record, Folder
# Import working components directly
from ..keeper_client import get_teams, get_folder_data
from ..logger import init_logger, StructuredLogger
from ..checkpoint import CheckpointManager


@dataclass
class ValidationReport:
    """Atomic validation report."""
    is_valid: bool
    error_count: int
    warning_count: int
    row_count: int
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class ApplyReport:
    """Atomic apply operation report."""
    success: bool
    total_operations: int
    failed_operations: int
    errors: List[str]
    warnings: List[str]
    checkpoint_file: Optional[str] = None


class AtomicValidationService:
    """Atomic service for CSV validation with single responsibility."""
    
    def __init__(self, vault_data: Optional[VaultData] = None):
        self.vault_data = vault_data
    
    def validate_csv(self, csv_path: Path, max_records: int = 5000) -> ValidationReport:
        """Validate CSV file and return structured report."""
        errors: List[str] = []
        warnings: List[str] = []
        row_count = 0
        
        try:
            # Check if file exists
            if not csv_path.exists():
                return ValidationReport(
                    is_valid=False,
                    error_count=1,
                    warning_count=0,
                    row_count=0,
                    errors=[f"File not found: {csv_path}"],
                    warnings=[],
                    metadata={}
                )
            
            # Read and validate CSV
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                
                # Validate required headers
                required_headers = {'record_uid', 'title', 'folder_path'}
                missing_headers = required_headers - set(headers)
                if missing_headers:
                    errors.append(f"Missing required headers: {missing_headers}")
                
                # Process rows
                rows = list(reader)
                row_count = len(rows)
                
                if row_count > max_records:
                    warnings.append(f"Large file: {row_count} rows (max recommended: {max_records})")
                
                # Validate each row
                for i, row in enumerate(rows, 1):
                    if not row.get('record_uid', '').strip():
                        errors.append(f"Row {i}: Missing record_uid")
                    if not row.get('title', '').strip():
                        errors.append(f"Row {i}: Missing title")
                
                # Check team columns
                team_columns = set(headers) - required_headers
                if not team_columns:
                    warnings.append("No team columns found")
                
                # Validate with vault data if available
                if self.vault_data:
                    vault_teams = set(team.name for team in self.vault_data.teams_by_uid.values())
                    
                    # Extract team names from CSV headers (handle "TeamName (uid)" format)
                    def extract_team_name(header: str) -> str:
                        """Extract team name from CSV header format 'TeamName (uid)'."""
                        if ' (' in header and header.endswith(')'):
                            return header.split(' (')[0]
                        return header
                    
                    csv_team_names = {extract_team_name(col) for col in team_columns}
                    unknown_teams = csv_team_names - vault_teams
                    
                    if unknown_teams:
                        warnings.append(f"Teams not found in vault: {unknown_teams}")
                    
                    # Also check for teams with UIDs that might be in wrong format
                    teams_with_uids = [col for col in team_columns if ' (' in col and col.endswith(')')]
                    if teams_with_uids and len(teams_with_uids) != len(team_columns):
                        warnings.append("Mix of team formats detected. Use consistent format: 'TeamName (uid)' or 'TeamName'")
            
            return ValidationReport(
                is_valid=len(errors) == 0,
                error_count=len(errors),
                warning_count=len(warnings),
                row_count=row_count,
                errors=errors,
                warnings=warnings,
                metadata={'headers': headers, 'team_columns': list(team_columns)}
            )
        
        except Exception as e:
            return ValidationReport(
                is_valid=False,
                error_count=1,
                warning_count=0,
                row_count=0,
                errors=[f"Validation failed: {e}"],
                warnings=[],
                metadata={}
            )


class AtomicTemplateService:
    """Atomic service for CSV template generation."""
    
    def __init__(self, vault_data: VaultData, config: ConfigRecord):
        self.vault_data = vault_data
        self.config = config
    
    def generate_template(self, output_path: Path) -> bool:
        """Generate CSV template and return success status."""
        try:
            # Get teams from vault data
            teams = list(self.vault_data.teams_by_uid.values())
            records = list(self.vault_data.records_by_uid.values())
            
            # Generate headers with team names (formatted with UIDs for clarity)
            headers = ['record_uid', 'title', 'folder_path']
            for team in teams:
                # Format: "TeamName (uid)" but only show the actual name part
                team_name = team.name
                if team_name.startswith('Team '):
                    # If it's still a placeholder, use the UID
                    headers.append(f"{team_name}")
                else:
                    # Use actual team name with UID for clarity
                    headers.append(f"{team_name} ({team.uid})")
            
            # Write template with all records
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                # Add rows for all records in the vault
                for record in records:
                    row = {
                        'record_uid': record.uid,
                        'title': record.title,
                        'folder_path': record.folder_path
                    }
                    # Add empty permission columns for each team (to be filled by user)
                    for team in teams:
                        team_header = f"{team.name} ({team.uid})" if not team.name.startswith('Team ') else team.name
                        row[team_header] = ''  # Empty for user to fill
                    
                    writer.writerow(row)
            
            return True
        except Exception:
            return False


class AtomicProvisioningService:
    """Atomic service for permissions provisioning."""
    
    def __init__(self, vault_data: VaultData, config: ConfigRecord, logger: StructuredLogger):
        self.vault_data = vault_data
        self.config = config
        self.logger = logger
        self.checkpoint_manager = CheckpointManager(logger.run_id)
    
    def dry_run(self, csv_path: Path) -> ApplyReport:
        """Perform dry run and return report."""
        try:
            changes = self._analyze_changes(csv_path)
            
            return ApplyReport(
                success=True,
                total_operations=len(changes),
                failed_operations=0,
                errors=[],
                warnings=[],
                checkpoint_file=None
            )
        except Exception as e:
            return ApplyReport(
                success=False,
                total_operations=0,
                failed_operations=1,
                errors=[f"Dry run failed: {e}"],
                warnings=[],
                checkpoint_file=None
            )
    
    def apply_changes(self, csv_path: Path, max_records: int = 5000, force: bool = False) -> ApplyReport:
        """Apply changes and return report."""
        try:
            # Start checkpoint
            checkpoint_file = self.checkpoint_manager.create_checkpoint({
                'csv_path': str(csv_path),
                'max_records': max_records,
                'force': force
            })
            
            # Analyze changes
            changes = self._analyze_changes(csv_path)
            
            # For now, just simulate success
            # In real implementation, this would apply changes to Keeper
            success = True
            
            if success:
                self.checkpoint_manager.complete_checkpoint()
                return ApplyReport(
                    success=True,
                    total_operations=len(changes),
                    failed_operations=0,
                    errors=[],
                    warnings=[],
                    checkpoint_file=checkpoint_file
                )
            else:
                return ApplyReport(
                    success=False,
                    total_operations=len(changes),
                    failed_operations=len(changes),
                    errors=["Apply operation failed"],
                    warnings=[],
                    checkpoint_file=checkpoint_file
                )
        except Exception as e:
            return ApplyReport(
                success=False,
                total_operations=0,
                failed_operations=1,
                errors=[f"Apply failed: {e}"],
                warnings=[],
                checkpoint_file=None
            )
    
    def _analyze_changes(self, csv_path: Path) -> List[Dict[str, Any]]:
        """Analyze what changes would be made."""
        changes: List[Dict[str, Any]] = []
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record_uid = row.get('record_uid', '').strip()
                if record_uid:
                    changes.append({
                        'type': 'update_permissions',
                        'record_uid': record_uid,
                        'title': row.get('title', ''),
                        'folder_path': row.get('folder_path', '')
                    })
        
        return changes


class AtomicConfigService:
    """Atomic service for configuration management."""
    
    def __init__(self):
        self.default_config = ConfigRecord()
    
    def load_config(self) -> Optional[ConfigRecord]:
        """Load configuration and return config record."""
        # For now, return default config
        # In real implementation, this would load from Keeper
        return self.default_config
    
    def save_config(self, config: ConfigRecord) -> bool:
        """Save configuration and return success status."""
        # For now, just return success
        # In real implementation, this would save to Keeper
        return True


class AtomicVaultService:
    """Atomic service for vault data management."""
    
    def __init__(self, config: ConfigRecord):
        self.config = config
    
    def load_vault_data(self) -> Optional[VaultData]:
        """Load vault data and return vault data object."""
        try:
            # Get data from Keeper client
            teams_data = get_teams()
            folder_data = get_folder_data()
            
            # Create VaultData instance
            vault_data = VaultData()
            
            # Populate teams
            for team_info in teams_data:
                team_uid = team_info.get('team_uid', '')
                team_name = team_info.get('team_name', f'Team {team_uid}')
                if team_uid:
                    team = Team.create(team_uid, team_name)
                    vault_data.teams_by_uid[team_uid] = team
            
            # Populate records and folders from folder_data
            if folder_data:
                # First, build folder lookup for path building
                folder_lookup: Dict[str, Dict[str, Optional[str]]] = {}
                folders = folder_data.get('folders', [])
                for folder_info in folders:
                    folder_uid = folder_info.get('uid', '')
                    folder_name = folder_info.get('name', 'Untitled Folder')
                    folder_path = folder_info.get('path', '/')
                    parent_uid = folder_info.get('parent_uid', None)
                    if folder_uid:
                        folder = Folder.create(folder_uid, folder_name, folder_path)
                        vault_data.folders_by_uid[folder_uid] = folder
                        folder_lookup[folder_uid] = {
                            'name': folder_name,
                            'parent_uid': parent_uid
                        }
                
                # Helper function to build folder path
                def build_folder_path(folder_uid: Optional[str]) -> str:
                    if not folder_uid or folder_uid not in folder_lookup:
                        return ""
                    
                    path_parts: List[str] = []
                    current_uid: Optional[str] = folder_uid
                    
                    while current_uid and current_uid in folder_lookup:
                        folder_info = folder_lookup[current_uid]
                        folder_name = folder_info.get('name', '')
                        if folder_name:
                            path_parts.append(folder_name)
                        current_uid = folder_info.get('parent_uid')
                    
                    # Reverse to get correct order (root to leaf)
                    path_parts.reverse()
                    return "/" + "/".join(path_parts) if path_parts else ""
                
                # Process records with correct field names
                records = folder_data.get('records', [])
                for record_info in records:
                    record_uid = record_info.get('uid', '')  # Use 'uid' not 'record_uid'
                    title = record_info.get('title', 'Untitled')
                    folder_uid = record_info.get('folder_uid', None)
                    folder_path = build_folder_path(folder_uid)
                    
                    if record_uid:
                        record = Record.create(record_uid, title, folder_path)
                        vault_data.records_by_uid[record_uid] = record
            
            return vault_data
        except Exception as e:
            print(f"Error loading vault data: {e}")
            return None


class ApplicationCoordinator:
    """
    Coordinates all atomic services for complete operations.
    Implements the facade pattern to provide simple interface.
    """
    
    def __init__(self, run_id: Optional[str] = None):
        self.logger = init_logger(run_id=run_id)
        self.config_service = AtomicConfigService()
        self.config: Optional[ConfigRecord] = None
        self.vault_service: Optional[AtomicVaultService] = None
        self.vault_data: Optional[VaultData] = None
    
    def initialize(self) -> bool:
        """Initialize all services and return success status."""
        try:
            # Load configuration
            self.config = self.config_service.load_config()
            if not self.config:
                return False
            
            # Load vault data
            self.vault_service = AtomicVaultService(self.config)
            self.vault_data = self.vault_service.load_vault_data()
            if not self.vault_data:
                return False
            
            self.logger.info("initialization_complete", {
                "teams_count": len(self.vault_data.teams_by_uid),
                "records_count": len(self.vault_data.records_by_uid),
                "folders_count": len(self.vault_data.folders_by_uid)
            })
            
            return True
        except Exception as e:
            self.logger.error("initialization_failed", {"error": str(e)})
            return False
    
    def validate_csv(self, csv_path: Path, max_records: int = 5000) -> ValidationReport:
        """Validate CSV file with full coordination."""
        validation_service = AtomicValidationService(self.vault_data)
        report = validation_service.validate_csv(csv_path, max_records)
        
        # Log validation results
        self.logger.info("validation_completed", {
            "is_valid": report.is_valid,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "row_count": report.row_count
        })
        
        return report
    
    def generate_template(self, output_path: Path) -> bool:
        """Generate CSV template with full coordination."""
        if not self.config or not self.vault_data:
            return False
        
        template_service = AtomicTemplateService(self.vault_data, self.config)
        success = template_service.generate_template(output_path)
        
        if success:
            self.logger.info("template_generated", {"output_path": str(output_path)})
        else:
            self.logger.error("template_generation_failed", {"output_path": str(output_path)})
        
        return success
    
    def dry_run(self, csv_path: Path) -> ApplyReport:
        """Perform dry run with full coordination."""
        if not self.config or not self.vault_data:
            return ApplyReport(
                success=False,
                total_operations=0,
                failed_operations=1,
                errors=["Service not initialized"],
                warnings=[]
            )
        
        provisioning_service = AtomicProvisioningService(self.vault_data, self.config, self.logger)
        return provisioning_service.dry_run(csv_path)
    
    def apply_changes(self, csv_path: Path, max_records: int = 5000, force: bool = False) -> ApplyReport:
        """Apply changes with full coordination."""
        if not self.config or not self.vault_data:
            return ApplyReport(
                success=False,
                total_operations=0,
                failed_operations=1,
                errors=["Service not initialized"],
                warnings=[]
            )
        
        provisioning_service = AtomicProvisioningService(self.vault_data, self.config, self.logger)
        report = provisioning_service.apply_changes(csv_path, max_records, force)
        
        # Log apply summary
        self.logger.info("apply_completed", {
            "success": report.success,
            "total_operations": report.total_operations,
            "failed_operations": report.failed_operations
        })
        
        return report
    
    def get_run_id(self) -> str:
        """Get current run ID."""
        return self.logger.run_id
    
    def get_log_file(self) -> Path:
        """Get current log file path."""
        return self.logger.log_file 