"""Tests for configuration management."""
import tempfile
from pathlib import Path

import pytest

from redirector.core.config import RedirectorConfig, DEFAULT_CONFIG


def test_default_config():
    """Test default configuration values."""
    config = RedirectorConfig()
    
    assert config.redirect_url == "https://example.com"
    assert config.redirect_port == 8080
    assert config.dashboard_port == 3000
    assert config.campaign is not None  # Auto-generated
    assert config.dashboard_raw is False
    assert config.dashboard_auth is None
    assert config.store_body is False
    assert config.database_path == "logs.db"
    assert config.tunnel is False


def test_config_campaign_generation():
    """Test automatic campaign name generation."""
    config = RedirectorConfig()
    assert config.campaign.startswith("campaign-")
    assert len(config.campaign) > 10  # Should include timestamp


def test_config_auth_properties():
    """Test auth property extraction."""
    config = RedirectorConfig(dashboard_auth="admin:secret123")
    
    assert config.auth_user == "admin"
    assert config.auth_password == "secret123"
    
    # Test no auth
    config_no_auth = RedirectorConfig()
    assert config_no_auth.auth_user is None
    assert config_no_auth.auth_password is None


def test_config_database_url():
    """Test database URL generation."""
    config = RedirectorConfig(database_path="test.db")
    assert config.database_url == "sqlite:///test.db"
    
    # Test with full SQLite URL
    config_full = RedirectorConfig(database_path="sqlite:///full/path.db")
    assert config_full.database_url == "sqlite:///full/path.db"


def test_config_validation():
    """Test configuration validation."""
    # Valid config should not raise
    config = RedirectorConfig()
    config.validate()
    
    # Invalid redirect URL
    config_invalid_url = RedirectorConfig(redirect_url="")
    with pytest.raises(ValueError, match="redirect_url is required"):
        config_invalid_url.validate()
    
    # Invalid port ranges
    config_invalid_port = RedirectorConfig(redirect_port=0)
    with pytest.raises(ValueError, match="redirect_port must be between"):
        config_invalid_port.validate()
    
    config_invalid_port2 = RedirectorConfig(dashboard_port=70000)
    with pytest.raises(ValueError, match="dashboard_port must be between"):
        config_invalid_port2.validate()
    
    # Same ports
    config_same_ports = RedirectorConfig(redirect_port=8080, dashboard_port=8080)
    with pytest.raises(ValueError, match="redirect_port and dashboard_port must be different"):
        config_same_ports.validate()
    
    # Invalid auth format
    config_invalid_auth = RedirectorConfig(dashboard_auth="invalid")
    with pytest.raises(ValueError, match="dashboard_auth must be in format"):
        config_invalid_auth.validate()


def test_config_file_operations():
    """Test loading and saving configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.yaml"
        
        # Create and save config
        original_config = RedirectorConfig(
            redirect_url="https://test.com",
            redirect_port=9090,
            dashboard_port=4000,
            campaign="test-campaign",
            dashboard_auth="user:pass"
        )
        original_config.to_file(config_path)
        
        # Load config
        loaded_config = RedirectorConfig.from_file(config_path)
        
        assert loaded_config.redirect_url == "https://test.com"
        assert loaded_config.redirect_port == 9090
        assert loaded_config.dashboard_port == 4000
        assert loaded_config.campaign == "test-campaign"
        assert loaded_config.dashboard_auth == "user:pass"


def test_config_file_not_found():
    """Test error handling for non-existent config file."""
    non_existent_path = Path("/non/existent/config.yaml")
    
    with pytest.raises(FileNotFoundError):
        RedirectorConfig.from_file(non_existent_path)


def test_default_config_template():
    """Test that default config template is valid YAML."""
    import yaml
    
    # Should parse without errors
    parsed = yaml.safe_load(DEFAULT_CONFIG)
    assert isinstance(parsed, dict)
    assert "redirect_url" in parsed
    assert "redirect_port" in parsed