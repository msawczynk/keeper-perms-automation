"""Simple tests to improve code coverage."""

from keeper_auto.models import VaultData, ValidationResult, OperationResult, ConfigRecord
from keeper_auto.exceptions import APIError, AuthenticationError


def test_api_error_with_response_command():
    """Test APIError with additional details."""
    resp = {"error": "Bad Request"}
    error = APIError("Test error", response=resp, command="GET /endpoint")
    assert str(error) == "Test error"
    assert error.details["response"] == resp
    assert error.details["command"] == "GET /endpoint"


def test_api_error_basic():
    """Test basic APIError."""
    error = APIError("Test error")
    assert str(error) == "Test error"


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError("Auth failed")
    assert str(error) == "Auth failed"


def test_vault_data_comprehensive():
    """Test VaultData model."""
    vault_data = VaultData()
    
    # Test initial state
    assert not vault_data.is_loaded()
    assert vault_data.summary() == {"teams": 0, "records": 0, "root_folders": 0}
    assert vault_data.get_team_by_name("nonexistent") is None
    assert vault_data.get_record_by_uid("nonexistent") is None
    assert vault_data.find_folder_by_uid("nonexistent") is None
    
    # Add data
    team = vault_data.add_team("team1", "Team One")
    assert team.name == "Team One"
    
    record = vault_data.add_record("record1", "Record One", "/path")
    assert record.title == "Record One"
    
    folder = vault_data.add_folder("folder1", "Folder One")
    assert folder.name == "Folder One"
    
    # Test retrieval
    found_team = vault_data.get_team_by_name("Team One")
    assert found_team is not None
    assert found_team.uid == "team1"
    
    found_record = vault_data.get_record_by_uid("record1")
    assert found_record is not None
    assert found_record.title == "Record One"
    
    found_folder = vault_data.find_folder_by_uid("folder1")
    assert found_folder is not None
    assert found_folder.name == "Folder One"
    
    # Test mark loaded
    vault_data.mark_loaded()
    assert vault_data.is_loaded()
    
    # Test clear
    vault_data.clear()
    assert not vault_data.is_loaded()
    assert len(vault_data.teams_by_uid) == 0


def test_validation_result():
    """Test ValidationResult model."""
    result = ValidationResult(is_valid=True)
    assert result.is_valid
    assert not result.has_issues()
    
    result.add_error("Test error")
    assert not result.is_valid
    assert result.has_issues()
    
    result.add_warning("Test warning")
    assert result.has_issues()


def test_operation_result():
    """Test OperationResult model."""
    result = OperationResult(success=True, message="Success")
    assert result.success
    assert result.message == "Success"
    
    result2 = OperationResult(
        success=False,
        message="Failed",
        data={"key": "value"},
        errors=["Error 1"],
        warnings=["Warning 1"]
    )
    assert not result2.success
    assert result2.data is not None
    assert result2.data["key"] == "value"


def test_config_record():
    """Test ConfigRecord model."""
    config = ConfigRecord()
    assert config.root_folder_name == "[Perms]"
    assert config.included_teams is None
    assert config.excluded_folders == []
    
    config2 = ConfigRecord(
        root_folder_name="[Custom]",
        included_teams=["team1"],
        excluded_folders=["folder1"]
    )
    assert config2.root_folder_name == "[Custom]"
    assert config2.included_teams == ["team1"]
    assert config2.excluded_folders == ["folder1"] 