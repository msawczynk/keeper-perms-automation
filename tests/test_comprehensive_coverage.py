"""
Comprehensive test suite for 100% code coverage of keeper_auto package.
This file focuses on testing all the uncovered lines and edge cases.
"""

import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from keeper_auto.models import (
    VaultData, ValidationResult, OperationResult, CSVTemplate, ConfigRecord,
    Record, Team, VaultFolder
)
from keeper_auto.services import (
    ConfigService, VaultService, TemplateService, ProvisioningService, ValidationService
)
from keeper_auto.exceptions import (
    APIError, AuthenticationError, ConfigurationError, ValidationError,
    OperationError, DataError, NetworkError, PermissionError
)


class TestExceptions:
    """Test all exception classes."""
    
    def test_api_error_with_code(self):
        error = APIError("Test error", error_code="E001")
        assert str(error) == "Test error"
        assert error.error_code == "E001"
    
    def test_api_error_without_code(self):
        error = APIError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None
    
    def test_authentication_error(self):
        error = AuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
    
    def test_configuration_error(self):
        error = ConfigurationError("Config error")
        assert str(error) == "Config error"
    
    def test_validation_error(self):
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
    
    def test_operation_error(self):
        error = OperationError("Operation failed")
        assert str(error) == "Operation failed"
    
    def test_data_error(self):
        error = DataError("Data error")
        assert str(error) == "Data error"
    
    def test_network_error(self):
        error = NetworkError("Network error")
        assert str(error) == "Network error"
    
    def test_permission_error(self):
        error = PermissionError("Permission denied")
        assert str(error) == "Permission denied"


