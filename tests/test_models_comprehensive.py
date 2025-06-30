"""
Comprehensive tests for models to improve code coverage.
"""

import pytest
from keeper_auto.models import VaultData, ValidationResult, OperationResult, CSVTemplate, ConfigRecord, Record, Team, VaultFolder
from keeper_auto.exceptions import APIError, AuthenticationError, ConfigurationError, ValidationError, OperationError, DataError, NetworkError, PermissionError


class TestExceptions:
    """Test all exception classes for coverage."""
    
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


class TestModelClasses:
    """Test individual model classes."""
    
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


class TestVaultData:
    """Test VaultData model comprehensively."""
    
    def test_initial_state(self):
        vault_data = VaultData()
        assert not vault_data.is_loaded()
        assert vault_data.summary() == {"teams": 0, "folders": 0, "records": 0}
        assert vault_data.get_team_by_uid("nonexistent") is None
        assert vault_data.find_folder_by_uid("nonexistent") is None
        assert vault_data.get_record_by_uid("nonexistent") is None
    
    def test_add_and_retrieve_data(self):
        vault_data = VaultData()
        
        # Add data
        vault_data.add_team("team1", "Team One")
        vault_data.add_folder("folder1", "Folder One", None)
        vault_data.add_record("record1", "Record One", "/path")
        
        # Test retrieval
        team = vault_data.get_team_by_uid("team1")
        assert team is not None
        assert team.name == "Team One"
        
        folder = vault_data.find_folder_by_uid("folder1")
        assert folder is not None
        assert folder.name == "Folder One"
        
        record = vault_data.get_record_by_uid("record1")
        assert record is not None
        assert record.title == "Record One"
        
        # Test summary
        summary = vault_data.summary()
        assert summary["teams"] == 1
        assert summary["folders"] == 1
        assert summary["records"] == 1
    
    def test_mark_loaded_and_clear(self):
        vault_data = VaultData()
        
        # Add some data
        vault_data.add_team("team1", "Team One")
        vault_data.mark_loaded()
        assert vault_data.is_loaded()
        
        # Clear data
        vault_data.clear()
        assert not vault_data.is_loaded()
        assert len(vault_data.teams_by_uid) == 0
        assert len(vault_data.folders_by_uid) == 0
        assert len(vault_data.records_by_uid) == 0


class TestValidationResult:
    """Test ValidationResult model."""
    
    def test_initial_state(self):
        result = ValidationResult()
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.metadata == {}
    
    def test_add_errors_and_warnings(self):
        result = ValidationResult()
        
        result.add_error("Error 1")
        result.add_error("Error 2")
        result.add_warning("Warning 1")
        
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "Error 1" in result.errors
        assert "Warning 1" in result.warnings
    
    def test_constructor_with_params(self):
        result = ValidationResult(
            is_valid=False,
            errors=["Initial error"],
            warnings=["Initial warning"],
            metadata={"key": "value"}
        )
        assert not result.is_valid
        assert "Initial error" in result.errors
        assert "Initial warning" in result.warnings
        assert result.metadata["key"] == "value"


class TestOperationResult:
    """Test OperationResult model."""
    
    def test_minimal_result(self):
        result = OperationResult(success=True, message="Success")
        assert result.success
        assert result.message == "Success"
        assert result.data is None
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_full_result(self):
        result = OperationResult(
            success=False,
            message="Failed",
            data={"key": "value"},
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert not result.success
        assert result.message == "Failed"
        assert result.data["key"] == "value"
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestCSVTemplate:
    """Test CSVTemplate model."""
    
    def test_initial_state(self):
        template = CSVTemplate()
        expected_headers = ["record_uid", "title", "folder_path"]
        assert template.headers == expected_headers
        assert len(template.rows) == 0
    
    def test_add_rows(self):
        template = CSVTemplate()
        
        # Add first row
        template.add_row("uid1", "Title 1", "/path1", {"Team1": "ro", "Team2": "rw"})
        assert len(template.rows) == 1
        
        row1 = template.rows[0]
        assert row1["record_uid"] == "uid1"
        assert row1["title"] == "Title 1"
        assert row1["folder_path"] == "/path1"
        assert row1["Team1"] == "ro"
        assert row1["Team2"] == "rw"
        
        # Add second row with different teams
        template.add_row("uid2", "Title 2", "/path2", {"Team1": "rws"})
        assert len(template.rows) == 2
        
        row2 = template.rows[1]
        assert row2["record_uid"] == "uid2"
        assert row2["Team1"] == "rws"
        assert "Team2" not in row2  # Should not have Team2 permission
    
    def test_add_row_no_permissions(self):
        template = CSVTemplate()
        template.add_row("uid1", "Title 1", "/path1", {})
        
        assert len(template.rows) == 1
        row = template.rows[0]
        assert row["record_uid"] == "uid1"
        assert row["title"] == "Title 1"
        assert row["folder_path"] == "/path1"


class TestConfigRecord:
    """Test ConfigRecord model."""
    
    def test_default_values(self):
        config = ConfigRecord()
        assert config.root_folder_name == "[Perms]"
        assert config.included_teams is None
        assert config.included_folders is None
        assert config.excluded_folders == []
    
    def test_custom_values(self):
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
    
    def test_partial_custom_values(self):
        config = ConfigRecord(
            root_folder_name="[Partial]",
            included_teams=["team1"]
        )
        assert config.root_folder_name == "[Partial]"
        assert config.included_teams == ["team1"]
        assert config.included_folders is None  # Should remain None
        assert config.excluded_folders == []    # Should remain default 