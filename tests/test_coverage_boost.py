"""
Comprehensive test suite to boost code coverage for keeper_auto package.
This file focuses on testing all the uncovered lines and edge cases.
"""

import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import tempfile

from keeper_auto.models import (
    VaultData, ValidationResult, OperationResult, CSVTemplate, ConfigRecord,
    Record, Team, VaultFolder, Permission, PermissionLevel
)
from keeper_auto.services import (
    ConfigService, VaultService, TemplateService, ProvisioningService, ValidationService
)
from keeper_auto.exceptions import (
    APIError, AuthenticationError, ConfigurationError, ValidationError,
    OperationError, DataError, NetworkError, PermissionError
)


class TestExceptionCoverage:
    """Test all exception classes for full coverage."""
    
    def test_api_error_with_error_code(self):
        error = APIError("Test API error", error_code="E001")
        assert str(error) == "Test API error"
        assert error.error_code == "E001"
    
    def test_api_error_without_error_code(self):
        error = APIError("Test API error")
        assert str(error) == "Test API error"
        assert error.error_code is None
    
    def test_authentication_error(self):
        error = AuthenticationError("Authentication failed")
        assert str(error) == "Authentication failed"
    
    def test_configuration_error(self):
        error = ConfigurationError("Configuration error")
        assert str(error) == "Configuration error"
    
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


