# Keeper Permissions Automation

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enterprise-grade bulk permissions management for Keeper vaults using CSV workflows with per-team folder isolation.**

This system automates the provisioning of Keeper record permissions to teams through a clean CSV-based interface. It creates **per-team mirrored folder structures** ensuring perfect team isolation and granular permissions without duplicating data.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure and authenticate
python cli.py configure

# Generate CSV template with team-specific columns
python cli.py template --out permissions.csv

# Validate your CSV
python cli.py validate permissions.csv

# Preview changes (dry run)
python cli.py dry-run permissions.csv

# Apply permissions
python cli.py apply permissions.csv --force
```

## 📋 Table of Contents

- [Features](#-features)
- [Per-Team Architecture](#-per-team-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [CSV Schema](#-csv-schema)
- [Examples](#-examples)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)
- [Development](#-development)

## ✨ Features

### **Core Capabilities**
- 🔄 **Bulk Permission Management** - Update hundreds of records with single CSV
- 📊 **CSV-Based Workflow** - Familiar spreadsheet interface for permissions
- 🏗️ **Per-Team Folder Isolation** - Each team gets their own mirrored folder structure
- 🔒 **Granular Permissions** - 5-level permission system (ro, rw, rws, mgr, admin)
- 🎯 **Idempotent Operations** - Safe to run multiple times with same results
- 📈 **Enterprise Scale** - Handles thousands of records and teams

### **Per-Team Architecture Benefits**
- 🔐 **Perfect Team Isolation** - Teams can only access their own folder structure
- 📁 **Complete Folder Mirroring** - Each team gets the full organizational hierarchy
- ✅ **Keeper-Compliant** - Follows Keeper's permission model correctly
- 🚀 **Scalable** - Works with any number of teams
- 🎯 **Granular Control** - Different teams can have different permissions on same record

### **Enterprise Features**
- 🔐 **SSO Integration** - Works with enterprise Single Sign-On
- 📋 **Interactive Mode** - Authenticate once, run multiple commands
- 🧪 **Dry Run Mode** - Preview changes before applying
- 📝 **Comprehensive Logging** - Structured logs with full audit trail
- 🏁 **Checkpoint Recovery** - Resume operations after interruptions
- ✅ **Advanced Validation** - Detects duplicates, invalid permissions, missing records

### **Developer Features**
- ⚛️ **Atomic Architecture** - Clean separation of concerns
- 🧪 **100% Test Coverage** - Comprehensive test suite
- 📚 **Type Safety** - Full type annotations with mypy compliance
- 🔌 **Pluggable Adapters** - Mock implementations for testing
- 📖 **Comprehensive Documentation** - Detailed API and usage docs

## 🏗️ Per-Team Architecture

The system implements a **per-team folder structure** that creates isolated, mirrored folder hierarchies for each team:

### **Folder Structure**
```
[Perms] (private root folder)
├── TeamA (shared folder) ← Team A has access
│   └── Clients/Client1/Development/Servers (private subfolders)
│       └── Records shared with Team A permissions
├── TeamB (shared folder) ← Team B has access  
│   └── Clients/Client1/Development/Servers (private subfolders)
│       └── Records shared with Team B permissions
└── TeamC (shared folder) ← Team C has access
    └── Clients/Client2/Production/Database (private subfolders)
        └── Records shared with Team C permissions
```

### **Key Benefits**
1. **Perfect Team Isolation**: Each team can only access their own folder structure
2. **Scalable**: Works with any number of teams
3. **Keeper-Compliant**: Follows Keeper's permission model correctly
4. **Complete Mirroring**: Each team gets the full organizational folder hierarchy
5. **Granular Permissions**: Different teams can have different permission levels on the same record

### **How It Works**
1. **CSV Processing**: Each row specifies which teams get access to which records
2. **Folder Creation**: Creates team-specific shared folders under `[Perms]`
3. **Record Sharing**: Shares records to appropriate team folders with specified permissions
4. **Team Permissions**: Applies team permissions to their shared folders

## 📦 Installation

### **Prerequisites**
- Python 3.9 or later
- Keeper Commander access (installed automatically)
- Valid Keeper vault credentials

### **Setup**

1. **Clone and Navigate**
```bash
git clone <repository-url>
cd keeper-perms-automation
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Verify Installation**
```bash
python cli.py --help
```

### **Authentication Setup**

The tool integrates with Keeper Commander's authentication system:

- **SSO Users**: Follow browser-based SSO flow
- **Master Password**: Standard Keeper login
- **Device Tokens**: Automatically managed and cached

Authentication is handled transparently - you'll be prompted when needed.

## ⚙️ Configuration

### **Automatic Configuration**

