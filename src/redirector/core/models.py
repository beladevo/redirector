"""Database models for redirector."""
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import hashlib
import base64
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, 
    create_engine, Index, func, desc, asc
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

Base = declarative_base()


class Campaign(Base):
    """Campaign model for organizing redirect logs."""
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }


class LogEntry(Base):
    """Enhanced log entry model with comprehensive request tracking."""
    __tablename__ = "logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Request identification
    ip = Column(String(64), index=True)
    x_forwarded_for = Column(String(255))
    user_agent = Column(Text)
    
    # Request details
    method = Column(String(10), index=True)
    url = Column(Text, nullable=False)
    path = Column(String(2048), index=True)
    query = Column(Text)
    
    # Headers and body
    headers = Column(Text)  # JSON string
    body_digest = Column(String(64))  # SHA256 hash
    body_content = Column(Text, nullable=True)  # Base64 encoded body (optional)
    
    # Additional tracking
    referer = Column(Text)
    accept_language = Column(String(255))
    
    # Campaign association
    campaign = Column(String(255), nullable=False, index=True)
    
    # Performance tracking
    response_time_ms = Column(Integer)
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_campaign', 'timestamp', 'campaign'),
        Index('idx_ip_campaign', 'ip', 'campaign'),
        Index('idx_path_campaign', 'path', 'campaign'),
        Index('idx_method_campaign', 'method', 'campaign'),
    )
    
    @classmethod
    def from_request(
        cls, 
        request, 
        campaign: str, 
        store_body: bool = False,
        response_time_ms: Optional[int] = None
    ) -> "LogEntry":
        """Create LogEntry from FastAPI request."""
        from urllib.parse import urlparse, parse_qs
        
        # Parse URL components
        parsed_url = urlparse(str(request.url))
        
        # Get IP address (prefer X-Forwarded-For for proxy setups)
        x_forwarded = request.headers.get("X-Forwarded-For")
        client_ip = request.client.host if request.client else None
        
        # Handle body if needed
        body_digest = None
        body_content = None
        
        # Create headers dict (exclude sensitive headers)
        headers_dict = dict(request.headers)
        sensitive_headers = {'authorization', 'cookie', 'x-api-key', 'x-auth-token'}
        filtered_headers = {
            k: v for k, v in headers_dict.items() 
            if k.lower() not in sensitive_headers
        }
        
        entry = cls(
            timestamp=datetime.utcnow(),
            ip=client_ip,
            x_forwarded_for=x_forwarded,
            user_agent=request.headers.get("User-Agent"),
            method=request.method,
            url=str(request.url),
            path=parsed_url.path,
            query=parsed_url.query,
            headers=json.dumps(filtered_headers),
            body_digest=body_digest,
            body_content=body_content,
            referer=request.headers.get("Referer"),
            accept_language=request.headers.get("Accept-Language"),
            campaign=campaign,
            response_time_ms=response_time_ms
        )
        
        return entry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip': self.ip,
            'x_forwarded_for': self.x_forwarded_for,
            'user_agent': self.user_agent,
            'method': self.method,
            'url': self.url,
            'path': self.path,
            'query': self.query,
            'headers': json.loads(self.headers) if self.headers else {},
            'body_digest': self.body_digest,
            'referer': self.referer,
            'accept_language': self.accept_language,
            'campaign': self.campaign,
            'response_time_ms': self.response_time_ms,
            'has_body': bool(self.body_content)
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV-friendly dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else '',
            'ip': self.ip or '',
            'x_forwarded_for': self.x_forwarded_for or '',
            'user_agent': self.user_agent or '',
            'method': self.method or '',
            'url': self.url or '',
            'path': self.path or '',
            'query': self.query or '',
            'referer': self.referer or '',
            'accept_language': self.accept_language or '',
            'campaign': self.campaign or '',
            'response_time_ms': self.response_time_ms or '',
            'has_body': 'true' if self.body_content else 'false'
        }


