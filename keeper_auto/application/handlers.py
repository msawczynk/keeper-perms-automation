"""
Atomic command handlers for CLI operations.
Each handler has single responsibility for a specific command.
"""

from typing import Optional, Tuple
from pathlib import Path
import sys

from .services import ApplicationCoordinator, ValidationReport, ApplyReport


class BaseHandler:
    """Base handler with common functionality."""
    
    def __init__(self, coordinator: ApplicationCoordinator):
        self.coordinator = coordinator
    
    def ensure_initialized(self) -> bool:
        """Ensure coordinator is initialized."""
        if not self.coordinator.config or not self.coordinator.vault_data:
            print("Error: System not initialized. Please run initialization first.")
            return False
        return True


class ConfigureHandler(BaseHandler):
    """Handler for configure command."""
    
    def handle(self) -> int:
        """Handle configure command."""
        print("Configure command not yet implemented.")
        print("This will guide users through initial setup.")
        return 1


class ValidateHandler(BaseHandler):
    """Handler for validate command."""
    
    def handle(self, csv_path: Path, max_records: int = 5000) -> int:
        """Handle validate command."""
        if not self.ensure_initialized():
            return 1
        
        if not csv_path.exists():
            print(f"Error: CSV file not found: {csv_path}")
            return 1
        
        print(f"Validating CSV file: {csv_path}")
        report = self.coordinator.validate_csv(csv_path, max_records)
        
        self._print_validation_report(report)
        
        return 0 if report.is_valid else 1
    
    def _print_validation_report(self, report: ValidationReport):
        """Print validation report to console."""
        print(f"\nValidation Results:")
        print(f"  Rows processed: {report.row_count}")
        print(f"  Errors: {report.error_count}")
        print(f"  Warnings: {report.warning_count}")
        print(f"  Status: {'✓ VALID' if report.is_valid else '✗ INVALID'}")
        
        if report.errors:
            print("\nErrors:")
            for error in report.errors:
                print(f"  - {error}")
        
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"  - {warning}")


class TemplateHandler(BaseHandler):
    """Handler for template command."""
    
    def handle(self, output_path: Path) -> int:
        """Handle template command."""
        if not self.ensure_initialized():
            return 1
        
        print(f"Generating CSV template: {output_path}")
        success = self.coordinator.generate_template(output_path)
        
        if success:
            print(f"✓ Template generated successfully: {output_path}")
            return 0
        else:
            print(f"✗ Template generation failed")
            return 1


class DryRunHandler(BaseHandler):
    """Handler for dry-run command."""
    
    def handle(self, csv_path: Path) -> int:
        """Handle dry-run command."""
        if not self.ensure_initialized():
            return 1
        
        if not csv_path.exists():
            print(f"Error: CSV file not found: {csv_path}")
            return 1
        
        print(f"Performing dry run: {csv_path}")
        report = self.coordinator.dry_run(csv_path)
        
        self._print_apply_report(report, dry_run=True)
        
        return 0 if report.success else 1
    
    def _print_apply_report(self, report: ApplyReport, dry_run: bool = False):
        """Print apply report to console."""
        operation_type = "Dry Run" if dry_run else "Apply"
        print(f"\n{operation_type} Results:")
        print(f"  Total operations: {report.total_operations}")
        print(f"  Failed operations: {report.failed_operations}")
        print(f"  Status: {'✓ SUCCESS' if report.success else '✗ FAILED'}")
        
        if report.checkpoint_file:
            print(f"  Checkpoint: {report.checkpoint_file}")
        
        if report.errors:
            print("\nErrors:")
            for error in report.errors:
                print(f"  - {error}")
        
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"  - {warning}")


class ApplyHandler(BaseHandler):
    """Handler for apply command."""
    
    def handle(self, csv_path: Path, max_records: int = 5000, force: bool = False) -> int:
        """Handle apply command."""
        if not self.ensure_initialized():
            return 1
        
        if not csv_path.exists():
            print(f"Error: CSV file not found: {csv_path}")
            return 1
        
        # First validate the CSV
        print(f"Validating CSV file: {csv_path}")
        validation_report = self.coordinator.validate_csv(csv_path, max_records)
        
        if not validation_report.is_valid:
            print("❌ Validation failed. Cannot proceed with apply.")
            ValidateHandler(self.coordinator)._print_validation_report(validation_report)
            return 1
        
        # Check max records
        if validation_report.row_count > max_records and not force:
            print(f"❌ CSV has {validation_report.row_count} rows, exceeding max-records limit of {max_records}")
            print("Use --force to override this limit or --max-records to increase it.")
            return 1
        
        # Show confirmation
        print(f"✅ Validation passed. Ready to apply {validation_report.row_count} records.")
        if not force:
            response = input("Proceed with apply? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Apply cancelled by user.")
                return 0
        
        print(f"Applying changes: {csv_path}")
        report = self.coordinator.apply_changes(csv_path, max_records, force)
        
        DryRunHandler(self.coordinator)._print_apply_report(report, dry_run=False)
        
        return 0 if report.success else 1


class HandlerFactory:
    """Factory for creating command handlers."""
    
    def __init__(self, run_id: Optional[str] = None):
        self.coordinator = ApplicationCoordinator(run_id=run_id)
    
    def initialize(self) -> bool:
        """Initialize the coordinator."""
        return self.coordinator.initialize()
    
    def create_configure_handler(self) -> ConfigureHandler:
        """Create configure handler."""
        return ConfigureHandler(self.coordinator)
    
    def create_validate_handler(self) -> ValidateHandler:
        """Create validate handler."""
        return ValidateHandler(self.coordinator)
    
    def create_template_handler(self) -> TemplateHandler:
        """Create template handler."""
        return TemplateHandler(self.coordinator)
    
    def create_dry_run_handler(self) -> DryRunHandler:
        """Create dry-run handler."""
        return DryRunHandler(self.coordinator)
    
    def create_apply_handler(self) -> ApplyHandler:
        """Create apply handler."""
        return ApplyHandler(self.coordinator)
    
    def get_run_id(self) -> str:
        """Get current run ID."""
        return self.coordinator.get_run_id()
    
    def get_log_file(self) -> Path:
        """Get current log file path."""
        return self.coordinator.get_log_file() 