The system uses intelligent defaults and automatically detects:
- Vault structure and teams
- Permission mappings
- Folder hierarchies

### **Advanced Configuration**

Create a `Perms-Config` record in your vault for advanced control:

```json
{
  "root_folder_name": "[Perms]",
  "included_teams": ["team-uid-1", "team-uid-2"],
  "included_folders": null,
  "excluded_folders": ["folder-uid-to-skip"]
}
```

**Configuration Fields:**
- `root_folder_name`: Root folder for permission mirrors (default: `[Perms]`)
- `included_teams`: Specific teams to include (null = all teams)
- `included_folders`: Specific folders to process (null = all folders)
- `excluded_folders`: Folders to skip during processing

## 📘 Usage Guide

### **Interactive Mode (Recommended)**

For multiple operations, use interactive mode to authenticate once:

```bash
python cli.py interactive
```

**Interactive Commands:**
```
keeper> status                    # Show vault summary
keeper> template perms.csv        # Generate CSV template
keeper> validate perms.csv        # Validate CSV structure
keeper> dry-run perms.csv         # Preview changes
keeper> apply perms.csv           # Apply permissions
keeper> help                      # Show available commands
keeper> quit                      # Exit interactive mode
```

### **Single Command Mode**

For scripting or one-off operations:

```bash
# Check vault connection
python cli.py status

# Generate permission template
python cli.py template --output my_permissions.csv

# Validate CSV file
python cli.py validate my_permissions.csv

# Preview changes (dry run)
python cli.py dry-run my_permissions.csv

# Apply permissions (requires --force flag)
python cli.py apply my_permissions.csv --force
```

### **Command Reference**

| Command | Description | Options |
|---------|-------------|---------|
| `status` | Check vault connectivity and show summary | - |
| `template` | Generate CSV template with current vault data | `-o, --output` |
| `validate` | Validate CSV structure and permissions | `--max-records` |
| `dry-run` | Preview changes without applying | `--max-records` |
| `apply` | Apply permissions to vault | `--force`, `--max-records` |
| `configure` | View or create configuration | `--create`, `--root-folder` |
| `interactive` | Start interactive session | - |

### **Safety Features**

- **--max-records**: Limits operation size (default: 5000)
- **--force**: Required for destructive operations
- **Dry run**: Always preview changes first
- **Validation**: Automatic CSV validation before operations
- **Checkpoints**: Automatic progress tracking and recovery

## 📊 CSV Schema

### **Required Columns**

| Column | Description | Example |
|--------|-------------|---------|
| `record_uid` | Unique identifier of the Keeper record | `VXLhlwc06wnXzsLm-G7jFA` |
| `title` | Record title (for validation) | `Database Credentials` |
| `folder_path` | Target folder path in vault | `[Perms]/Finance/Database` |

### **Team Permission Columns**

One column per team in your vault, with permission levels:

| Permission | Access Level | Description |
|------------|--------------|-------------|
| `ro` | Read Only | View record only |
| `rw` | Read/Write | View and edit record |
| `rws` | Read/Write/Share | View, edit, and share record |
| `mgr` | Manager | Manage records in folder |
| `admin` | Administrator | Full administrative access |
| *(empty)* | No Access | Team has no access to record |

### **Example CSV**

```csv
record_uid,title,folder_path,Engineering Team,Finance Team,HR Team
VXLhlwc06wnXzsLm-G7jFA,Database Prod,[Perms]/Engineering/Database,admin,ro,
EuBQia1i-bQAfQajIlzTyA,Payroll System,[Perms]/Finance/Payroll,,admin,rw
ja3SF9YHBdrKVSavN4tQlw,Benefits Portal,[Perms]/HR/Benefits,,rw,admin
```

This grants:
- Engineering Team: Admin access to Database Prod
- Finance Team: Read-only access to Database Prod, Admin access to Payroll
- HR Team: Read/write access to Payroll, Admin access to Benefits Portal

## 📚 Examples

### **Basic Workflow**

1. **Generate Template**
```bash
python cli.py template permissions.csv
```

2. **Edit CSV** (in Excel, Google Sheets, etc.)
   - Set permission levels for each team/record combination
   - Use: `ro`, `rw`, `rws`, `mgr`, `admin`, or leave blank

3. **Validate Changes**
```bash
python cli.py validate permissions.csv
```

4. **Preview Impact**
```bash
python cli.py dry-run permissions.csv
```

5. **Apply Permissions**
```bash
python cli.py apply permissions.csv --force
```

### **Enterprise Workflow**

For large organizations with complex permission structures:

```bash
# Start interactive session
python cli.py interactive

# In interactive mode:
keeper> status
✅ Connected: 847 records, 23 teams

keeper> template enterprise_perms.csv
✅ Template generated with 847 records and 23 team columns

# Edit CSV with your preferred tool
# Then validate and apply:

keeper> validate enterprise_perms.csv  
✅ Validation passed: 847 rows, 0 errors, 2 warnings

keeper> dry-run enterprise_perms.csv
📋 Preview: 234 records will be updated, 613 unchanged

keeper> apply enterprise_perms.csv
🚀 Applying 847 operations...
✅ Complete: 847 operations succeeded, 0 failed
```

### **Advanced Configuration**

```bash
# Create custom configuration
python cli.py configure --create --root-folder "[CompanyPerms]"

# Use specific configuration
python cli.py template --config <config-record-uid> perms.csv
```

## 🔌 API Reference

### **Application Coordinator**

```python
from keeper_auto.application.services import ApplicationCoordinator

# Initialize coordinator
coordinator = ApplicationCoordinator()
coordinator.initialize()

# Validate CSV
report = coordinator.validate_csv(Path("permissions.csv"))
print(f"Valid: {report.is_valid}, Errors: {report.error_count}")

# Generate template
success = coordinator.generate_template(Path("template.csv"))

# Apply changes
result = coordinator.apply_changes(Path("permissions.csv"), force=True)
```

### **Atomic Services**

```python
from keeper_auto.application.services import (
    AtomicValidationService,
    AtomicTemplateService,
    AtomicProvisioningService
)

# Direct service usage
validator = AtomicValidationService()
report = validator.validate_csv(Path("data.csv"))

# Template generation
template_service = AtomicTemplateService(vault_data, config)
template_service.generate_template(Path("output.csv"))
```

### **Domain Models**

```python
from keeper_auto.domain.models import (
    ConfigRecord,
    VaultData,
    Team,
    Record,
    PermissionLevel
)

# Create domain objects
config = ConfigRecord(root_folder_name="[Perms]")
team = Team.create("team-uid", "Engineering")
permission = PermissionLevel.READ_WRITE
```

## 🔧 Troubleshooting

### **Common Issues**

**Authentication Problems**
```bash
# Clear cached credentials
rm ~/.keeper/config.json  # macOS/Linux
del %USERPROFILE%\.keeper\config.json  # Windows

# Try authentication again
python cli.py status
```

**CSV Format Errors**
```bash
# Get detailed validation errors
python cli.py validate problematic.csv

# Common issues:
# - Missing required columns (record_uid, title, folder_path)
# - Invalid permission levels (use: ro, rw, rws, mgr, admin)
# - Duplicate record_uid values
# - Invalid folder paths
```

**Performance Issues**
```bash
# Limit operation size
python cli.py apply large_file.csv --max-records 1000

# Use dry-run to estimate impact
python cli.py dry-run large_file.csv
```

**Connection Issues**
```bash
# Test basic connectivity
python cli.py status

# Check Keeper Commander installation
pip install --upgrade keepercommander
```

### **Debug Mode**

Enable detailed logging for troubleshooting:

```bash
# Set environment variable
export KEEPER_DEBUG=1  # Linux/macOS
set KEEPER_DEBUG=1     # Windows

# Run commands with debug output
python cli.py status
```

### **Error Codes**

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | Validation error or operation failed |
| 2 | Authentication error |
| 3 | Configuration error |
| 4 | File not found or permission denied |

## 👥 Development

### **Setup Development Environment**

```bash
# Clone repository
git clone <repository-url>
cd keeper-perms-automation

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
python -m pytest tests/

# Run linting
python -m pylint keeper_auto/
python -m mypy keeper_auto/
```

### **Architecture Principles**

1. **Atomic Design** - Each component has single responsibility
2. **Clean Architecture** - Clear layer separation
3. **Test-Driven Development** - Comprehensive test coverage
4. **Type Safety** - Full type annotations
5. **Idempotent Operations** - Safe to run multiple times

### **Contributing Guidelines**

1. **Fork and Branch** - Create feature branches from `main`
2. **Write Tests** - Maintain 100% test coverage
3. **Follow Style** - Use Black, isort, and pylint
4. **Document Changes** - Update README and docstrings
5. **Submit PR** - Include clear description and tests

### **Testing**

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=keeper_auto

# Run specific test categories
python -m pytest tests/test_atomic_services.py
python -m pytest tests/test_integration.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Documentation**: [Full API documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/keeper-perms-automation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/keeper-perms-automation/discussions)

## 🏆 Acknowledgments

- Built on [Keeper Commander SDK](https://github.com/Keeper-Security/Commander)
- Inspired by enterprise IAM best practices
- Designed for DevOps and security teams

---

**Made with ❤️ for enterprise security teams**
