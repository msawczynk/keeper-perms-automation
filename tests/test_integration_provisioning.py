import uuid
import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from keeper_auto.keeper_client import find_folder_by_name, get_records, get_teams
from keeper_auto.models import ConfigRecord, VaultData, ValidationResult, OperationResult, CSVTemplate
from keeper_auto.services import ProvisioningService, VaultService, ConfigService, TemplateService, ValidationService
from keeper_auto.exceptions import (
    APIError, AuthenticationError, ConfigurationError, ValidationError, 
    OperationError, DataError, NetworkError, PermissionError
)


@pytest.fixture(scope="module")
def live_vault_data():
    """Fixture to get live, uncached data from the vault once per module."""
    vault_service = VaultService()
    return vault_service.load_vault_data(force_reload=True)


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return [
        {
            "record_uid": "UID1",
            "title": "Test Record 1",
            "folder_path": "Test/Folder",
            "Team Alpha_can_edit": "true",
            "Team Alpha_can_share": "false",
            "Team Beta_manage_records": "true",
            "Team Beta_manage_users": "false"
        },
        {
            "record_uid": "UID2", 
            "title": "Test Record 2",
            "folder_path": "Another/Path",
            "Team Gamma": "ro"
        }
    ]


# Exception tests
def test_api_error():
    """Test APIError exception."""
    error = APIError("Test API error")
    assert str(error) == "Test API error"
    assert error.error_code is None
    
    error_with_code = APIError("Test error", error_code="E001")
    assert error_with_code.error_code == "E001"


def test_authentication_error():
    """Test AuthenticationError exception."""
    error = AuthenticationError("Auth failed")
    assert str(error) == "Auth failed"


def test_configuration_error():
    """Test ConfigurationError exception."""
    error = ConfigurationError("Config invalid")
    assert str(error) == "Config invalid"


def test_validation_error():
    """Test ValidationError exception."""
    error = ValidationError("Validation failed")
    assert str(error) == "Validation failed"


def test_operation_error():
    """Test OperationError exception."""
    error = OperationError("Operation failed")
    assert str(error) == "Operation failed"


def test_data_error():
    """Test DataError exception."""
    error = DataError("Data corrupted")
    assert str(error) == "Data corrupted"


def test_network_error():
    """Test NetworkError exception."""
    error = NetworkError("Network timeout")
    assert str(error) == "Network timeout"


def test_permission_error():
    """Test PermissionError exception."""
    error = PermissionError("Access denied")
    assert str(error) == "Access denied"


# Models tests
def test_vault_data_model():
    """Test VaultData model methods."""
    vault_data = VaultData()
    
    # Test initial state
    assert not vault_data.is_loaded()
    assert vault_data.summary() == {"teams": 0, "folders": 0, "records": 0}
    
    # Test adding data
    vault_data.add_team("team1", "Team One")
    vault_data.add_folder("folder1", "Folder One", None)
    vault_data.add_record("record1", "Record One", "/path")
    
    assert len(vault_data.teams_by_uid) == 1
    assert len(vault_data.folders_by_uid) == 1
    assert len(vault_data.records_by_uid) == 1
    
    # Test finding methods
    team = vault_data.get_team_by_uid("team1")
    assert team is not None
    assert team.name == "Team One"
    
    folder = vault_data.find_folder_by_uid("folder1")
    assert folder is not None
    assert folder.name == "Folder One"
    
    record = vault_data.get_record_by_uid("record1")
    assert record is not None
    assert record.title == "Record One"
    
    # Test clear
    vault_data.clear()
    assert len(vault_data.teams_by_uid) == 0
    assert len(vault_data.folders_by_uid) == 0
    assert len(vault_data.records_by_uid) == 0
    
    # Test mark loaded
    vault_data.mark_loaded()
    assert vault_data.is_loaded()


def test_validation_result_model():
    """Test ValidationResult model methods."""
    result = ValidationResult()
    
    # Test initial state
    assert result.is_valid
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    
    # Test adding errors and warnings
    result.add_error("Test error")
    result.add_warning("Test warning")
    
    assert not result.is_valid
    assert "Test error" in result.errors
    assert "Test warning" in result.warnings


def test_operation_result_model():
    """Test OperationResult model methods."""
    # Test success result
    result = OperationResult(success=True, message="Success")
    assert result.success
    assert result.message == "Success"
    assert len(result.errors) == 0
    
    # Test failure result
    result = OperationResult(
        success=False, 
        message="Failed", 
        errors=["Error 1"], 
        warnings=["Warning 1"],
        data={"key": "value"}
    )
    assert not result.success
    assert result.message == "Failed"
    assert "Error 1" in result.errors
    assert "Warning 1" in result.warnings
    assert result.data["key"] == "value"


