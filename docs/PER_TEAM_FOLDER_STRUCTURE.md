# Per-Team Folder Structure Implementation

## Overview

The Keeper Permissions Automation tool now implements a **per-team folder structure** that creates isolated, mirrored folder hierarchies for each team. This approach solves the fundamental limitation where teams can only be added to shared folders, not private folders.

## Architecture

### Before (Broken)
```
[Perms] (private)
└── Clients (shared)
    ├── Client1 (private) ❌ Can't add teams here
    ├── Client2 (private) ❌ Can't add teams here  
    └── Client4 (private) ❌ Can't add teams here
```

### After (Working)
```
[Perms] (private)
├── Admin Team (shared) ✅ Team permissions work
│   └── Clients/Client1/Development/Servers (private subfolders)
├── test (shared) ✅ Team permissions work  
│   └── Clients/Client1/Development/Servers (private subfolders)
│   └── Clients/Client4/Cloud/AWS (private subfolders)
└── Switzerland IPallow (shared) ✅ Team permissions work
    └── Clients/Client4/Cloud/AWS (private subfolders)
```

## Key Benefits

1. **Perfect Team Isolation**: Each team can only access their own folder structure
2. **Scalable**: Works with any number of teams
3. **Keeper-Compliant**: Follows Keeper's permission model correctly
4. **Complete Mirroring**: Each team gets the full organizational folder hierarchy
5. **Granular Permissions**: Different teams can have different permission levels on the same record

## Implementation Details

### Folder Creation Logic

The `ensure_team_folder_path()` function implements the per-team structure:

1. **Root Folder**: Creates `[Perms]` as a private user folder
2. **Team Folders**: Creates `TeamName` as shared folders under `[Perms]`
3. **Subfolders**: Creates the complete `folder_path` as private subfolders under each team's shared folder
4. **Record Sharing**: Shares records to the deepest folder in each team's hierarchy
5. **Team Permissions**: Applies team permissions to the team's shared folder

### CSV Processing

Each row in the CSV is processed as follows:

```csv
record_uid,title,folder_path,TeamA (uid),TeamB (uid),TeamC (uid)
abc123,Server1,Clients/Client1/Servers,rw,ro,
```

Results in:
- `[Perms]/TeamA/Clients/Client1/Servers` ← Server1 shared with RW permissions
- `[Perms]/TeamB/Clients/Client1/Servers` ← Server1 shared with RO permissions  
- TeamC gets no access (blank cell)

### Permission Mapping

| CSV Value | can_edit | can_share | manage_records | manage_users |
|-----------|----------|-----------|----------------|--------------|
| `ro`      | ✗        | ✗         | ✗              | ✗            |
| `rw`      | ✓        | ✗         | ✗              | ✗            |
| `rws`     | ✓        | ✓         | ✗              | ✗            |
| `mgr`     | ✓        | ✓         | ✓              | ✗            |
| `admin`   | ✓        | ✓         | ✓              | ✓            |

## Code Changes

### New Functions

- `ensure_team_folder_path()`: Creates per-team folder structures
- Updated `apply_changes()`: Processes each team separately
- Updated `dry_run()`: Shows per-team operations

### Removed Functions

- `ensure_folder_path()`: Replaced with per-team logic

## Testing

The implementation has been thoroughly tested:

1. **Template Generation**: Creates CSV with proper team columns
2. **Validation**: Validates CSV structure and permissions
3. **Dry Run**: Shows clear per-team operations
4. **Apply**: Successfully creates folder structures and shares records
5. **Vault Verification**: Confirmed correct folder structure in vault

## Usage Examples

### Generate Template
```bash
python cli.py template --out template.csv
```

### Validate CSV
```bash
python cli.py validate permissions.csv
```

### Preview Changes
```bash
python cli.py dry-run permissions.csv
```

### Apply Changes
```bash
python cli.py apply permissions.csv --force
```

## Troubleshooting

### Common Issues

1. **Team Not Found**: Ensure team names in CSV headers match exactly
2. **Permission Errors**: Use valid permission tokens (`ro`, `rw`, `rws`, `mgr`, `admin`)
3. **Folder Creation Fails**: Check Keeper permissions and authentication

### Debug Commands

```bash
# Check vault structure
python -c "from keeper_auto.keeper_client import get_client; sdk = get_client(); print('Shared folders:', len(sdk.shared_folder_cache))"

# List teams
python -c "from keeper_auto.keeper_client import get_teams; print([t['team_name'] for t in get_teams()])"
```

## Migration from Old Structure

If you have an existing vault with the old structure, the tool will create the new per-team structure alongside it. The old structure can be manually cleaned up after verifying the new structure works correctly.

## Future Enhancements

1. **Rollback Capability**: Ability to reverse applied changes
2. **Bulk Operations**: Process multiple CSV files
3. **Audit Trail**: Enhanced logging and change tracking
4. **UI Integration**: Web interface for non-technical users 