class TestModels:
    """Test all model classes and their methods."""
    
    def test_vault_record_model(self):
        record = Record(uid="uid1", title="Title", folder_path="/path")
        assert record.uid == "uid1"
        assert record.title == "Title"
        assert record.folder_path == "/path"
    
    def test_team_model(self):
        team = Team(uid="team1", name="Team One")
        assert team.uid == "team1"
        assert team.name == "Team One"
    
    def test_folder_model(self):
        folder = VaultFolder(uid="folder1", name="Folder One", parent_uid="parent1")
        assert folder.uid == "folder1"
        assert folder.name == "Folder One"
        assert folder.parent_uid == "parent1"
        
        # Test folder without parent
        root_folder = VaultFolder(uid="root", name="Root", parent_uid=None)
        assert root_folder.parent_uid is None
    
    def test_vault_data_comprehensive(self):
        vault_data = VaultData()
        
        # Test initial state
        assert not vault_data.is_loaded()
        assert vault_data.summary() == {"teams": 0, "folders": 0, "records": 0}
        assert vault_data.get_team_by_uid("nonexistent") is None
        assert vault_data.find_folder_by_uid("nonexistent") is None
        assert vault_data.get_record_by_uid("nonexistent") is None
        
        # Add data
        vault_data.add_team("team1", "Team One")
        vault_data.add_folder("folder1", "Folder One", None)
        vault_data.add_record("record1", "Record One", "/path")
        
        # Test retrieval
        team = vault_data.get_team_by_uid("team1")
        assert team.name == "Team One"
        
        folder = vault_data.find_folder_by_uid("folder1")
        assert folder.name == "Folder One"
        
        record = vault_data.get_record_by_uid("record1")
        assert record.title == "Record One"
        
        # Test summary
        summary = vault_data.summary()
        assert summary["teams"] == 1
        assert summary["folders"] == 1
        assert summary["records"] == 1
        
        # Test mark loaded
        vault_data.mark_loaded()
        assert vault_data.is_loaded()
        
        # Test clear
        vault_data.clear()
        assert not vault_data.is_loaded()
        assert len(vault_data.teams_by_uid) == 0
    
    def test_validation_result_comprehensive(self):
        result = ValidationResult()
        
        # Test initial state
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.metadata == {}
        
        # Test adding errors and warnings
        result.add_error("Error 1")
        result.add_error("Error 2")
        result.add_warning("Warning 1")
        
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "Error 1" in result.errors
        assert "Warning 1" in result.warnings
    
    def test_operation_result_comprehensive(self):
        # Test minimal result
        result = OperationResult(success=True, message="Success")
        assert result.success
        assert result.message == "Success"
        assert result.data is None
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        
        # Test full result
        result = OperationResult(
            success=False,
            message="Failed",
            data={"key": "value"},
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert not result.success
        assert result.data["key"] == "value"
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
    
    def test_csv_template_comprehensive(self):
        template = CSVTemplate()
        
        # Test initial state
        expected_headers = ["record_uid", "title", "folder_path"]
        assert template.headers == expected_headers
        assert len(template.rows) == 0
        
        # Test adding rows
        template.add_row("uid1", "Title 1", "/path1", {"Team1": "ro", "Team2": "rw"})
        template.add_row("uid2", "Title 2", "/path2", {"Team1": "rws"})
        
        assert len(template.rows) == 2
        
        # Check first row
        row1 = template.rows[0]
        assert row1["record_uid"] == "uid1"
        assert row1["title"] == "Title 1"
        assert row1["folder_path"] == "/path1"
        assert row1["Team1"] == "ro"
        assert row1["Team2"] == "rw"
        
        # Check second row
        row2 = template.rows[1]
        assert row2["record_uid"] == "uid2"
        assert row2["Team1"] == "rws"
        assert "Team2" not in row2  # Should not have Team2 permission
    
    def test_config_record_defaults(self):
        config = ConfigRecord()
        assert config.root_folder_name == "[Perms]"
        assert config.included_teams is None
        assert config.included_folders is None
        assert config.excluded_folders == []
    
    def test_config_record_custom(self):
        config = ConfigRecord(
            root_folder_name="[Custom]",
            included_teams=["team1", "team2"],
            included_folders=["folder1"],
            excluded_folders=["folder2", "folder3"]
        )
        assert config.root_folder_name == "[Custom]"
        assert config.included_teams == ["team1", "team2"]
        assert config.included_folders == ["folder1"]
        assert config.excluded_folders == ["folder2", "folder3"]


class TestConfigService:
    """Test ConfigService comprehensive functionality."""
    
    def test_load_configuration_no_uid_no_record(self):
        service = ConfigService()
        
        with patch('keeper_auto.services.get_records', return_value=[]):
            result = service.load_configuration()
            assert result.success
            assert "not found" in result.message
            assert isinstance(result.data, ConfigRecord)
            assert len(result.warnings) == 1
    
    def test_load_configuration_find_by_title(self):
        service = ConfigService()
        
        mock_records = [
            {"uid": "other_uid", "title": "Other Record"},
            {"uid": "config_uid", "title": "Perms-Config"},
        ]
        
        mock_field = Mock()
        mock_field.type = 'json'
        mock_field.value = '{"root_folder_name": "[Found]"}'
        
        mock_record = Mock()
        mock_record.data = [mock_field]
        
        with patch('keeper_auto.services.get_records', return_value=mock_records), \
             patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration()
            assert result.success
            assert result.data.root_folder_name == "[Found]"
    
    def test_load_configuration_with_uid_valid_json(self):
        service = ConfigService()
        
        mock_field = Mock()
        mock_field.type = 'json'
        mock_field.value = json.dumps({
            "root_folder_name": "[Test]",
            "included_teams": ["team1"],
            "included_folders": ["folder1"],
            "excluded_folders": ["folder2"]
        })
        
        mock_record = Mock()
        mock_record.data = [mock_field]
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert result.success
            assert result.data.root_folder_name == "[Test]"
            assert result.data.included_teams == ["team1"]
            assert result.data.included_folders == ["folder1"]
            assert result.data.excluded_folders == ["folder2"]
    
    def test_load_configuration_invalid_json(self):
        service = ConfigService()
        
        mock_field = Mock()
        mock_field.type = 'json'
        mock_field.value = 'invalid json{'
        
        mock_record = Mock()
        mock_record.data = [mock_field]
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert not result.success
            assert "Failed to parse" in result.message
            assert len(result.errors) == 1
    
    def test_load_configuration_empty_record(self):
        service = ConfigService()
        
        mock_record = Mock()
        mock_record.data = []  # No fields
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert result.success
            assert "empty" in result.message
            assert len(result.warnings) == 1
    
    def test_load_configuration_no_json_field(self):
        service = ConfigService()
        
        mock_field = Mock()
        mock_field.type = 'text'  # Not json
        mock_field.value = 'some text'
        
        mock_record = Mock()
        mock_record.data = [mock_field]
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert result.success
            assert "empty" in result.message
            assert len(result.warnings) == 1
    
    def test_load_configuration_api_exception(self):
        service = ConfigService()
        
        with patch('keeper_auto.services.get_record', side_effect=Exception("API Error")):
            result = service.load_configuration("test_uid")
            assert not result.success
            assert "Could not load configuration" in result.message
            assert len(result.errors) == 1
    
    def test_find_config_record_by_title_exception(self):
        service = ConfigService()
        
        with patch('keeper_auto.services.get_records', side_effect=Exception("Search failed")):
            result = service._find_config_record_by_title()
            assert result is None


class TestVaultService:
    """Test VaultService comprehensive functionality."""
    
    def test_load_vault_data_cached(self):
        service = VaultService()
        service.vault_data.mark_loaded()
        
        # Should return cached data without API calls
        result = service.load_vault_data()
        assert result.is_loaded()
    
    def test_load_vault_data_force_reload(self):
        service = VaultService()
        service.vault_data.mark_loaded()
        
        mock_folder_data = {
            "folders": [
                {"uid": "folder1", "name": "Folder 1", "parent_uid": None}
            ],
            "records": [
                {"uid": "record1", "title": "Record 1", "folder_uid": "folder1"}
            ]
        }
        mock_teams = [
            {"team_uid": "team1", "team_name": "Team 1"}
        ]
        
        with patch('keeper_auto.services.get_folder_data', return_value=mock_folder_data), \
             patch('keeper_auto.services.get_teams', return_value=mock_teams):
            result = service.load_vault_data(force_reload=True)
            assert result.is_loaded()
            assert len(result.teams_by_uid) == 1
            assert len(result.folders_by_uid) == 1
            assert len(result.records_by_uid) == 1
    
    def test_load_vault_data_with_config_filtering(self):
        service = VaultService()
        
        config = ConfigRecord(
            included_teams=["team1"],
            included_folders=["folder1"],
            excluded_folders=["folder2"]
        )
        
        mock_folder_data = {
            "folders": [
                {"uid": "folder1", "name": "Included Folder", "parent_uid": None},
                {"uid": "folder2", "name": "Excluded Folder", "parent_uid": None},
                {"uid": "folder3", "name": "Not Included Folder", "parent_uid": None}
            ],
            "records": [
                {"uid": "record1", "title": "Record 1", "folder_uid": "folder1"}
            ]
        }
        mock_teams = [
            {"team_uid": "team1", "team_name": "Included Team"},
            {"team_uid": "team2", "team_name": "Not Included Team"}
        ]
        
        with patch('keeper_auto.services.get_folder_data', return_value=mock_folder_data), \
             patch('keeper_auto.services.get_teams', return_value=mock_teams):
            result = service.load_vault_data(config=config)
            
            # Should only include team1 (in included_teams)
            assert len(result.teams_by_uid) == 1
            assert "team1" in result.teams_by_uid
            
            # Should only include folder1 (in included_folders, folder2 is excluded)
            assert len(result.folders_by_uid) == 1
            assert "folder1" in result.folders_by_uid
    
    def test_load_vault_data_api_exception(self):
        service = VaultService()
        
        with patch('keeper_auto.services.get_folder_data', side_effect=Exception("API Error")):
            with pytest.raises(APIError):
                service.load_vault_data()
    
    def test_build_folder_path_complex_hierarchy(self):
        service = VaultService()
        
        # Build complex folder hierarchy
        service.vault_data.add_folder("root", "Root", None)
        service.vault_data.add_folder("level1", "Level1", "root")
        service.vault_data.add_folder("level2", "Level2", "level1")
        service.vault_data.add_folder("level3", "Level3", "level2")
        
        path = service._build_folder_path("level3")
        assert path == "/Root/Level1/Level2/Level3"
        
        path = service._build_folder_path("level1")
        assert path == "/Root/Level1"
        
        path = service._build_folder_path("root")
        assert path == "/Root"
    
    def test_build_folder_path_edge_cases(self):
        service = VaultService()
        
        # Test with None
        path = service._build_folder_path(None)
        assert path == ""
        
        # Test with nonexistent folder
        path = service._build_folder_path("nonexistent")
        assert path == ""
        
        # Test with broken hierarchy (missing parent)
        service.vault_data.add_folder("orphan", "Orphan", "missing_parent")
        path = service._build_folder_path("orphan")
        assert path == "/Orphan"  # Should stop at the orphan
    
    def test_get_vault_summary_not_loaded(self):
        service = VaultService()
        
        mock_folder_data = {"folders": [], "records": []}
        mock_teams = []
        
        with patch('keeper_auto.services.get_folder_data', return_value=mock_folder_data), \
             patch('keeper_auto.services.get_teams', return_value=mock_teams), \
             patch.object(service, 'load_vault_data', wraps=service.load_vault_data) as mock_load:
            summary = service.get_vault_summary()
            mock_load.assert_called_once()
            assert isinstance(summary, dict)


class TestTemplateService:
    """Test TemplateService comprehensive functionality."""
    
    def test_generate_template_no_teams(self):
        vault_service = VaultService()
        service = TemplateService(vault_service)
        
        vault_data = VaultData()
        # No teams added
        
        result = service.generate_template(vault_data, Path("test.csv"))
        assert not result.success
        assert "No teams found" in result.message
    
    def test_generate_template_success(self, tmp_path):
        vault_service = VaultService()
        service = TemplateService(vault_service)
        
        vault_data = VaultData()
        vault_data.add_team("team1", "Team Alpha")
        vault_data.add_team("team2", "Team Beta")
        vault_data.add_record("record1", "Record One", "/Folder1")
        vault_data.add_record("record2", "Record Two", "/Folder2")
        
        output_path = tmp_path / "template.csv"
        result = service.generate_template(vault_data, output_path)
        
        assert result.success
        assert output_path.exists()
        
        # Verify CSV structure
        with open(output_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)
        
        expected_headers = ["record_uid", "title", "folder_path", "Team Alpha", "Team Beta"]
        assert set(headers) == set(expected_headers)
        assert len(rows) == 2
        
        # Verify row content
        assert rows[0]["record_uid"] == "record1"
        assert rows[0]["title"] == "Record One"
        assert rows[0]["folder_path"] == "/Folder1"
        assert rows[0]["Team Alpha"] == ""
        assert rows[0]["Team Beta"] == ""
    
    def test_generate_template_write_exception(self, tmp_path):
        vault_service = VaultService()
        service = TemplateService(vault_service)
        
        vault_data = VaultData()
        vault_data.add_team("team1", "Team One")
        vault_data.add_record("record1", "Record One", "/path")
        
        # Use a directory as the output path to cause write error
        output_path = tmp_path / "directory"
        output_path.mkdir()
        
        result = service.generate_template(vault_data, output_path)
        assert not result.success
        assert "Failed to write template" in result.message


class TestProvisioningService:
    """Test ProvisioningService comprehensive functionality."""
    
    def test_get_changes_from_csv_success(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        # Create test CSV
        csv_data = [
            {"record_uid": "uid1", "title": "Title 1", "folder_path": "/path1"},
            {"record_uid": "uid2", "title": "Title 2", "folder_path": "/path2"}
        ]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        changes = service._get_changes_from_csv(csv_file)
        assert len(changes) == 2
        assert changes[0]["record_uid"] == "uid1"
        assert changes[1]["record_uid"] == "uid2"
    
    def test_get_target_folder_path_variations(self):
        service = ProvisioningService(VaultService())
        config = ConfigRecord(root_folder_name="[Root]")
        
        # Test with folder path
        row = {"folder_path": "Sub/Folder"}
        path = service._get_target_folder_path(config, row)
        assert path == "[Root]/Sub/Folder"
        
        # Test with leading/trailing slashes
        row = {"folder_path": "/Sub/Folder/"}
        path = service._get_target_folder_path(config, row)
        assert path == "[Root]/Sub/Folder"
        
        # Test with empty folder path
        row = {"folder_path": ""}
        path = service._get_target_folder_path(config, row)
        assert path == "[Root]"
        
        # Test with missing folder path
        row = {}
        path = service._get_target_folder_path(config, row)
        assert path == "[Root]"
    
    def test_extract_team_permissions_comprehensive(self):
        service = ProvisioningService(VaultService())
        
        row = {
            "record_uid": "uid1",
            "title": "Title",
            "Team_Alpha_can_edit": "true",
            "Team_Alpha_can_share": "false",
            "Team_Beta_manage_records": "true",
            "Team_Beta_manage_users": "false",
            "Team_Gamma_can_edit": "TRUE",  # Test case insensitive
            "Team_Delta_manage_users": "False",  # Test case insensitive
            "Invalid_Column": "value",  # Should be ignored
            "Team_Invalid_format": "true",  # Should be ignored (wrong format)
            "folder_path": "/path"  # Should be ignored
        }
        
        perms = service._extract_team_permissions(row)
        
        assert "Team_Alpha" in perms
        assert perms["Team_Alpha"]["can_edit"] == True
        assert perms["Team_Alpha"]["can_share"] == False
        
        assert "Team_Beta" in perms
        assert perms["Team_Beta"]["manage_records"] == True
        assert perms["Team_Beta"]["manage_users"] == False
        
        assert "Team_Gamma" in perms
        assert perms["Team_Gamma"]["can_edit"] == True
        
        assert "Team_Delta" in perms
        assert perms["Team_Delta"]["manage_users"] == False
        
        # Should not include invalid formats
        assert "Team_Invalid" not in perms
        assert "Invalid" not in perms
    
    def test_dry_run_success(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        # Create test CSV
        csv_data = [
            {"record_uid": "uid1", "title": "Title 1", "folder_path": "path1"},
            {"record_uid": "uid2", "title": "Title 2", "folder_path": "path2"}
        ]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        result = service.dry_run(csv_file, config)
        
        assert result.success
        assert "Dry run completed" in result.message
        assert "operations" in result.data
        assert len(result.data["operations"]) >= 2  # At least one operation per record
    
    def test_dry_run_exception(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        # Create invalid CSV (missing required headers)
        csv_file = tmp_path / "invalid.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["invalid_header"])
            writer.writerow(["invalid_data"])
        
        config = ConfigRecord()
        result = service.dry_run(csv_file, config)
        
        assert not result.success
        assert "Failed to perform dry run" in result.message
    
    def test_ensure_folder_path_creation_failure(self):
        service = ProvisioningService(VaultService())
        operations = []
        
        with patch('keeper_auto.services.find_folder_by_name', return_value=None), \
             patch('keeper_auto.services.create_shared_folder', side_effect=Exception("Creation failed")):
            result = service._ensure_folder_path("Test/Path", operations)
            assert result is None
            assert any("Failed to create folder" in op for op in operations)
    
    def test_ensure_folder_path_already_exists_error(self):
        service = ProvisioningService(VaultService())
        operations = []
        
        mock_folder = {"uid": "found_uid"}
        
        with patch('keeper_auto.services.find_folder_by_name', side_effect=[None, mock_folder]), \
             patch('keeper_auto.services.create_shared_folder', side_effect=Exception("already exists")):
            result = service._ensure_folder_path("Test", operations)
            assert result == "found_uid"
            assert any("Found existing folder" in op for op in operations)
    
    def test_apply_changes_comprehensive_success(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        # Create test CSV with team permissions
        csv_data = [
            {
                "record_uid": "uid1", 
                "title": "Title 1", 
                "folder_path": "path1",
                "Team_Alpha_can_edit": "true"
            }
        ]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        
        with patch('keeper_auto.services.find_folder_by_name', return_value=None), \
             patch('keeper_auto.services.create_shared_folder', return_value="folder_uid"), \
             patch('keeper_auto.services.share_record_to_folder'), \
             patch('keeper_auto.services.get_team_uid_by_name', return_value="team_uid"), \
             patch('keeper_auto.services.add_team_to_shared_folder'):
            
            result = service.apply_changes(csv_file, config)
            assert result.success
            assert "Apply completed successfully" in result.message
    
    def test_apply_changes_with_errors(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        # Create test CSV with missing data
        csv_data = [
            {"record_uid": "", "title": "Title 1", "folder_path": "path1"},  # Missing UID
            {"record_uid": "uid2", "title": "", "folder_path": "path2"},     # Missing title
            {"record_uid": "uid3", "title": "Title 3", "folder_path": "path3"}  # Valid
        ]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        
        with patch('keeper_auto.services.find_folder_by_name', return_value=None), \
             patch('keeper_auto.services.create_shared_folder', return_value="folder_uid"), \
             patch('keeper_auto.services.share_record_to_folder'):
            
            result = service.apply_changes(csv_file, config)
            assert not result.success
            assert "Apply completed with errors" in result.message
            assert len(result.errors) >= 2  # Should have errors for missing UID and title
    
    def test_apply_changes_folder_creation_failure(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        csv_data = [{"record_uid": "uid1", "title": "Title 1", "folder_path": "path1"}]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        
        with patch.object(service, '_ensure_folder_path', return_value=None):
            result = service.apply_changes(csv_file, config)
            assert not result.success
            assert "Apply completed with errors" in result.message
            assert any("Could not create or find folder" in error for error in result.errors)
    
    def test_apply_changes_team_not_found(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        csv_data = [
            {
                "record_uid": "uid1", 
                "title": "Title 1", 
                "folder_path": "path1",
                "Unknown_Team_can_edit": "true"
            }
        ]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        
        with patch('keeper_auto.services.find_folder_by_name', return_value=None), \
             patch('keeper_auto.services.create_shared_folder', return_value="folder_uid"), \
             patch('keeper_auto.services.share_record_to_folder'), \
             patch('keeper_auto.services.get_team_uid_by_name', return_value=None):
            
            result = service.apply_changes(csv_file, config)
            assert not result.success
            assert any("Team 'Unknown_Team' not found" in error for error in result.errors)
    
    def test_apply_changes_processing_exception(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        csv_data = [{"record_uid": "uid1", "title": "Title 1", "folder_path": "path1"}]
        
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        config = ConfigRecord()
        
        with patch.object(service, '_ensure_folder_path', side_effect=Exception("Processing error")):
            result = service.apply_changes(csv_file, config)
            assert not result.success
            assert any("Failed to process record" in error for error in result.errors)
    
    def test_apply_changes_general_exception(self, tmp_path):
        service = ProvisioningService(VaultService())
        
        csv_file = tmp_path / "nonexistent.csv"  # File doesn't exist
        config = ConfigRecord()
        
        result = service.apply_changes(csv_file, config)
        assert not result.success
        assert "Failed to apply changes" in result.message


class TestValidationService:
    """Test ValidationService comprehensive functionality."""
    
    def test_validate_csv_file_not_found(self):
        service = ValidationService()
        result = service.validate_csv_file(Path("nonexistent.csv"))
        
        assert not result.is_valid
        assert any("not found" in error for error in result.errors)
    
    def test_validate_csv_empty_file(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        result = service.validate_csv_file(csv_file)
        assert not result.is_valid
        assert any("no headers" in error for error in result.errors)
    
    def test_validate_csv_missing_required_headers(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "missing_headers.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["record_uid", "title"])  # Missing folder_path
            writer.writerow(["uid1", "Title 1"])
        
        result = service.validate_csv_file(csv_file)
        assert not result.is_valid
        assert any("Missing required headers" in error for error in result.errors)
    
    def test_validate_csv_empty_rows_warning(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "empty_rows.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            # No data rows
        
        result = service.validate_csv_file(csv_file)
        assert result.is_valid
        assert any("empty" in warning for warning in result.warnings)
    
    def test_validate_csv_large_file_warning(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "large.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            # Write more than 1000 rows
            for i in range(1001):
                writer.writerow({
                    "record_uid": f"uid{i}",
                    "title": f"Title {i}",
                    "folder_path": f"/path{i}"
                })
        
        result = service.validate_csv_file(csv_file)
        assert result.is_valid
        assert any("Large CSV file" in warning for warning in result.warnings)
        assert result.metadata["rows"] == 1001
    
    def test_validate_csv_no_team_columns_warning(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "no_teams.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            writer.writerow({"record_uid": "uid1", "title": "Title 1", "folder_path": "/path"})
        
        result = service.validate_csv_file(csv_file)
        assert result.is_valid
        assert any("No team permission columns" in warning for warning in result.warnings)
    
    def test_validate_csv_invalid_permissions(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "invalid_perms.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path", "Team1"])
            writer.writeheader()
            writer.writerow({
                "record_uid": "uid1",
                "title": "Title 1",
                "folder_path": "/path",
                "Team1": "invalid_permission"
            })
        
        result = service.validate_csv_file(csv_file)
        assert not result.is_valid
        assert any("Invalid permission value" in error for error in result.errors)
    
    def test_validate_csv_missing_record_uid(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "missing_uid.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            writer.writerow({"record_uid": "", "title": "Title 1", "folder_path": "/path"})
        
        result = service.validate_csv_file(csv_file)
        assert not result.is_valid
        assert any("Missing record_uid" in error for error in result.errors)
    
    def test_validate_csv_with_vault_data_unknown_teams(self, tmp_path):
        service = ValidationService()
        
        vault_data = VaultData()
        vault_data.add_team("team1", "Known Team")
        
        csv_file = tmp_path / "unknown_teams.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path", "Known Team", "Unknown Team"])
            writer.writeheader()
            writer.writerow({
                "record_uid": "uid1",
                "title": "Title 1",
                "folder_path": "/path",
                "Known Team": "ro",
                "Unknown Team": "rw"
            })
        
        result = service.validate_csv_file(csv_file, vault_data)
        assert not result.is_valid
        assert any("Unknown teams" in error for error in result.errors)
    
    def test_validate_csv_with_vault_data_record_not_found(self, tmp_path):
        service = ValidationService()
        
        vault_data = VaultData()
        vault_data.add_record("existing_uid", "Existing Record", "/path")
        
        csv_file = tmp_path / "missing_record.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            writer.writerow({
                "record_uid": "nonexistent_uid",
                "title": "Missing Record",
                "folder_path": "/path"
            })
        
        result = service.validate_csv_file(csv_file, vault_data)
        assert not result.is_valid
        assert any("not found in vault" in error for error in result.errors)
    
    def test_validate_csv_with_vault_data_drift_warnings(self, tmp_path):
        service = ValidationService()
        
        vault_data = VaultData()
        vault_data.add_record("uid1", "Correct Title", "/correct/path")
        
        csv_file = tmp_path / "drift.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path"])
            writer.writeheader()
            writer.writerow({
                "record_uid": "uid1",
                "title": "Wrong Title",
                "folder_path": "/wrong/path"
            })
        
        result = service.validate_csv_file(csv_file, vault_data)
        assert result.is_valid  # Drift is warning, not error
        assert any("Title mismatch" in warning for warning in result.warnings)
        assert any("Folder path mismatch" in warning for warning in result.warnings)
    
    def test_validate_csv_exception_handling(self, tmp_path):
        service = ValidationService()
        
        # Create a file that will cause an exception when reading
        csv_file = tmp_path / "bad_encoding.csv"
        with open(csv_file, 'wb') as f:
            f.write(b'\xff\xfe')  # Invalid UTF-8
        
        result = service.validate_csv_file(csv_file)
        assert not result.is_valid
        assert any("CSV validation failed" in error for error in result.errors)
    
    def test_validate_csv_metadata(self, tmp_path):
        service = ValidationService()
        
        csv_file = tmp_path / "metadata_test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["record_uid", "title", "folder_path", "Team1", "Team2"])
            writer.writeheader()
            writer.writerow({"record_uid": "uid1", "title": "Title 1", "folder_path": "/path", "Team1": "ro", "Team2": "rw"})
            writer.writerow({"record_uid": "uid2", "title": "Title 2", "folder_path": "/path", "Team1": "rws", "Team2": "ro"})
        
        result = service.validate_csv_file(csv_file)
        assert result.is_valid
        assert result.metadata["headers"] == 5
        assert result.metadata["rows"] == 2
        assert result.metadata["team_columns"] == 2 