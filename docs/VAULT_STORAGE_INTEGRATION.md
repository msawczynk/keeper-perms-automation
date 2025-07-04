# Vault Storage Integration

## Overview

The Keeper Permissions Automation tool now supports storing all system data directly in the Keeper vault for centralized, secure management. This enhancement moves logs, checkpoints, configurations, operation reports, and CSV templates from local file storage to dedicated Keeper vault records.

## Benefits

### 🔒 **Enhanced Security**
- All sensitive data stored in encrypted Keeper vault
- No local files containing operational data
- Centralized access control through Keeper permissions

### 🌐 **Centralized Management**
- Single source of truth for all automation data
- Accessible from any environment with Keeper access
- Team collaboration on configurations and reports

### 📊 **Better Auditability**
- Complete audit trail stored in vault
- Immutable record of all operations
- Easy compliance reporting and analysis

### 🔄 **Improved Continuity**
- Resume operations from any environment
- Disaster recovery through vault backups
- No dependency on local file systems

## Architecture

### Storage Organization

The vault storage system creates a structured hierarchy in your Keeper vault:

```
[Perms-System]/                    # Main system folder
├── Logs/                          # Daily log records
│   ├── 2025-07-04/
│   │   └── Perms-Log-20250704     # Daily log aggregation
│   └── 2025-07-05/
├── Checkpoints/                   # Operation checkpoints
│   ├── 2025-07-04/
│   │   ├── Checkpoint-abc123      # Individual checkpoints
│   │   └── Checkpoint-def456
│   └── 2025-07-05/
├── Reports/                       # Operation reports
│   ├── 2025-07-04/
│   │   └── Operation-Report-abc123
│   └── 2025-07-05/
├── Templates/                     # CSV templates
│   ├── CSV-Template-default
│   └── CSV-Template-team-specific
└── Configurations/                # System configurations
    ├── Perms-Config-default
    └── Perms-Config-production
```

### Data Types Stored

#### 1. **Log Entries**
- Structured JSON logs with timestamps
- Operation details and results
- Error messages and warnings
- Performance metrics

#### 2. **Checkpoints**
- Operation state for resume capability
- Progress tracking for large operations
- Error recovery information
- Idempotent operation support

#### 3. **Configurations**
- System settings and parameters
- Team and folder inclusion/exclusion rules
- Environment-specific configurations
- Version-controlled settings

#### 4. **Operation Reports**
- Comprehensive operation summaries
- Success/failure statistics
- Detailed error analysis
- Performance benchmarks

#### 5. **CSV Templates**
- Generated templates with real data
- Team-specific templates
- Historical template versions
- Template metadata

## Usage

### Enabling Vault Storage

Add the `--vault-storage` flag to any CLI command:

```bash
# Basic usage with vault storage
python cli.py --vault-storage configure
python cli.py --vault-storage template my_template.csv
python cli.py --vault-storage apply permissions.csv
```

### Configuration Management

#### Store Configuration in Vault
```bash
# Create or update default configuration
python cli.py --vault-storage configure

# Create named configuration
python cli.py --vault-storage configure --config-name production
```

#### Load Configuration from Vault
The system automatically loads configurations from the vault when `--vault-storage` is enabled.

### Template Generation

#### Generate and Store Templates
```bash
# Generate template and store in vault
python cli.py --vault-storage template output.csv --template-name team-alpha

# Templates are accessible from any environment
python cli.py --vault-storage template output2.csv --template-name team-alpha
```

### Operation Execution

#### Apply Changes with Vault Logging
```bash
# All logs and checkpoints stored in vault
python cli.py --vault-storage apply permissions.csv

# Resume from vault-stored checkpoint
python cli.py --vault-storage apply permissions.csv --resume-from-vault run-id-123
```

### Data Management

#### Export System Data
```bash
# Export all system data
python cli.py --vault-storage export-data --output backup.json

# Export data for specific date range
python cli.py --vault-storage export-data --output backup.json --date-range 2025-07-01 2025-07-31
```

#### List Checkpoints
```bash
# List all checkpoints
python cli.py --vault-storage list-checkpoints

# List checkpoints for date range
python cli.py --vault-storage list-checkpoints --date-range 2025-07-01 2025-07-31
```

#### Cleanup Old Data
```bash
# Clean up data older than 30 days (default)
python cli.py --vault-storage cleanup

# Custom retention period
python cli.py --vault-storage cleanup --retention-days 60
```

## Implementation Details

### VaultStorageAdapter

The `VaultStorageAdapter` class provides the core functionality:

```python
from keeper_auto.infrastructure.vault_storage_adapter import VaultStorageAdapter

# Initialize adapter
adapter = VaultStorageAdapter()

# Store log entry
adapter.store_log_entry(log_entry)

# Store checkpoint
adapter.store_checkpoint(checkpoint)

# Store configuration
adapter.store_configuration(config, "production")

# Load configuration
config = adapter.load_configuration("production")
```

### Enhanced Logger

The logger automatically stores entries in the vault when enabled:

```python
from keeper_auto.logger import init_logger

# Initialize with vault storage
logger = init_logger(vault_storage=True)

# Logs are automatically stored in vault
logger.info("operation_complete", {"records_processed": 100})
```

### Enhanced Checkpoint Manager

Checkpoints are automatically synced to the vault:

```python
from keeper_auto.checkpoint import CheckpointManager

# Initialize with vault storage
manager = CheckpointManager(vault_storage=True)

# Create checkpoint (stored locally and in vault)
manager.create_checkpoint({"csv_path": "data.csv"})

# Add operation (synced to vault)
manager.add_operation("create_folder", "folder-uid", "Team Alpha")
```

## Security Considerations

### Access Control
- Vault storage respects Keeper's permission model
- System folder permissions should be restricted to automation users
- Regular access audits recommended

### Data Encryption
- All data encrypted at rest in Keeper vault
- In-transit encryption through Keeper APIs
- No plaintext data stored locally

### Backup and Recovery
- Vault data included in Keeper backups
- Export functionality for additional backups
- Checkpoint system enables operation recovery

## Performance Considerations

### Batch Operations
- Log entries batched daily for efficiency
- Checkpoint updates minimized during operations
- Bulk export capabilities for large datasets

### Caching
- Local fallback for vault connectivity issues
- Configuration caching to reduce API calls
- Intelligent retry mechanisms

### Scalability
- Folder structure scales with operation volume
- Automatic cleanup of old data
- Efficient search and retrieval patterns

## Migration from Local Storage

### Automatic Migration
When enabling vault storage for the first time:

1. **Existing Configurations**: Automatically detected and migrated
2. **Active Checkpoints**: Can be imported to vault storage
3. **Historical Logs**: Available for manual migration if needed

### Migration Commands
```bash
# Enable vault storage (migrates current config)
python cli.py --vault-storage configure

# Import existing checkpoint
python cli.py --vault-storage apply data.csv --resume checkpoint-abc123.json
```

## Troubleshooting

### Common Issues

#### Vault Storage Not Available
```
Warning: Vault storage adapter not available, falling back to file logging
```
**Solution**: Ensure Keeper SDK is properly installed and authenticated.

#### Permission Denied
```
Error: Failed to store log entry in vault: Permission denied
```
**Solution**: Verify Keeper user has permissions to create records in the system folder.

#### Connectivity Issues
```
Warning: Failed to store checkpoint in vault: Connection timeout
```
**Solution**: Check network connectivity and Keeper service status. Local files are maintained as backup.

### Debug Mode
Enable verbose logging for troubleshooting:
```bash
python cli.py --vault-storage --verbose apply data.csv
```

### Fallback Behavior
The system gracefully falls back to local storage if vault storage fails:
- Operations continue without interruption
- Local files maintained as backup
- Vault storage automatically resumes when available

## Best Practices

### Configuration Management
1. **Use named configurations** for different environments
2. **Regular configuration backups** through export functionality
3. **Version control** configuration changes through vault history

### Operational Procedures
1. **Enable vault storage** for all production operations
2. **Regular cleanup** of old data to maintain performance
3. **Monitor vault storage** usage and permissions

### Security Practices
1. **Restrict system folder access** to automation users only
2. **Regular permission audits** of vault storage folders
3. **Secure backup procedures** for exported data

### Performance Optimization
1. **Use appropriate retention periods** for cleanup
2. **Monitor vault storage performance** during large operations
3. **Consider local storage** for development environments

## API Reference

### VaultStorageAdapter Methods

#### Core Storage Operations
- `store_log_entry(log_entry: LogEntry) -> str`
- `store_checkpoint(checkpoint: Checkpoint) -> str`
- `store_configuration(config: ConfigRecord, name: str) -> str`
- `store_operation_report(report_data: Dict, run_id: str) -> str`
- `store_csv_template(template_data: str, name: str) -> str`

#### Data Retrieval
- `load_configuration(name: str) -> Optional[ConfigRecord]`
- `load_checkpoint(run_id: str) -> Optional[Checkpoint]`
- `get_daily_logs(date: datetime) -> List[LogEntry]`

#### Management Operations
- `list_checkpoints(date_range: Optional[tuple]) -> List[Dict]`
- `cleanup_old_data(retention_days: int) -> Dict[str, int]`
- `export_system_data(date_range: Optional[tuple]) -> Dict[str, Any]`

## Future Enhancements

### Planned Features
1. **Real-time synchronization** between multiple automation instances
2. **Advanced search and filtering** for vault-stored data
3. **Automated retention policies** with configurable rules
4. **Integration with Keeper reporting** for compliance dashboards

### Extensibility
The vault storage system is designed for extensibility:
- Plugin architecture for custom storage adapters
- Configurable data schemas for different use cases
- Integration points for external monitoring systems

## Support

For issues related to vault storage functionality:

1. **Check troubleshooting section** for common issues
2. **Enable verbose logging** for detailed error information
3. **Verify Keeper connectivity** and permissions
4. **Review vault folder structure** for data integrity

The vault storage integration provides enterprise-grade data management while maintaining the simplicity and reliability of the core automation system. 