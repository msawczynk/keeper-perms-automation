#!/usr/bin/env python3
"""
Keeper Permissions Automation CLI
Enhanced with vault storage integration for centralized data management.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from keeper_auto.application.services import ApplicationCoordinator
from keeper_auto.infrastructure.vault_storage_adapter import VaultStorageAdapter

def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with vault storage options."""
    parser = argparse.ArgumentParser(
        description="Keeper Permissions Automation Tool with Vault Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (local storage)
  python cli.py configure
  python cli.py template my_template.csv
  python cli.py validate permissions.csv
  python cli.py dry-run permissions.csv
  python cli.py apply permissions.csv
  
  # With vault storage enabled
  python cli.py --vault-storage configure
  python cli.py --vault-storage template my_template.csv
  python cli.py --vault-storage apply permissions.csv
  
  # Resume from vault-stored checkpoint
  python cli.py --vault-storage apply permissions.csv --resume-from-vault run-id-123
  
  # Export system data from vault
  python cli.py --vault-storage export-data --output backup.json
        """
    )
    
    # Global options
    parser.add_argument(
        '--vault-storage',
        action='store_true',
        help='Enable vault storage for logs, checkpoints, and configurations'
    )
    
    parser.add_argument(
        '--run-id',
        type=str,
        help='Specify a custom run ID (default: auto-generated)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Configure command
    configure_parser = subparsers.add_parser(
        'configure',
        help='Show or create configuration'
    )
    configure_parser.add_argument(
        '--config-name',
        type=str,
        default='default',
        help='Configuration name (default: default)'
    )
    
    # Template command
    template_parser = subparsers.add_parser(
        'template',
        help='Generate CSV template'
    )
    template_parser.add_argument(
        'output_file',
        type=str,
        help='Output CSV file path'
    )
    template_parser.add_argument(
        '--template-name',
        type=str,
        help='Template name for vault storage'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate CSV file'
    )
    validate_parser.add_argument(
        'csv_file',
        type=str,
        help='CSV file to validate'
    )
    validate_parser.add_argument(
        '--max-records',
        type=int,
        default=5000,
        help='Maximum number of records to validate (default: 5000)'
    )
    
    # Dry-run command
    dry_run_parser = subparsers.add_parser(
        'dry-run',
        help='Show what would be changed without applying'
    )
    dry_run_parser.add_argument(
        'csv_file',
        type=str,
        help='CSV file to process'
    )
    dry_run_parser.add_argument(
        '--max-records',
        type=int,
        default=5000,
        help='Maximum number of records to process (default: 5000)'
    )
    
    # Apply command
    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply changes to Keeper vault'
    )
    apply_parser.add_argument(
        'csv_file',
        type=str,
        help='CSV file to process'
    )
    apply_parser.add_argument(
        '--max-records',
        type=int,
        default=5000,
        help='Maximum number of records to process (default: 5000)'
    )
    apply_parser.add_argument(
        '--force',
        action='store_true',
        help='Force processing even if max-records limit is exceeded'
    )
    apply_parser.add_argument(
        '--resume',
        type=str,
        help='Resume from checkpoint file'
    )
    apply_parser.add_argument(
        '--resume-from-vault',
        type=str,
        help='Resume from vault-stored checkpoint by run ID'
    )
    
    # Vault-specific commands
    if '--vault-storage' in sys.argv:
        # Export data command
        export_parser = subparsers.add_parser(
            'export-data',
            help='Export system data from vault'
        )
        export_parser.add_argument(
            '--output',
            type=str,
            required=True,
            help='Output file for exported data'
        )
        export_parser.add_argument(
            '--date-range',
            type=str,
            nargs=2,
            help='Date range for export (YYYY-MM-DD YYYY-MM-DD)'
        )
        
        # List checkpoints command
        list_checkpoints_parser = subparsers.add_parser(
            'list-checkpoints',
            help='List available checkpoints in vault'
        )
        list_checkpoints_parser.add_argument(
            '--date-range',
            type=str,
            nargs=2,
            help='Date range filter (YYYY-MM-DD YYYY-MM-DD)'
        )
        
        # Cleanup command
        cleanup_parser = subparsers.add_parser(
            'cleanup',
            help='Clean up old data in vault'
        )
        cleanup_parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to retain data (default: 30)'
        )
    
    return parser

def main():
    """Main CLI entry point with vault storage integration."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Initialize logging
        # Logger is initialized within ApplicationCoordinator
        
        # Initialize application coordinator with vault storage
        coordinator = ApplicationCoordinator(
            run_id=args.run_id
        )
        
        # Initialize vault adapter if needed
        vault_adapter = None
        if args.vault_storage:
            vault_adapter = VaultStorageAdapter()
        
        # Handle commands
        if args.command == 'configure':
            return handle_configure(coordinator, args, vault_adapter)
        
        elif args.command == 'template':
            return handle_template(coordinator, args, vault_adapter)
        
        elif args.command == 'validate':
            return handle_validate(coordinator, args)
        
        elif args.command == 'dry-run':
            return handle_dry_run(coordinator, args)
        
        elif args.command == 'apply':
            return handle_apply(coordinator, args, vault_adapter)
        
        elif args.command == 'export-data' and args.vault_storage and vault_adapter:
            return handle_export_data(vault_adapter, args)
        
        elif args.command == 'list-checkpoints' and args.vault_storage and vault_adapter:
            return handle_list_checkpoints(vault_adapter, args)
        
        elif args.command == 'cleanup' and args.vault_storage and vault_adapter:
            return handle_cleanup(vault_adapter, args)
        
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

def handle_configure(coordinator: ApplicationCoordinator, args: argparse.Namespace, vault_adapter: Optional[VaultStorageAdapter]) -> int:
    """Handle configure command with vault storage support."""
    try:
        # Initialize coordinator first
        if not coordinator.initialize():
            print("Failed to initialize coordinator")
            return 1
        
        # Load configuration from vault if available, otherwise use default
        if vault_adapter:
            config = vault_adapter.load_configuration(args.config_name)
        else:
            config = coordinator.config  # Use the config loaded during initialization
        
        if config:
            print("Current configuration:")
            print(f"  Root folder name: {config.root_folder_name}")
            print(f"  Included teams: {config.included_teams or 'All teams'}")
            print(f"  Included folders: {config.included_folders or 'All folders'}")
            print(f"  Excluded folders: {config.excluded_folders or 'None'}")
            
            if vault_adapter:
                print(f"  Storage: Vault (config: {args.config_name})")
            else:
                print("  Storage: Local file system")
        else:
            print("No configuration found. Using defaults.")
            if vault_adapter:
                print("Creating default configuration in vault...")
                from keeper_auto.models import ConfigRecord
                default_config = ConfigRecord()
                vault_adapter.store_configuration(default_config, args.config_name)
                print(f"Default configuration stored in vault as '{args.config_name}'")
        
        return 0
        
    except Exception as e:
        print(f"Configuration error: {e}")
        return 1

def handle_template(coordinator: ApplicationCoordinator, args: argparse.Namespace, vault_adapter: Optional[VaultStorageAdapter]) -> int:
    """Handle template command with vault storage support."""
    try:
        # Initialize coordinator first
        if not coordinator.initialize():
            print("Failed to initialize coordinator")
            return 1
        
        output_path = Path(args.output_file)
        success = coordinator.generate_template(output_path)
        
        if success:
            print(f"Template generated: {output_path}")
            
            # Also store in vault if enabled
            if vault_adapter:
                with open(output_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                template_name = args.template_name or f"template-{coordinator.get_run_id()}"
                vault_record_uid = vault_adapter.store_csv_template(template_content, template_name)
                print(f"Template also stored in vault as '{template_name}' (UID: {vault_record_uid})")
        else:
            print("Failed to generate template")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"Template generation error: {e}")
        return 1

def handle_validate(coordinator: ApplicationCoordinator, args: argparse.Namespace) -> int:
    """Handle validate command."""
    try:
        # Initialize coordinator first
        if not coordinator.initialize():
            print("Failed to initialize coordinator")
            return 1
        
        csv_path = Path(args.csv_file)
        if not csv_path.exists():
            print(f"CSV file not found: {csv_path}")
            return 1
        
        result = coordinator.validate_csv(csv_path, args.max_records)
        
        if result.is_valid:
            print(f"✅ CSV file is valid ({result.row_count} rows)")
        else:
            print(f"❌ CSV file has {len(result.errors)} error(s)")
            for error in result.errors:
                print(f"  Error: {error}")
        
        if result.warnings:
            print(f"⚠️  {len(result.warnings)} warning(s):")
            for warning in result.warnings:
                print(f"  Warning: {warning}")
        
        return 0 if result.is_valid else 1
        
    except Exception as e:
        print(f"Validation error: {e}")
        return 1

def handle_dry_run(coordinator: ApplicationCoordinator, args: argparse.Namespace) -> int:
    """Handle dry-run command."""
    try:
        # Initialize coordinator first
        if not coordinator.initialize():
            print("Failed to initialize coordinator")
            return 1
        
        csv_path = Path(args.csv_file)
        if not csv_path.exists():
            print(f"CSV file not found: {csv_path}")
            return 1
        
        report = coordinator.dry_run(csv_path)
        
        if report.success:
            print(f"✅ Dry run completed successfully")
            print(f"  Total operations planned: {report.total_operations}")
            
            if report.warnings:
                print(f"⚠️  {len(report.warnings)} warning(s):")
                for warning in report.warnings:
                    print(f"  Warning: {warning}")
        else:
            print(f"❌ Dry run failed")
            print(f"  Failed operations: {report.failed_operations}")
            for error in report.errors:
                print(f"  Error: {error}")
        
        return 0 if report.success else 1
        
    except Exception as e:
        print(f"Dry run error: {e}")
        return 1

def handle_apply(coordinator: ApplicationCoordinator, args: argparse.Namespace, vault_adapter: Optional[VaultStorageAdapter]) -> int:
    """Handle apply command with vault storage and resume support."""
    try:
        # Initialize coordinator first
        if not coordinator.initialize():
            print("Failed to initialize coordinator")
            return 1
        
        csv_path = Path(args.csv_file)
        if not csv_path.exists():
            print(f"CSV file not found: {csv_path}")
            return 1
        
        # Handle resume options
        if args.resume_from_vault and vault_adapter:
            print(f"Resuming from vault checkpoint: {args.resume_from_vault}")
            # Implementation would load checkpoint from vault and resume
            # This is a placeholder for the actual resume logic
        elif args.resume:
            print(f"Resuming from local checkpoint: {args.resume}")
            # Implementation would load local checkpoint and resume
        
        report = coordinator.apply_changes(csv_path, args.max_records, args.force)
        
        if report.success:
            print(f"✅ Successfully applied {report.total_operations} operations")
            if vault_adapter:
                # Store final report in vault
                report_data = {
                    "operation_type": "apply",
                    "success": report.success,
                    "total_operations": report.total_operations,
                    "failed_operations": report.failed_operations,
                    "csv_file": str(csv_path),
                    "errors": report.errors,
                    "warnings": report.warnings
                }
                report_uid = vault_adapter.store_operation_report(report_data, coordinator.get_run_id())
                print(f"Operation report stored in vault (UID: {report_uid})")
        else:
            print(f"❌ Failed to apply changes. {report.failed_operations} operations failed")
            for error in report.errors:
                print(f"  Error: {error}")
        
        return 0 if report.success else 1
        
    except Exception as e:
        print(f"Apply error: {e}")
        return 1

def handle_export_data(vault_adapter: VaultStorageAdapter, args: argparse.Namespace) -> int:
    """Handle export-data command."""
    try:
        date_range = None
        if args.date_range:
            from datetime import datetime
            start_date = datetime.strptime(args.date_range[0], '%Y-%m-%d')
            end_date = datetime.strptime(args.date_range[1], '%Y-%m-%d')
            date_range = (start_date, end_date)
        
        export_data = vault_adapter.export_system_data(date_range)
        
        # Save to output file
        import json
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"System data exported to: {args.output}")
        return 0
        
    except Exception as e:
        print(f"Export error: {e}")
        return 1