class DatabaseManager:
    """Database management utilities."""
    
    def __init__(self, database_url: str = "sqlite:///logs.db"):
        self.database_url = database_url
        self.engine: Engine = create_engine(
            database_url, 
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def ensure_campaign_exists(self, campaign_name: str, description: Optional[str] = None) -> None:
        """Ensure campaign exists in database."""
        session = self.get_session()
        try:
            existing = session.query(Campaign).filter(Campaign.name == campaign_name).first()
            if not existing:
                campaign = Campaign(
                    name=campaign_name,
                    description=description or f"Auto-created campaign: {campaign_name}"
                )
                session.add(campaign)
                session.commit()
        finally:
            session.close()
    
    def get_campaigns(self, active_only: bool = True) -> List[Campaign]:
        """Get all campaigns."""
        session = self.get_session()
        try:
            query = session.query(Campaign)
            if active_only:
                query = query.filter(Campaign.is_active == True)
            return query.order_by(desc(Campaign.created_at)).all()
        finally:
            session.close()
    
    def get_campaign_stats(self, campaign_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for campaigns."""
        session = self.get_session()
        try:
            # Base query
            query = session.query(LogEntry)
            if campaign_name:
                query = query.filter(LogEntry.campaign == campaign_name)
            
            # Basic stats
            total_requests = query.count()
            
            # Method breakdown
            methods = session.query(
                LogEntry.method, 
                func.count(LogEntry.id)
            ).group_by(LogEntry.method)
            
            if campaign_name:
                methods = methods.filter(LogEntry.campaign == campaign_name)
            
            method_stats = {method: count for method, count in methods.all()}
            
            # Top user agents
            user_agents = session.query(
                LogEntry.user_agent,
                func.count(LogEntry.id)
            ).group_by(LogEntry.user_agent).order_by(
                desc(func.count(LogEntry.id))
            ).limit(10)
            
            if campaign_name:
                user_agents = user_agents.filter(LogEntry.campaign == campaign_name)
            
            ua_stats = {ua or 'Unknown': count for ua, count in user_agents.all()}
            
            # Time-based stats (last 24 hours)
            from datetime import timedelta
            last_24h = datetime.utcnow() - timedelta(hours=24)
            recent_query = query.filter(LogEntry.timestamp >= last_24h)
            recent_requests = recent_query.count()
            
            return {
                'total_requests': total_requests,
                'recent_requests': recent_requests,
                'methods': method_stats,
                'top_user_agents': ua_stats,
                'campaign': campaign_name
            }
        finally:
            session.close()
    
    def search_logs(
        self,
        campaign: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_filter: Optional[str] = None,
        ua_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
        path_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_desc: bool = True
    ) -> List[LogEntry]:
        """Search logs with filters."""
        session = self.get_session()
        try:
            query = session.query(LogEntry)
            
            # Apply filters
            if campaign:
                query = query.filter(LogEntry.campaign == campaign)
            
            if start_time:
                query = query.filter(LogEntry.timestamp >= start_time)
            
            if end_time:
                query = query.filter(LogEntry.timestamp <= end_time)
            
            if ip_filter:
                query = query.filter(
                    (LogEntry.ip.like(f"%{ip_filter}%")) |
                    (LogEntry.x_forwarded_for.like(f"%{ip_filter}%"))
                )
            
            if ua_filter:
                query = query.filter(LogEntry.user_agent.like(f"%{ua_filter}%"))
            
            if method_filter:
                query = query.filter(LogEntry.method == method_filter)
            
            if path_filter:
                query = query.filter(LogEntry.path.like(f"%{path_filter}%"))
            
            # Apply sorting
            if sort_desc:
                query = query.order_by(desc(LogEntry.timestamp))
            else:
                query = query.order_by(asc(LogEntry.timestamp))
            
            # Apply pagination
            return query.offset(offset).limit(limit).all()
        finally:
            session.close()
    
    def count_logs(
        self,
        campaign: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_filter: Optional[str] = None,
        ua_filter: Optional[str] = None,
        method_filter: Optional[str] = None,
        path_filter: Optional[str] = None
    ) -> int:
        """Count logs matching filters."""
        session = self.get_session()
        try:
            query = session.query(LogEntry)
            
            # Apply same filters as search_logs
            if campaign:
                query = query.filter(LogEntry.campaign == campaign)
            
            if start_time:
                query = query.filter(LogEntry.timestamp >= start_time)
            
            if end_time:
                query = query.filter(LogEntry.timestamp <= end_time)
            
            if ip_filter:
                query = query.filter(
                    (LogEntry.ip.like(f"%{ip_filter}%")) |
                    (LogEntry.x_forwarded_for.like(f"%{ip_filter}%"))
                )
            
            if ua_filter:
                query = query.filter(LogEntry.user_agent.like(f"%{ua_filter}%"))
            
            if method_filter:
                query = query.filter(LogEntry.method == method_filter)
            
            if path_filter:
                query = query.filter(LogEntry.path.like(f"%{path_filter}%"))
            
            return query.count()
        finally:
            session.close()