class TestModelCoverage:
    """Test all model classes for full coverage."""
    
    def test_permission_level_enum(self):
        """Test PermissionLevel enum values."""
        assert PermissionLevel.NONE.value == "none"
        assert PermissionLevel.VIEW.value == "view"
        assert PermissionLevel.EDIT.value == "edit"
        assert PermissionLevel.SHARE.value == "share"
        assert PermissionLevel.MANAGE_RECORDS.value == "manage_records"
        assert PermissionLevel.MANAGE_USERS.value == "manage_users"
    
    def test_config_record_defaults(self):
        """Test ConfigRecord default values."""
        config = ConfigRecord()
        assert config.root_folder_name == "[Perms]"
        assert config.included_teams is None
        assert config.included_folders is None
        assert config.excluded_folders == []
    
    def test_config_record_custom_values(self):
        """Test ConfigRecord with custom values."""
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
    
    def test_vault_folder_model(self):
        """Test VaultFolder model."""
        # Test folder with parent
        folder = VaultFolder(uid="folder1", name="Folder One", parent_uid="parent1")
        assert folder.uid == "folder1"
        assert folder.name == "Folder One"
        assert folder.parent_uid == "parent1"
        assert str(folder) == "Folder One"
        assert hash(folder) == hash("folder1")
        
        # Test root folder
        root_folder = VaultFolder(uid="root", name="Root")
        assert root_folder.parent_uid is None
        assert len(root_folder.subfolders) == 0
        assert len(root_folder.records) == 0
    
    def test_record_model(self):
        """Test Record model."""
        record = Record(uid="record1", title="Test Record", folder_path="/test/path")
        assert record.uid == "record1"
        assert record.title == "Test Record"
        assert record.folder_path == "/test/path"
        assert str(record) == "Test Record"
        assert hash(record) == hash("record1")
        
        # Test record with default folder path
        record2 = Record(uid="record2", title="Test Record 2")
        assert record2.folder_path == ""
    
    def test_team_model(self):
        """Test Team model."""
        team = Team(uid="team1", name="Test Team")
        assert team.uid == "team1"
        assert team.name == "Test Team"
        assert str(team) == "Test Team"
        assert hash(team) == hash("team1")
    
    def test_permission_model(self):
        """Test Permission model."""
        team = Team(uid="team1", name="Test Team")
        record = Record(uid="record1", title="Test Record")
        
        permission = Permission(team=team, record=record)
        assert permission.team == team
        assert permission.record == record
        assert permission.can_edit is False
        assert permission.can_share is False
        assert permission.manage_records is False
        assert permission.manage_users is False
        
        # Test to_dict
        perm_dict = permission.to_dict()
        assert perm_dict["team_uid"] == "team1"
        assert perm_dict["team_name"] == "Test Team"
        assert perm_dict["record_uid"] == "record1"
        assert perm_dict["record_title"] == "Test Record"
        assert perm_dict["can_edit"] is False
        
        # Test with permissions set
        permission.can_edit = True
        permission.manage_records = True
        perm_dict = permission.to_dict()
        assert perm_dict["can_edit"] is True
        assert perm_dict["manage_records"] is True
    
    def test_permission_from_csv_row(self):
        """Test Permission.from_csv_row method."""
        team = Team(uid="team1", name="Test Team")
        record = Record(uid="record1", title="Test Record")
        
        teams = {"team1": team}
        records = {"record1": record}
        
        # Test with valid permissions
        row = {
            "record_uid": "record1",
            "Test_can_edit": "true",
            "Test_can_share": "false",
            "Test_manage_records": "true",
            "Test_manage_users": "false"
        }
        
        permissions = Permission.from_csv_row(teams, records, "record1", row)
        assert len(permissions) == 1
        
        perm = permissions[0]
        assert perm.team.uid == "team1"
        assert perm.record.uid == "record1"
        assert perm.can_edit is True
        assert perm.can_share is False
        assert perm.manage_records is True
        assert perm.manage_users is False
    
    def test_permission_from_csv_row_invalid_record(self):
        """Test Permission.from_csv_row with invalid record."""
        teams = {"team1": Team(uid="team1", name="Test Team")}
        records = {"record1": Record(uid="record1", title="Test Record")}
        
        permissions = Permission.from_csv_row(teams, records, "nonexistent", {})
        assert len(permissions) == 0
    
    def test_permission_from_csv_row_invalid_team(self):
        """Test Permission.from_csv_row with invalid team."""
        teams = {"team1": Team(uid="team1", name="Test Team")}
        records = {"record1": Record(uid="record1", title="Test Record")}
        
        row = {
            "record_uid": "record1",
            "NonexistentTeam_can_edit": "true"
        }
        
        permissions = Permission.from_csv_row(teams, records, "record1", row)
        assert len(permissions) == 0
    
    def test_permission_from_csv_row_invalid_values(self):
        """Test Permission.from_csv_row with invalid permission values."""
        team = Team(uid="team1", name="Test Team")
        record = Record(uid="record1", title="Test Record")
        
        teams = {"team1": team}
        records = {"record1": record}
        
        row = {
            "record_uid": "record1",
            "Test_can_edit": "invalid_value",
            "Test_can_share": "maybe"
        }
        
        permissions = Permission.from_csv_row(teams, records, "record1", row)
        assert len(permissions) == 0
    
    def test_validation_result_comprehensive(self):
        """Test ValidationResult model comprehensively."""
        # Test default constructor
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.metadata == {}
        assert not result.has_issues()
        
        # Test add_error
        result.add_error("Test error")
        assert not result.is_valid
        assert "Test error" in result.errors
        assert result.has_issues()
        
        # Test add_warning
        result.add_warning("Test warning")
        assert "Test warning" in result.warnings
        assert result.has_issues()
        
        # Test constructor with all parameters
        result2 = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            metadata={"key": "value"}
        )
        assert not result2.is_valid
        assert len(result2.errors) == 2
        assert len(result2.warnings) == 1
        assert result2.metadata["key"] == "value"
        assert result2.has_issues()
    
    def test_operation_result_comprehensive(self):
        """Test OperationResult model comprehensively."""
        # Test minimal constructor
        result = OperationResult(success=True, message="Success")
        assert result.success
        assert result.message == "Success"
        assert result.data is None
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        
        # Test full constructor
        result2 = OperationResult(
            success=False,
            message="Failed",
            data={"key": "value"},
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert not result2.success
        assert result2.message == "Failed"
        assert result2.data["key"] == "value"
        assert len(result2.errors) == 2
        assert len(result2.warnings) == 1
    
    def test_csv_template_comprehensive(self):
        """Test CSVTemplate model comprehensively."""
        template = CSVTemplate()
        
        # Test initial state
        assert len(template.headers) == 0
        assert len(template.teams) == 0
        assert len(template.records) == 0
        
        # Add teams and records
        team1 = Team(uid="team1", name="Team One")
        team2 = Team(uid="team2", name="Team Two")
        record1 = Record(uid="record1", title="Record One", folder_path="/path1")
        record2 = Record(uid="record2", title="Record Two", folder_path="/path2")
        
        template.teams = [team1, team2]
        template.records = [record1, record2]
        
        # Test generate_headers
        headers = template.generate_headers()
        expected_headers = ["record_uid", "title", "folder_path", "Team One", "Team Two"]
        assert headers == expected_headers
        
        # Test generate_row
        row = template.generate_row(record1)
        assert row["record_uid"] == "record1"
        assert row["title"] == "Record One"
        assert row["folder_path"] == "/path1"
        assert row["Team One"] == ""
        assert row["Team Two"] == ""
    
    def test_vault_data_comprehensive(self):
        """Test VaultData model comprehensively."""
        vault_data = VaultData()
        
        # Test initial state
        assert len(vault_data.root_folders) == 0
        assert len(vault_data.records_by_uid) == 0
        assert len(vault_data.teams_by_uid) == 0
        assert not vault_data.is_loaded()
        
        # Test summary
        summary = vault_data.summary()
        assert summary["teams"] == 0
        assert summary["records"] == 0
        assert summary["root_folders"] == 0
        
        # Test add_team
        team = vault_data.add_team("team1", "Team One")
        assert team.uid == "team1"
        assert team.name == "Team One"
        assert len(vault_data.teams_by_uid) == 1
        
        # Test add_record
        record = vault_data.add_record("record1", "Record One", "/path1")
        assert record.uid == "record1"
        assert record.title == "Record One"
        assert record.folder_path == "/path1"
        assert len(vault_data.records_by_uid) == 1
        
        # Test add_folder (root folder)
        root_folder = vault_data.add_folder("root1", "Root Folder")
        assert root_folder.uid == "root1"
        assert root_folder.name == "Root Folder"
        assert root_folder.parent_uid is None
        assert len(vault_data.root_folders) == 1
        
        # Test add_folder (child folder)
        child_folder = vault_data.add_folder("child1", "Child Folder", "root1")
        assert child_folder.uid == "child1"
        assert child_folder.parent_uid == "root1"
        assert len(root_folder.subfolders) == 1
        
        # Test find_folder_by_uid
        found_root = vault_data.find_folder_by_uid("root1")
        assert found_root is not None
        assert found_root.uid == "root1"
        
        found_child = vault_data.find_folder_by_uid("child1")
        assert found_child is not None
        assert found_child.uid == "child1"
        
        not_found = vault_data.find_folder_by_uid("nonexistent")
        assert not_found is None
        
        # Test get_team_by_name
        found_team = vault_data.get_team_by_name("Team One")
        assert found_team is not None
        assert found_team.uid == "team1"
        
        not_found_team = vault_data.get_team_by_name("Nonexistent Team")
        assert not_found_team is None
        
        # Test get_record_by_uid
        found_record = vault_data.get_record_by_uid("record1")
        assert found_record is not None
        assert found_record.uid == "record1"
        
        not_found_record = vault_data.get_record_by_uid("nonexistent")
        assert not_found_record is None
        
        # Test mark_loaded
        vault_data.mark_loaded()
        assert vault_data.is_loaded()
        
        # Test updated summary
        summary = vault_data.summary()
        assert summary["teams"] == 1
        assert summary["records"] == 1
        assert summary["root_folders"] == 1
        
        # Test clear
        vault_data.clear()
        assert len(vault_data.root_folders) == 0
        assert len(vault_data.records_by_uid) == 0
        assert len(vault_data.teams_by_uid) == 0
        assert not vault_data.is_loaded()


class TestConfigServiceCoverage:
    """Test ConfigService for full coverage."""
    
    def test_load_configuration_no_uid_no_record(self):
        """Test load_configuration when no config record exists."""
        service = ConfigService()
        
        with patch('keeper_auto.services.get_records', return_value=[]):
            result = service.load_configuration()
            assert result.success
            assert "not found" in result.message
            assert isinstance(result.data, ConfigRecord)
            assert len(result.warnings) == 1
    
    def test_load_configuration_find_by_title_success(self):
        """Test load_configuration finding config by title."""
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
        """Test load_configuration with valid JSON config."""
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
        """Test load_configuration with invalid JSON."""
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
        """Test load_configuration with empty record."""
        service = ConfigService()
        
        mock_record = Mock()
        mock_record.data = []
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert result.success
            assert "empty" in result.message
            assert len(result.warnings) == 1
    
    def test_load_configuration_no_json_field(self):
        """Test load_configuration with no JSON field."""
        service = ConfigService()
        
        mock_field = Mock()
        mock_field.type = 'text'
        mock_field.value = 'some text'
        
        mock_record = Mock()
        mock_record.data = [mock_field]
        
        with patch('keeper_auto.services.get_record', return_value=mock_record):
            result = service.load_configuration("test_uid")
            assert result.success
            assert "empty" in result.message
            assert len(result.warnings) == 1
    
    def test_load_configuration_api_exception(self):
        """Test load_configuration with API exception."""
        service = ConfigService()
        
        with patch('keeper_auto.services.get_record', side_effect=Exception("API Error")):
            result = service.load_configuration("test_uid")
            assert not result.success
            assert "Could not load configuration" in result.message
            assert len(result.errors) == 1
    
    def test_find_config_record_by_title_exception(self):
        """Test _find_config_record_by_title with exception."""
        service = ConfigService()
        
        with patch('keeper_auto.services.get_records', side_effect=Exception("Search failed")):
            result = service._find_config_record_by_title()
            assert result is None
    
    def test_find_config_record_by_title_custom_title(self):
        """Test _find_config_record_by_title with custom title."""
        service = ConfigService()
        
        mock_records = [
            {"uid": "config_uid", "title": "Custom-Config"},
        ]
        
        with patch('keeper_auto.services.get_records', return_value=mock_records):
            result = service._find_config_record_by_title("Custom-Config")
            assert result == "config_uid"


class TestVaultServiceCoverage:
    """Test VaultService for full coverage."""
    
    def test_load_vault_data_cached(self):
        """Test load_vault_data returns cached data."""
        service = VaultService()
        service.vault_data.mark_loaded()
        
        result = service.load_vault_data()
        assert result.is_loaded()
    
    def test_load_vault_data_force_reload(self):
        """Test load_vault_data with force_reload."""
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
            assert len(result.records_by_uid) == 1
    
    def test_load_vault_data_with_config_filtering(self):
        """Test load_vault_data with config filtering."""
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
            assert len(result.root_folders) == 1
            assert result.root_folders[0].uid == "folder1"
    
    def test_load_vault_data_missing_uids(self):
        """Test load_vault_data with missing UIDs."""
        service = VaultService()
        
        mock_folder_data = {
            "folders": [
                {"name": "Folder 1", "parent_uid": None},  # Missing uid
                {"uid": "folder2", "parent_uid": None}      # Missing name
            ],
            "records": [
                {"title": "Record 1", "folder_uid": "folder1"},  # Missing uid
                {"uid": "record2", "folder_uid": "folder1"}       # Missing title
            ]
        }
        mock_teams = [
            {"team_name": "Team 1"},  # Missing team_uid
            {"team_uid": "team2"}     # Missing team_name
        ]
        
        with patch('keeper_auto.services.get_folder_data', return_value=mock_folder_data), \
             patch('keeper_auto.services.get_teams', return_value=mock_teams):
            result = service.load_vault_data()
            
            # Should skip items with missing required fields
            assert len(result.teams_by_uid) == 0
            assert len(result.root_folders) == 0
            assert len(result.records_by_uid) == 0
    
    def test_load_vault_data_api_exception(self):
        """Test load_vault_data with API exception."""
        service = VaultService()
        
        with patch('keeper_auto.services.get_folder_data', side_effect=Exception("API Error")):
            with pytest.raises(APIError):
                service.load_vault_data()
    
    def test_build_folder_path_complex_hierarchy(self):
        """Test _build_folder_path with complex hierarchy."""
        service = VaultService()
        
        # Build complex folder hierarchy
        service.vault_data.add_folder("root", "Root")
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
        """Test _build_folder_path edge cases."""
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
        assert path == "/Orphan"
    
    def test_get_vault_summary_not_loaded(self):
        """Test get_vault_summary when not loaded."""
        service = VaultService()
        
        mock_folder_data = {"folders": [], "records": []}
        mock_teams = []
        
        with patch('keeper_auto.services.get_folder_data', return_value=mock_folder_data), \
             patch('keeper_auto.services.get_teams', return_value=mock_teams):
            summary = service.get_vault_summary()
            assert isinstance(summary, dict)
            assert "teams" in summary
            assert "records" in summary
            assert "root_folders" in summary 