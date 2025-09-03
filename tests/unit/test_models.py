"""Tests for database models."""
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from redirector.core.models import Base, Campaign, LogEntry, DatabaseManager


@pytest.fixture
def db_manager():
    """Create in-memory database for testing."""
    manager = DatabaseManager("sqlite:///:memory:")
    manager.create_tables()
    return manager


@pytest.fixture
def mock_request():
    """Create mock FastAPI request for testing."""
    request = Mock()
    request.method = "GET"
    request.url = "https://example.com/test?param=value"
    request.client.host = "192.168.1.100"
    request.headers = {
        "User-Agent": "Mozilla/5.0 Test Browser",
        "Referer": "https://google.com",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Forwarded-For": "203.0.113.1",
        "Authorization": "Bearer secret-token",  # Should be filtered
    }
    return request


class TestCampaign:
    """Test Campaign model."""
    
    def test_campaign_creation(self):
        """Test creating a campaign."""
        campaign = Campaign(
            name="test-campaign",
            description="Test campaign description"
        )
        
        assert campaign.name == "test-campaign"
        assert campaign.description == "Test campaign description"
        assert campaign.is_active is True
    
    def test_campaign_to_dict(self):
        """Test campaign serialization."""
        now = datetime.utcnow()
        campaign = Campaign(
            id=1,
            name="test-campaign",
            description="Test description",
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        result = campaign.to_dict()
        
        assert result["id"] == 1
        assert result["name"] == "test-campaign"
        assert result["description"] == "Test description"
        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()
        assert result["is_active"] is True


class TestLogEntry:
    """Test LogEntry model."""
    
    def test_log_entry_from_request(self, mock_request):
        """Test creating LogEntry from request."""
        log_entry = LogEntry.from_request(
            request=mock_request,
            campaign="test-campaign",
            store_body=False,
            response_time_ms=250
        )
        
        assert log_entry.ip == "192.168.1.100"
        assert log_entry.x_forwarded_for == "203.0.113.1"
        assert log_entry.user_agent == "Mozilla/5.0 Test Browser"
        assert log_entry.method == "GET"
        assert log_entry.url == "https://example.com/test?param=value"
        assert log_entry.path == "/test"
        assert log_entry.query == "param=value"
        assert log_entry.referer == "https://google.com"
        assert log_entry.accept_language == "en-US,en;q=0.9"
        assert log_entry.campaign == "test-campaign"
        assert log_entry.response_time_ms == 250
        
        # Check headers are properly filtered
        headers = json.loads(log_entry.headers)
        assert "User-Agent" in headers
        assert "Authorization" not in headers  # Should be filtered out
    
    def test_log_entry_to_dict(self):
        """Test LogEntry serialization."""
        now = datetime.utcnow()
        log_entry = LogEntry(
            id=1,
            timestamp=now,
            ip="192.168.1.1",
            user_agent="Test Agent",
            method="POST",
            url="https://example.com/api",
            path="/api",
            query="key=value",
            headers='{"Content-Type": "application/json"}',
            campaign="test-campaign",
            response_time_ms=150
        )
        
        result = log_entry.to_dict()
        
        assert result["id"] == 1
        assert result["timestamp"] == now.isoformat()
        assert result["ip"] == "192.168.1.1"
        assert result["user_agent"] == "Test Agent"
        assert result["method"] == "POST"
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["campaign"] == "test-campaign"
        assert result["response_time_ms"] == 150
    
    def test_log_entry_to_csv_row(self):
        """Test LogEntry CSV serialization."""
        now = datetime.utcnow()
        log_entry = LogEntry(
            id=1,
            timestamp=now,
            ip="192.168.1.1",
            method="GET",
            path="/test",
            campaign="csv-test"
        )
        
        result = log_entry.to_csv_row()
        
        assert result["id"] == 1
        assert result["timestamp"] == now.isoformat()
        assert result["ip"] == "192.168.1.1"
        assert result["method"] == "GET"
        assert result["path"] == "/test"
        assert result["campaign"] == "csv-test"
        assert result["has_body"] == "false"


class TestDatabaseManager:
    """Test DatabaseManager functionality."""
    
    def test_ensure_campaign_exists(self, db_manager):
        """Test campaign creation."""
        db_manager.ensure_campaign_exists("test-campaign", "Test description")
        
        campaigns = db_manager.get_campaigns()
        assert len(campaigns) == 1
        assert campaigns[0].name == "test-campaign"
        assert campaigns[0].description == "Test description"
        
        # Should not create duplicate
        db_manager.ensure_campaign_exists("test-campaign", "Different description")
        campaigns = db_manager.get_campaigns()
        assert len(campaigns) == 1
    
    def test_get_campaigns(self, db_manager):
        """Test retrieving campaigns."""
        # Create test campaigns
        session = db_manager.get_session()
        try:
            campaign1 = Campaign(name="active-campaign", is_active=True)
            campaign2 = Campaign(name="inactive-campaign", is_active=False)
            session.add_all([campaign1, campaign2])
            session.commit()
        finally:
            session.close()
        
        # Get active campaigns only
        active_campaigns = db_manager.get_campaigns(active_only=True)
        assert len(active_campaigns) == 1
        assert active_campaigns[0].name == "active-campaign"
        
        # Get all campaigns
        all_campaigns = db_manager.get_campaigns(active_only=False)
        assert len(all_campaigns) == 2
    
    def test_search_logs(self, db_manager):
        """Test log searching functionality."""
        session = db_manager.get_session()
        now = datetime.utcnow()
        
        try:
            # Create test logs
            logs = [
                LogEntry(
                    timestamp=now - timedelta(hours=1),
                    ip="192.168.1.1",
                    method="GET",
                    path="/test1",
                    campaign="campaign1"
                ),
                LogEntry(
                    timestamp=now,
                    ip="192.168.1.2",
                    method="POST",
                    path="/test2",
                    campaign="campaign2"
                ),
                LogEntry(
                    timestamp=now + timedelta(hours=1),
                    ip="192.168.1.1",
                    method="GET",
                    path="/test3",
                    campaign="campaign1"
                ),
            ]
            session.add_all(logs)
            session.commit()
        finally:
            session.close()
        
        # Test campaign filter
        results = db_manager.search_logs(campaign="campaign1")
        assert len(results) == 2
        
        # Test method filter
        results = db_manager.search_logs(method_filter="POST")
        assert len(results) == 1
        assert results[0].method == "POST"
        
        # Test IP filter
        results = db_manager.search_logs(ip_filter="192.168.1.2")
        assert len(results) == 1
        assert results[0].ip == "192.168.1.2"
        
        # Test time range
        results = db_manager.search_logs(
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=30)
        )
        assert len(results) == 1
        
        # Test pagination
        results = db_manager.search_logs(limit=1, offset=1)
        assert len(results) == 1
    
    def test_count_logs(self, db_manager):
        """Test log counting with filters."""
        session = db_manager.get_session()
        
        try:
            # Create test logs
            logs = [
                LogEntry(method="GET", campaign="test1", ip="1.1.1.1"),
                LogEntry(method="POST", campaign="test1", ip="1.1.1.2"),
                LogEntry(method="GET", campaign="test2", ip="1.1.1.1"),
            ]
            session.add_all(logs)
            session.commit()
        finally:
            session.close()
        
        # Test total count
        total = db_manager.count_logs()
        assert total == 3
        
        # Test campaign filter
        campaign_count = db_manager.count_logs(campaign="test1")
        assert campaign_count == 2
        
        # Test method filter
        method_count = db_manager.count_logs(method_filter="GET")
        assert method_count == 2
        
        # Test IP filter
        ip_count = db_manager.count_logs(ip_filter="1.1.1.1")
        assert ip_count == 2
    
    def test_get_campaign_stats(self, db_manager):
        """Test campaign statistics generation."""
        session = db_manager.get_session()
        now = datetime.utcnow()
        
        try:
            # Create test data
            logs = [
                LogEntry(
                    timestamp=now,
                    method="GET",
                    user_agent="Chrome Browser",
                    campaign="stats-test"
                ),
                LogEntry(
                    timestamp=now,
                    method="POST",
                    user_agent="Firefox Browser",
                    campaign="stats-test"
                ),
                LogEntry(
                    timestamp=now - timedelta(hours=25),  # Outside 24h window
                    method="GET",
                    user_agent="Chrome Browser",
                    campaign="stats-test"
                ),
            ]
            session.add_all(logs)
            session.commit()
        finally:
            session.close()
        
        stats = db_manager.get_campaign_stats("stats-test")
        
        assert stats["total_requests"] == 3
        assert stats["recent_requests"] == 2  # Only last 24h
        assert stats["methods"]["GET"] == 2
        assert stats["methods"]["POST"] == 1
        assert "Chrome Browser" in stats["top_user_agents"]
        assert stats["campaign"] == "stats-test"