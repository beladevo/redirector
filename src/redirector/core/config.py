"""Configuration management for redirector."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from datetime import datetime


@dataclass
class RedirectorConfig:
    """Configuration for redirector application."""
    
    # Core settings
    redirect_url: str = "https://example.com"
    redirect_port: int = 8080
    dashboard_port: int = 3000
    
    # Campaign settings
    campaign: Optional[str] = None
    
    # Dashboard settings
    dashboard_raw: bool = False
    dashboard_auth: Optional[str] = None
    
    # Logging settings
    store_body: bool = False
    database_path: str = "logs.db"
    
    # Tunnel settings
    tunnel: bool = False
    
    # Runtime settings
    host: str = "0.0.0.0"
    log_level: str = "info"
    
    # Security settings
    max_body_size: int = 10 * 1024 * 1024  # 10MB
    rate_limit: Optional[int] = None  # requests per minute
    
    def __post_init__(self) -> None:
        """Set default campaign name if not provided."""
        if not self.campaign:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M")
            self.campaign = f"campaign-{timestamp}"
    
    @classmethod
    def from_file(cls, config_path: Path) -> "RedirectorConfig":
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return cls(**data)
    
    def to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict, excluding None values
        data = {
            k: v for k, v in self.__dict__.items() 
            if v is not None and not k.startswith('_')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=True)
    
    @property
    def auth_user(self) -> Optional[str]:
        """Extract username from dashboard_auth."""
        if self.dashboard_auth and ':' in self.dashboard_auth:
            return self.dashboard_auth.split(':', 1)[0]
        return None
    
    @property
    def auth_password(self) -> Optional[str]:
        """Extract password from dashboard_auth."""
        if self.dashboard_auth and ':' in self.dashboard_auth:
            return self.dashboard_auth.split(':', 1)[1]
        return None
    
    @property
    def database_url(self) -> str:
        """Get SQLAlchemy database URL."""
        if self.database_path.startswith("sqlite:"):
            return self.database_path
        return f"sqlite:///{self.database_path}"
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.redirect_url:
            raise ValueError("redirect_url is required")
        
        if not (1 <= self.redirect_port <= 65535):
            raise ValueError("redirect_port must be between 1 and 65535")
        
        if not (1 <= self.dashboard_port <= 65535):
            raise ValueError("dashboard_port must be between 1 and 65535")
        
        if self.redirect_port == self.dashboard_port:
            raise ValueError("redirect_port and dashboard_port must be different")
        
        if self.dashboard_auth and ':' not in self.dashboard_auth:
            raise ValueError("dashboard_auth must be in format 'user:password'")


# Default configuration template
DEFAULT_CONFIG = """# Redirector Configuration
# Professional URL redirector with campaign tracking and analytics

# Core settings
redirect_url: https://example.com
redirect_port: 8080
dashboard_port: 3000

# Campaign settings
campaign: null  # Will auto-generate timestamped name

# Dashboard settings
dashboard_raw: false
dashboard_auth: null  # Format: "username:password"

# Logging settings
store_body: false  # WARNING: Only enable in controlled lab environments
database_path: logs.db

# Tunnel settings
tunnel: false

# Runtime settings
host: 0.0.0.0
log_level: info

# Security settings
max_body_size: 10485760  # 10MB
rate_limit: null  # requests per minute
"""