def handle_list_checkpoints(vault_adapter: VaultStorageAdapter, args: argparse.Namespace) -> int:
    """Handle list-checkpoints command."""
    try:
        date_range = None
        if args.date_range:
            from datetime import datetime
            start_date = datetime.strptime(args.date_range[0], '%Y-%m-%d')
            end_date = datetime.strptime(args.date_range[1], '%Y-%m-%d')
            date_range = (start_date, end_date)
        
        checkpoints = vault_adapter.list_checkpoints(date_range)
        
        if checkpoints:
            print(f"Found {len(checkpoints)} checkpoints:")
            for checkpoint in checkpoints:
                print(f"  - {checkpoint['run_id']}: {checkpoint['operation_type']} ({checkpoint['timestamp']})")
        else:
            print("No checkpoints found")
        
        return 0
        
    except Exception as e:
        print(f"List checkpoints error: {e}")
        return 1

def handle_cleanup(vault_adapter: VaultStorageAdapter, args: argparse.Namespace) -> int:
    """Handle cleanup command."""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=args.retention_days)
        cleanup_result = vault_adapter.cleanup_old_data(cutoff_date)
        
        print(f"Cleanup completed:")
        print(f"  Removed {cleanup_result.get('deleted_records', 0)} old records")
        print(f"  Freed {cleanup_result.get('freed_space', 0)} bytes")
        
        return 0
        
    except Exception as e:
        print(f"Cleanup error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