def test_csv_template_model():
    """Test CSVTemplate model methods."""
    template = CSVTemplate()
    
    # Test initial state
    assert len(template.headers) == 3  # record_uid, title, folder_path
    assert len(template.rows) == 0
    
    # Test adding row
    template.add_row("uid1", "Title 1", "/path1", {"Team1": "ro"})
    assert len(template.rows) == 1
    assert template.rows[0]["record_uid"] == "uid1"
    assert template.rows[0]["Team1"] == "ro"


def test_config_record_model():
    """Test ConfigRecord model."""
    # Test default config
    config = ConfigRecord()
    assert config.root_folder_name == "[Perms]"
    assert config.included_teams is None
    assert config.included_folders is None
    assert config.excluded_folders == []
    
    # Test custom config
    config = ConfigRecord(
        root_folder_name="[Custom]",
        included_teams=["team1"],
        included_folders=["folder1"],
        excluded_folders=["folder2"]
    )
    assert config.root_folder_name == "[Custom]"
    assert config.included_teams == ["team1"]
    assert config.included_folders == ["folder1"]
    assert config.excluded_folders == ["folder2"]


# Services tests
def test_config_service_no_config_record():
    """Test ConfigService when no config record exists."""
    service = ConfigService()
    
    with patch('keeper_auto.services.get_records', return_value=[]):
        result = service.load_configuration()
        assert result.success
        assert "not found" in result.message
        assert isinstance(result.data, ConfigRecord)
        assert len(result.warnings) == 1


def test_config_service_with_valid_config():
    """Test ConfigService with valid JSON config."""
    service = ConfigService()
    
    # Mock record with JSON config
    mock_field = Mock()
    mock_field.type = 'json'
    mock_field.value = '{"root_folder_name": "[Test]", "included_teams": ["team1"]}'
    
    mock_record = Mock()
    mock_record.data = [mock_field]
    
    with patch('keeper_auto.services.get_record', return_value=mock_record):
        result = service.load_configuration("test_uid")
        assert result.success
        assert result.data.root_folder_name == "[Test]"
        assert result.data.included_teams == ["team1"]


def test_config_service_invalid_json():
    """Test ConfigService with invalid JSON config."""
    service = ConfigService()
    
    # Mock record with invalid JSON
    mock_field = Mock()
    mock_field.type = 'json'
    mock_field.value = 'invalid json'
    
    mock_record = Mock()
    mock_record.data = [mock_field]
    
    with patch('keeper_auto.services.get_record', return_value=mock_record):
        result = service.load_configuration("test_uid")
        assert not result.success
        assert "Failed to parse" in result.message
        assert len(result.errors) == 1


def test_vault_service_build_folder_path():
    """Test VaultService _build_folder_path method."""
    service = VaultService()
    
    # Add test folders to vault data
    service.vault_data.add_folder("root", "Root", None)
    service.vault_data.add_folder("child", "Child", "root")
    service.vault_data.add_folder("grandchild", "Grandchild", "child")
    
    # Test path building
    path = service._build_folder_path("grandchild")
    assert path == "/Root/Child/Grandchild"
    
    path = service._build_folder_path("child")
    assert path == "/Root/Child"
    
    path = service._build_folder_path("root")
    assert path == "/Root"
    
    path = service._build_folder_path(None)
    assert path == ""
    
    path = service._build_folder_path("nonexistent")
    assert path == ""


def test_vault_service_get_vault_summary():
    """Test VaultService get_vault_summary method."""
    service = VaultService()
    
    with patch.object(service, 'load_vault_data'):
        service.vault_data.add_team("team1", "Team One")
        service.vault_data.add_folder("folder1", "Folder One", None)
        service.vault_data.add_record("record1", "Record One", "/path")
        service.vault_data.mark_loaded()
        
        summary = service.get_vault_summary()
        assert summary["teams"] == 1
        assert summary["folders"] == 1
        assert summary["records"] == 1


def test_template_service_no_teams():
    """Test TemplateService when no teams are available."""
    vault_service = VaultService()
    service = TemplateService(vault_service)
    
    vault_data = VaultData()
    # Don't add any teams
    
    result = service.generate_template(vault_data, Path("test.csv"))
    assert not result.success
    assert "No teams found" in result.message


def test_template_service_generate_template(tmp_path):
    """Test TemplateService template generation."""
    vault_service = VaultService()
    service = TemplateService(vault_service)
    
    # Setup test data
    vault_data = VaultData()
    vault_data.add_team("team1", "Team One")
    vault_data.add_team("team2", "Team Two")
    vault_data.add_record("record1", "Record One", "/Test/Path")
    vault_data.add_record("record2", "Record Two", "/Another/Path")
    
    output_path = tmp_path / "template.csv"
    result = service.generate_template(vault_data, output_path)
    
    assert result.success
    assert output_path.exists()
    
    # Verify CSV content
    with open(output_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)
    
    assert "record_uid" in headers
    assert "title" in headers
    assert "folder_path" in headers
    assert "Team One" in headers
    assert "Team Two" in headers
    assert len(rows) == 2


