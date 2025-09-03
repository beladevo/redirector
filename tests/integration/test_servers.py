"""Integration tests for redirect and dashboard servers."""
import pytest
import httpx
from fastapi.testclient import TestClient

from redirector.core.config import RedirectorConfig
from redirector.servers.redirect import create_redirect_app
from redirector.servers.dashboard import create_dashboard_app


@pytest.fixture
def test_config():
    """Create test configuration."""
    return RedirectorConfig(
        redirect_url="https://test-target.com",
        campaign="test-campaign",
        database_path="sqlite:///:memory:",
        dashboard_auth=None,
        store_body=False
    )


@pytest.fixture
def redirect_client(test_config):
    """Create test client for redirect server."""
    app = create_redirect_app(test_config)
    return TestClient(app)


@pytest.fixture
def dashboard_client(test_config):
    """Create test client for dashboard server."""
    app = create_dashboard_app(test_config)
    return TestClient(app)


class TestRedirectServer:
    """Test redirect server functionality."""
    
    def test_redirect_functionality(self, redirect_client):
        """Test basic redirect functionality."""
        response = redirect_client.get("/", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "https://test-target.com"
    
    def test_redirect_with_path(self, redirect_client):
        """Test redirect preserves target URL regardless of path."""
        response = redirect_client.get("/some/path", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "https://test-target.com"
    
    def test_redirect_with_query_params(self, redirect_client):
        """Test redirect with query parameters."""
        response = redirect_client.get("/test?param=value&other=data", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers["location"] == "https://test-target.com"
    
    def test_redirect_different_methods(self, redirect_client):
        """Test redirect works with different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        
        for method in methods:
            if method == "HEAD":
                response = redirect_client.head("/", follow_redirects=False)
            elif method == "OPTIONS":
                response = redirect_client.options("/", follow_redirects=False)
            else:
                response = redirect_client.request(method, "/", follow_redirects=False)
            
            assert response.status_code == 302
            assert response.headers["location"] == "https://test-target.com"
    
    def test_redirect_health_endpoint(self, redirect_client):
        """Test redirect server health endpoint."""
        response = redirect_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "redirect"
        assert data["campaign"] == "test-campaign"
    
    def test_redirect_headers(self, redirect_client):
        """Test redirect response includes cache control headers."""
        response = redirect_client.get("/", follow_redirects=False)
        
        assert response.status_code == 302
        assert response.headers.get("cache-control") == "no-cache, no-store, must-revalidate"
        assert response.headers.get("pragma") == "no-cache"
        assert response.headers.get("expires") == "0"


class TestDashboardServer:
    """Test dashboard server functionality."""
    
    def test_dashboard_home_page(self, dashboard_client):
        """Test dashboard home page loads."""
        response = dashboard_client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_dashboard_health_endpoint(self, dashboard_client):
        """Test dashboard health endpoint."""
        response = dashboard_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "dashboard"
        assert data["campaign"] == "test-campaign"
    
    def test_api_health_endpoint(self, dashboard_client):
        """Test API health endpoint."""
        response = dashboard_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "dashboard"
    
    def test_api_campaigns_endpoint(self, dashboard_client):
        """Test campaigns API endpoint."""
        response = dashboard_client.get("/api/campaigns")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_api_logs_endpoint(self, dashboard_client):
        """Test logs API endpoint."""
        response = dashboard_client.get("/api/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
    
    def test_api_stats_endpoint(self, dashboard_client):
        """Test stats API endpoint."""
        response = dashboard_client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "recent_requests" in data
        assert "methods" in data
        assert "top_user_agents" in data
    
    def test_api_create_campaign(self, dashboard_client):
        """Test creating campaign via API."""
        campaign_data = {
            "name": "api-test-campaign",
            "description": "Test campaign created via API"
        }
        
        response = dashboard_client.post("/api/campaigns", json=campaign_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "api-test-campaign"
        assert data["description"] == "Test campaign created via API"
        assert data["is_active"] is True
    
    def test_api_create_duplicate_campaign(self, dashboard_client):
        """Test creating duplicate campaign returns error."""
        campaign_data = {
            "name": "duplicate-campaign",
            "description": "First campaign"
        }
        
        # Create first campaign
        response1 = dashboard_client.post("/api/campaigns", json=campaign_data)
        assert response1.status_code == 200
        
        # Try to create duplicate
        response2 = dashboard_client.post("/api/campaigns", json=campaign_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    def test_api_logs_filtering(self, dashboard_client):
        """Test logs API filtering."""
        # Test campaign filter
        response = dashboard_client.get("/api/logs?campaign=nonexistent")
        assert response.status_code == 200
        
        # Test pagination
        response = dashboard_client.get("/api/logs?page=1&per_page=10")
        assert response.status_code == 200
        
        # Test method filter
        response = dashboard_client.get("/api/logs?method_filter=GET")
        assert response.status_code == 200
        
        # Test invalid pagination
        response = dashboard_client.get("/api/logs?page=0")
        assert response.status_code == 422  # Validation error
    
    def test_api_export_csv(self, dashboard_client):
        """Test CSV export functionality."""
        response = dashboard_client.get("/api/logs/export.csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
    
    def test_api_export_jsonl(self, dashboard_client):
        """Test JSONL export functionality."""
        response = dashboard_client.get("/api/logs/export.jsonl")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/jsonl; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]


class TestServerIntegration:
    """Test integration between redirect and dashboard servers."""
    
    @pytest.mark.integration
    def test_redirect_creates_log_entry(self, redirect_client, dashboard_client):
        """Test that redirect requests create log entries viewable in dashboard."""
        # Make request to redirect server
        redirect_response = redirect_client.get(
            "/test-path?param=value",
            headers={"User-Agent": "Test-Integration-Browser"}
        )
        
        assert redirect_response.status_code == 302
        
        # Check log entry was created via dashboard API
        logs_response = dashboard_client.get("/api/logs")
        assert logs_response.status_code == 200
        
        logs_data = logs_response.json()
        
        # Should have at least one log entry
        assert logs_data["total"] >= 1
        
        # Find our test request
        test_log = None
        for log in logs_data["logs"]:
            if "Test-Integration-Browser" in (log.get("user_agent") or ""):
                test_log = log
                break
        
        assert test_log is not None
        assert test_log["method"] == "GET"
        assert test_log["path"] == "/test-path"
        assert test_log["query"] == "param=value"
        assert test_log["campaign"] == "test-campaign"