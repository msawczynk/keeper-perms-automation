"""Tests for Keeper client functionality."""

import pytest
from unittest.mock import patch, MagicMock
from keeper_auto.keeper_client import get_record, get_teams, get_records, find_team_by_name


class TestKeeperClient:
    """Test Keeper client API functions."""
    
    @patch('keeper_auto.keeper_client.get_client')
    def test_get_record_success(self, mock_get_client):
        """Test successful record retrieval."""
        # Mock the SDK and record cache
        mock_sdk = MagicMock()
        mock_sdk.record_cache = {
            'test_uid': MagicMock(uid='test_uid', title='Test Record')
        }
        mock_get_client.return_value = mock_sdk
        
        # Test the function
        result = get_record('test_uid')
        
        # Verify
        assert result is not None
        mock_get_client.assert_called_once()
    
    @patch('keeper_auto.keeper_client.get_client')
    def test_get_record_not_found(self, mock_get_client):
        """Test record not found scenario."""
        # Mock the SDK with empty cache
        mock_sdk = MagicMock()
        mock_sdk.record_cache = {}
        mock_get_client.return_value = mock_sdk
        
        # Test the function should return None
        result = get_record('nonexistent_uid')
        assert result is None
    
    @patch('keeper_auto.keeper_client.get_client')
    def test_get_teams_success(self, mock_get_client):
        """Test successful teams retrieval."""
        # Mock the SDK and team cache
        mock_sdk = MagicMock()
        mock_sdk.team_cache = {
            'team1': {'team_uid': 'team1', 'team_name': 'Team 1'},
            'team2': {'team_uid': 'team2', 'team_name': 'Team 2'}
        }
        mock_get_client.return_value = mock_sdk
        
        # Test the function
        result = get_teams()
        
        # Verify
        assert len(result) == 2
        mock_get_client.assert_called_once()
    
    @patch('keeper_auto.keeper_client.get_client')
    def test_get_teams_no_cache(self, mock_get_client):
        """Test teams retrieval with no cache."""
        # Mock the SDK with no team cache
        mock_sdk = MagicMock()
        delattr(mock_sdk, 'team_cache')  # Remove the attribute
        mock_get_client.return_value = mock_sdk
        
        # Test the function
        result = get_teams()
        
        # Verify returns empty list
        assert result == []
        mock_get_client.assert_called_once()
    
    @patch('keeper_auto.keeper_client.get_client')
    def test_get_records_success(self, mock_get_client):
        """Test successful records retrieval."""
        # Mock the SDK and record cache
        mock_record = MagicMock()
        mock_record.uid = 'record1'
        mock_record.title = 'Test Record'
        mock_record.folder_uid = 'folder1'
        
        mock_sdk = MagicMock()
        mock_sdk.record_cache = {'record1': mock_record}
        mock_get_client.return_value = mock_sdk
        
        # Test the function
        result = get_records()
        
        # Verify
        assert len(result) == 1
        assert result[0]['uid'] == 'record1'
        assert result[0]['title'] == 'Test Record'
        assert result[0]['folder_uid'] == 'folder1'
        mock_get_client.assert_called_once()
    
    @patch('keeper_auto.keeper_client.get_teams')
    def test_find_team_by_name_success(self, mock_get_teams):
        """Test successful team finding by name."""
        # Mock teams data
        mock_get_teams.return_value = [
            {'team_uid': 'team1', 'team_name': 'Team 1'},
            {'team_uid': 'team2', 'team_name': 'Team 2'}
        ]
        
        # Test the function
        result = find_team_by_name('Team 1')
        
        # Verify
        assert result is not None
        assert result['team_uid'] == 'team1'
        assert result['team_name'] == 'Team 1'
    
    @patch('keeper_auto.keeper_client.get_teams')
    def test_find_team_by_name_not_found(self, mock_get_teams):
        """Test team not found by name."""
        # Mock teams data
        mock_get_teams.return_value = [
            {'team_uid': 'team1', 'team_name': 'Team 1'}
        ]
        
        # Test the function
        result = find_team_by_name('Nonexistent Team')
        
        # Verify
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__]) 