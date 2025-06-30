from typer.testing import CliRunner
from unittest.mock import patch
import tempfile

from cli import app
from keeper_auto.models import OperationResult, ConfigRecord, VaultData, ValidationResult

runner = CliRunner()


def test_app_runs():
    """Test that the CLI runs without crashing."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage: keeper-perms" in result.stdout


def test_template_command_success():
    """Test template command with successful execution."""
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        tmp_path = tmp.name
    
    mock_vault_data = VaultData()
    mock_vault_data.add_team("team1", "Team One")
    mock_vault_data.add_record("record1", "Record One", "/path1")
    
    with patch('cli.VaultService') as mock_vault_service, \
         patch('cli.TemplateService') as mock_template_service, \
         patch('cli.ConfigService') as mock_config_service:
        
        # Setup mocks
        mock_vault_service.return_value.load_vault_data.return_value = mock_vault_data
        mock_config_service.return_value.load_configuration.return_value = OperationResult(
            success=True, message="Config loaded", data=ConfigRecord()
        )
        mock_template_service.return_value.generate_template.return_value = OperationResult(
            success=True, message="Template generated successfully"
        )
        
        result = runner.invoke(app, ["template", tmp_path])
        assert result.exit_code == 0
        assert "Template generated successfully" in result.stdout


def test_validate_command_success():
    """Test validate command with successful validation."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("record_uid,title,folder_path\nuid1,Title1,/path1")
        tmp_path = tmp.name
    
    with patch('cli.ValidationService') as mock_validation_service:
        mock_validation_service.return_value.validate_csv_file.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[], metadata={}
        )
        
        result = runner.invoke(app, ["validate", tmp_path])
        assert result.exit_code == 0
        assert "✓ CSV validation passed" in result.stdout


def test_validate_command_with_errors():
    """Test validate command with validation errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("invalid,csv,format")
        tmp_path = tmp.name
    
    with patch('cli.ValidationService') as mock_validation_service:
        mock_validation_service.return_value.validate_csv_file.return_value = ValidationResult(
            is_valid=False, 
            errors=["Missing required headers"], 
            warnings=["Large file warning"],
            metadata={}
        )
        
        result = runner.invoke(app, ["validate", tmp_path])
        assert result.exit_code == 1
        assert "✗ CSV validation failed" in result.stdout
        assert "Missing required headers" in result.stdout
        assert "Large file warning" in result.stdout


def test_dry_run_command_success():
    """Test dry-run command with successful execution."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("record_uid,title,folder_path\nuid1,Title1,/path1")
        tmp_path = tmp.name
    
    with patch('cli.ProvisioningService') as mock_provisioning_service, \
         patch('cli.ConfigService') as mock_config_service:
        
        mock_config_service.return_value.load_configuration.return_value = OperationResult(
            success=True, message="Config loaded", data=ConfigRecord()
        )
        mock_provisioning_service.return_value.dry_run.return_value = OperationResult(
            success=True, 
            message="Dry run completed successfully",
            data={"operations": ["Create folder: /Test", "Share record: Title1"]}
        )
        
        result = runner.invoke(app, ["dry-run", tmp_path])
        assert result.exit_code == 0
        assert "Dry run completed successfully" in result.stdout
        assert "Create folder: /Test" in result.stdout


def test_apply_command_success():
    """Test apply command with successful execution."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("record_uid,title,folder_path\nuid1,Title1,/path1")
        tmp_path = tmp.name
    
    with patch('cli.ProvisioningService') as mock_provisioning_service, \
         patch('cli.ConfigService') as mock_config_service:
        
        mock_config_service.return_value.load_configuration.return_value = OperationResult(
            success=True, message="Config loaded", data=ConfigRecord()
        )
        mock_provisioning_service.return_value.apply_changes.return_value = OperationResult(
            success=True,
            message="Apply completed successfully", 
            data={"operations": ["Created folder: /Test", "Shared record: Title1"]}
        )
        
        result = runner.invoke(app, ["apply", tmp_path])
        assert result.exit_code == 0
        assert "Apply completed successfully" in result.stdout
        assert "Created folder: /Test" in result.stdout


def test_apply_command_with_errors():
    """Test apply command with errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("record_uid,title,folder_path\nuid1,Title1,/path1")
        tmp_path = tmp.name
    
    with patch('cli.ProvisioningService') as mock_provisioning_service, \
         patch('cli.ConfigService') as mock_config_service:
        
        mock_config_service.return_value.load_configuration.return_value = OperationResult(
            success=True, message="Config loaded", data=ConfigRecord()
        )
        mock_provisioning_service.return_value.apply_changes.return_value = OperationResult(
            success=False,
            message="Apply failed",
            errors=["Team not found", "Folder creation failed"],
            data={"operations": ["Some operation succeeded"]}
        )
        
        result = runner.invoke(app, ["apply", tmp_path])
        assert result.exit_code == 1
        assert "Apply failed" in result.stdout
        assert "Team not found" in result.stdout
        assert "Some operation succeeded" in result.stdout


def test_config_loading_failure():
    """Test behavior when config loading fails."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("record_uid,title,folder_path\nuid1,Title1,/path1")
        tmp_path = tmp.name
    
    with patch('cli.ConfigService') as mock_config_service:
        mock_config_service.return_value.load_configuration.return_value = OperationResult(
            success=False,
            message="Config loading failed",
            errors=["Invalid JSON in config"]
        )
        
        result = runner.invoke(app, ["dry-run", tmp_path])
        assert result.exit_code == 1
        assert "Config loading failed" in result.stdout
        assert "Invalid JSON in config" in result.stdout


def test_file_not_found():
    """Test behavior when CSV file doesn't exist."""
    result = runner.invoke(app, ["validate", "nonexistent.csv"])
    assert result.exit_code != 0 