def test_provisioning_service_get_changes_from_csv(tmp_path, sample_csv_data):
    """Test ProvisioningService _get_changes_from_csv method."""
    service = ProvisioningService(VaultService())
    
    # Create test CSV
    csv_file = tmp_path / "test.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_csv_data)
    
    changes = service._get_changes_from_csv(csv_file)
    assert len(changes) == 2
    assert changes[0]["record_uid"] == "UID1"
    assert changes[1]["record_uid"] == "UID2"


def test_provisioning_service_get_target_folder_path():
    """Test ProvisioningService _get_target_folder_path method."""
    service = ProvisioningService(VaultService())
    config = ConfigRecord(root_folder_name="[Root]")
    
    # Test with folder path
    row = {"folder_path": "Test/Path"}
    path = service._get_target_folder_path(config, row)
    assert path == "[Root]/Test/Path"
    
    # Test without folder path
    row = {"folder_path": ""}
    path = service._get_target_folder_path(config, row)
    assert path == "[Root]"
    
    # Test with None folder path
    row = {}
    path = service._get_target_folder_path(config, row)
    assert path == "[Root]"


def test_provisioning_service_extract_team_permissions():
    """Test ProvisioningService _extract_team_permissions method."""
    service = ProvisioningService(VaultService())
    
    row = {
        "record_uid": "UID1",
        "title": "Test",
        "Team_Alpha_can_edit": "true",
        "Team_Alpha_can_share": "false",
        "Team_Beta_manage_records": "true",
        "Team_Beta_manage_users": "false",
        "Other_Column": "ignore"
    }
    
    perms = service._extract_team_permissions(row)
    assert "Team_Alpha" in perms
    assert perms["Team_Alpha"]["can_edit"] == True
    assert perms["Team_Alpha"]["can_share"] == False
    assert "Team_Beta" in perms
    assert perms["Team_Beta"]["manage_records"] == True
    assert perms["Team_Beta"]["manage_users"] == False


def test_provisioning_service_dry_run(tmp_path, sample_csv_data):
    """Test ProvisioningService dry_run method."""
    service = ProvisioningService(VaultService())
    
    # Create test CSV
    csv_file = tmp_path / "test.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_csv_data)
    
    config = ConfigRecord()
    result = service.dry_run(csv_file, config)
    
    assert result.success
    assert "Dry run completed" in result.message
    assert "operations" in result.data


def test_validation_service_file_not_found():
    """Test ValidationService with non-existent file."""
    service = ValidationService()
    result = service.validate_csv_file(Path("nonexistent.csv"))
    
    assert not result.is_valid
    assert "not found" in result.errors[0]


def test_validation_service_empty_file(tmp_path):
    """Test ValidationService with empty CSV file."""
    service = ValidationService()
    
    # Create empty CSV
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")
    
    result = service.validate_csv_file(csv_file)
    assert not result.is_valid
    assert "no headers" in result.errors[0]


def test_validation_service_missing_headers(tmp_path):
    """Test ValidationService with missing required headers."""
    service = ValidationService()
    
    # Create CSV with missing headers
    csv_file = tmp_path / "missing_headers.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["record_uid", "title"])  # Missing folder_path
        writer.writerow(["uid1", "Title 1"])
    
    result = service.validate_csv_file(csv_file)
    assert not result.is_valid
    assert "Missing required headers" in result.errors[0]


def test_validation_service_invalid_permissions(tmp_path):
    """Test ValidationService with invalid permission values."""
    service = ValidationService()
    
    # Create CSV with invalid permission values
    csv_file = tmp_path / "invalid_perms.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path", "Team1"])
        writer.writeheader()
        writer.writerow({
            "record_uid": "uid1",
            "title": "Title 1", 
            "folder_path": "/path",
            "Team1": "invalid"
        })
    
    result = service.validate_csv_file(csv_file)
    assert not result.is_valid
    assert "Invalid permission value" in result.errors[0]


def test_validation_service_with_vault_data(tmp_path):
    """Test ValidationService with vault data for drift detection."""
    service = ValidationService()
    
    # Setup vault data
    vault_data = VaultData()
    vault_data.add_team("team1", "Team One")
    vault_data.add_record("uid1", "Correct Title", "/correct/path")
    
    # Create CSV with data drift
    csv_file = tmp_path / "drift_test.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path", "Team One", "Unknown Team"])
        writer.writeheader()
        writer.writerow({
            "record_uid": "uid1",
            "title": "Wrong Title",  # Title drift
            "folder_path": "/wrong/path",  # Path drift
            "Team One": "ro",
            "Unknown Team": "rw"  # Unknown team
        })
        writer.writerow({
            "record_uid": "nonexistent",  # Record not in vault
            "title": "Missing Record",
            "folder_path": "/path",
            "Team One": "ro"
        })
    
    result = service.validate_csv_file(csv_file, vault_data)
    assert not result.is_valid
    assert any("Unknown teams" in error for error in result.errors)
    assert any("not found in vault" in error for error in result.errors)
    assert any("Title mismatch" in warning for warning in result.warnings)
    assert any("Folder path mismatch" in warning for warning in result.warnings)


def test_validation_service_large_file_warning(tmp_path):
    """Test ValidationService warning for large files."""
    service = ValidationService()
    
    # Create large CSV (simulate with metadata)
    csv_file = tmp_path / "large.csv" 
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
        writer.writeheader()
        # Write many rows to trigger warning
        for i in range(1001):
            writer.writerow({
                "record_uid": f"uid{i}",
                "title": f"Title {i}",
                "folder_path": f"/path{i}"
            })
    
    result = service.validate_csv_file(csv_file)
    assert result.is_valid
    assert any("Large CSV file" in warning for warning in result.warnings)


# Integration tests
@pytest.mark.integration
def test_integration_ensure_folder_path(live_vault_data):
    """
    Tests the _ensure_folder_path with real API calls.
    It creates a unique folder path and verifies its creation.
    NOTE: This test leaves dummy folders in the vault.
    """
    svc = ProvisioningService(vault_service=VaultService())
    operations = []

    # Create a unique path for this test run
    # The command handles nesting, so we test that directly.
    parent_name = f"Test-Parent-{uuid.uuid4().hex[:8]}"
    child_name = f"Test-Child-{uuid.uuid4().hex[:8]}"
    test_path = f"{parent_name}/{child_name}"

    # First run: should create the full path in one operation
    child_uid = svc._ensure_folder_path(test_path, operations)
    assert child_uid is not None
    assert len(operations) == 2  # Parent + child folders
    assert f"Created shared folder: '{parent_name}'" in operations[0]
    assert f"Created shared folder: '{test_path}'" in operations[1]

    # Verify folders exist. We need to find the parent first to get its UID.
    parent_folder = find_folder_by_name(parent_name, parent_uid=None)
    assert parent_folder is not None, "Parent folder should have been created."
    child_folder = find_folder_by_name(child_name, parent_uid=parent_folder["uid"])
    assert child_folder is not None, "Child folder should have been created."
    assert child_folder["uid"] == child_uid

    # Second run: should find the existing folders
    operations_run2 = []
    child_uid_run2 = svc._ensure_folder_path(test_path, operations_run2)
    assert child_uid_run2 == child_uid
    assert len(operations_run2) == 2  # Should find both existing folders
    assert f"Found existing folder: '{parent_name}'" in operations_run2[0]
    assert f"Found existing folder: '{child_name}'" in operations_run2[1]


@pytest.mark.integration
def test_integration_apply_changes(tmp_path, live_vault_data):
    """
    Tests the apply_changes with real API calls.
    It fetches a real record/team, creates a CSV, applies it,
    and verifies the result.
    """
    # 1. Get real data to use for the test
    all_records = get_records()
    all_teams = get_teams()
    assert all_records, "Vault must have at least one record to run this test"
    assert all_teams, "Vault must have at least one team to run this test"

    test_record = all_records[0]
    test_team = all_teams[0]

    test_record_uid = test_record["uid"]
    test_team_name = test_team["team_name"]

    # 2. Create a unique folder path for the test
    folder_name = f"Test-Apply-{uuid.uuid4().hex[:8]}"

    # 3. Create sample CSV
    csv_content = f"record_uid,title,folder_path,{test_team_name}\n"
    csv_content += f"{test_record_uid},{test_record['title']},{folder_name},rw\n"
    csv_file = tmp_path / "apply_test.csv"
    csv_file.write_text(csv_content)

    # 4. Apply the changes
    svc = ProvisioningService(vault_service=VaultService())
    result = svc.apply_changes(csv_file, ConfigRecord())

    assert result.success is True, f"Apply failed: {result.errors}"
    assert "Apply completed successfully" in result.message

    # 5. Verify the changes
    # Check that the folder was created under the root folder
    # First find the root folder "[Perms]"
    root_folder = find_folder_by_name("[Perms]", parent_uid=None)
    assert root_folder is not None, "Root folder '[Perms]' should exist."
    
    # Then find the test folder within it
    folder = find_folder_by_name(folder_name, parent_uid=root_folder["uid"])
    assert folder is not None, f"Folder '{folder_name}' was not created under '[Perms]'."

    # TODO: Verify record and team permissions on the folder.
    # This requires more getter functions in keeper_client.
    # For now, successful apply is a good indicator.

    # TODO: Cleanup. 