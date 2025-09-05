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
    
    # Tunnel tracking
    via_tunnel = Column(Boolean, default=False, index=True)
    
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
        response_time_ms: Optional[int] = None,
        via_tunnel: bool = False
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
            response_time_ms=response_time_ms,
            via_tunnel=via_tunnel
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
            'has_body': bool(self.body_content),
            'via_tunnel': self.via_tunnel
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
            'has_body': 'true' if self.body_content else 'false',
            'via_tunnel': 'true' if self.via_tunnel else 'false'
        }


class ServerStatus(Base):
    """Server status model for tracking active redirect servers."""
    __tablename__ = "server_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String(255), unique=True, nullable=False, index=True)
    campaign = Column(String(255), nullable=False, index=True)
    redirect_url = Column(Text, nullable=False)
    redirect_port = Column(Integer, nullable=False)
    dashboard_port = Column(Integer, nullable=True)
    host = Column(String(255), nullable=False)
    pid = Column(Integer, nullable=True)
    
    # Status tracking
    status = Column(String(50), default='active', nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_request_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_requests = Column(Integer, default=0, nullable=False)
    requests_per_minute = Column(Integer, default=0, nullable=False)
    avg_response_time = Column(Integer, default=0, nullable=False)
    
    # Tunnel information
    tunnel_enabled = Column(Boolean, default=False, nullable=False)
    tunnel_url = Column(Text, nullable=True)
    
    # Additional metadata
    version = Column(String(50), nullable=True)
    python_version = Column(String(50), nullable=True)
    platform = Column(String(100), nullable=True)
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_server_campaign_status', 'campaign', 'status'),
        Index('idx_server_last_seen', 'last_seen'),
        Index('idx_server_started_at', 'started_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        uptime_seconds = (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0
        last_seen_seconds = (datetime.utcnow() - self.last_seen).total_seconds() if self.last_seen else 0
        
        return {
            'id': self.id,
            'server_id': self.server_id,
            'campaign': self.campaign,
            'redirect_url': self.redirect_url,
            'redirect_port': self.redirect_port,
            'dashboard_port': self.dashboard_port,
            'host': self.host,
            'pid': self.pid,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_request_at': self.last_request_at.isoformat() if self.last_request_at else None,
            'uptime_seconds': int(uptime_seconds),
            'uptime_formatted': self._format_uptime(uptime_seconds),
            'last_seen_seconds': int(last_seen_seconds),
            'is_active': self.status == 'active' and last_seen_seconds < 120,  # Active if seen in last 2 minutes
            'total_requests': self.total_requests,
            'requests_per_minute': self.requests_per_minute,
            'avg_response_time': self.avg_response_time,
            'tunnel_enabled': self.tunnel_enabled,
            'tunnel_url': self.tunnel_url,
            'version': self.version,
            'python_version': self.python_version,
            'platform': self.platform
        }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            minutes = int(uptime_seconds / 60)
            seconds = int(uptime_seconds % 60)
            return f"{minutes}m {seconds}s"
        elif uptime_seconds < 86400:
            hours = int(uptime_seconds / 3600)
            minutes = int((uptime_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(uptime_seconds / 86400)
            hours = int((uptime_seconds % 86400) / 3600)
            return f"{days}d {hours}h"


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
        # Run migrations for existing databases
        self._run_migrations()
    
    def _run_migrations(self) -> None:
        """Run database migrations for schema updates."""
        session = self.get_session()
        try:
            # Check if via_tunnel column exists, add it if it doesn't
            from sqlalchemy import inspect, text
            
            inspector = inspect(self.engine)
            columns = [col['name'] for col in inspector.get_columns('logs')]
            
            if 'via_tunnel' not in columns:
                print("Adding via_tunnel column to logs table...")
                session.execute(text("ALTER TABLE logs ADD COLUMN via_tunnel BOOLEAN DEFAULT FALSE"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_via_tunnel ON logs (via_tunnel)"))
                session.commit()
                print("Migration completed: via_tunnel column added")
            
            # Check if server_status table exists, create if it doesn't
            tables = inspector.get_table_names()
            if 'server_status' not in tables:
                print("Creating server_status table...")
                ServerStatus.__table__.create(self.engine, checkfirst=True)
                print("Migration completed: server_status table created")
                
        except Exception as e:
            print(f"Migration warning: {e}")
            session.rollback()
        finally:
            session.close()
    
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
            ).group_by(LogEntry.user_agent)
            
            if campaign_name:
                user_agents = user_agents.filter(LogEntry.campaign == campaign_name)
            
            user_agents = user_agents.order_by(
                desc(func.count(LogEntry.id))
            ).limit(10)
            
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
    
    def get_campaign_cards(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get campaign cards with metadata for dashboard."""
        session = self.get_session()
        try:
            # Get campaigns with request counts and latest activity
            campaign_cards = []
            
            campaigns = session.query(Campaign).filter(
                Campaign.is_active == True
            ).order_by(desc(Campaign.updated_at)).offset(offset).limit(limit).all()
            
            for campaign in campaigns:
                # Get request count for this campaign
                request_count = session.query(LogEntry).filter(
                    LogEntry.campaign == campaign.name
                ).count()
                
                # Get latest request timestamp
                latest_request = session.query(LogEntry).filter(
                    LogEntry.campaign == campaign.name
                ).order_by(desc(LogEntry.timestamp)).first()
                
                # Get tunnel usage stats
                tunnel_requests = session.query(LogEntry).filter(
                    LogEntry.campaign == campaign.name,
                    LogEntry.via_tunnel == True
                ).count()
                
                # Get top methods for this campaign
                top_methods = session.query(
                    LogEntry.method,
                    func.count(LogEntry.id)
                ).filter(
                    LogEntry.campaign == campaign.name
                ).group_by(LogEntry.method).order_by(
                    desc(func.count(LogEntry.id))
                ).limit(3).all()
                
                # Get recent activity (last 24 hours)
                from datetime import timedelta
                last_24h = datetime.utcnow() - timedelta(hours=24)
                recent_count = session.query(LogEntry).filter(
                    LogEntry.campaign == campaign.name,
                    LogEntry.timestamp >= last_24h
                ).count()
                
                campaign_card = {
                    'id': campaign.id,
                    'name': campaign.name,
                    'description': campaign.description,
                    'created_at': campaign.created_at.isoformat(),
                    'updated_at': campaign.updated_at.isoformat(),
                    'is_active': campaign.is_active,
                    'request_count': request_count,
                    'recent_count': recent_count,
                    'tunnel_requests': tunnel_requests,
                    'tunnel_percentage': round((tunnel_requests / request_count * 100) if request_count > 0 else 0, 1),
                    'latest_request': latest_request.timestamp.isoformat() if latest_request else None,
                    'top_methods': [{'method': method, 'count': count} for method, count in top_methods]
                }
                
                campaign_cards.append(campaign_card)
            
            return campaign_cards
            
        finally:
            session.close()
    
    def get_campaign_cards_count(self) -> int:
        """Get total count of active campaigns for pagination."""
        session = self.get_session()
        try:
            return session.query(Campaign).filter(Campaign.is_active == True).count()
        finally:
            session.close()
    
    # ==================== SERVER STATUS MANAGEMENT ====================
    
    def register_server(
        self,
        server_id: str,
        campaign: str,
        redirect_url: str,
        redirect_port: int,
        dashboard_port: Optional[int] = None,
        host: str = 'localhost',
        pid: Optional[int] = None,
        tunnel_enabled: bool = False,
        tunnel_url: Optional[str] = None,
        version: Optional[str] = None
    ) -> None:
        """Register or update a server in the status table."""
        print(f"[DEBUG] Registering server: {server_id}, campaign: {campaign}, host: {host}:{redirect_port}")
        session = self.get_session()
        try:
            # Check if server already exists
            existing_server = session.query(ServerStatus).filter(
                ServerStatus.server_id == server_id
            ).first()
            
            if existing_server:
                print(f"[DEBUG] Updating existing server: {server_id}")
                # Update existing server
                existing_server.campaign = campaign
                existing_server.redirect_url = redirect_url
                existing_server.redirect_port = redirect_port
                existing_server.dashboard_port = dashboard_port
                existing_server.host = host
                existing_server.pid = pid
                existing_server.status = 'active'
                existing_server.last_seen = datetime.utcnow()
                existing_server.tunnel_enabled = tunnel_enabled
                existing_server.tunnel_url = tunnel_url
                existing_server.version = version
            else:
                print(f"[DEBUG] Creating new server entry: {server_id}")
                # Create new server entry
                import platform
                import sys
                
                server = ServerStatus(
                    server_id=server_id,
                    campaign=campaign,
                    redirect_url=redirect_url,
                    redirect_port=redirect_port,
                    dashboard_port=dashboard_port,
                    host=host,
                    pid=pid,
                    status='active',
                    started_at=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    tunnel_enabled=tunnel_enabled,
                    tunnel_url=tunnel_url,
                    version=version,
                    python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    platform=platform.system()
                )
                session.add(server)
            
            session.commit()
            print(f"[DEBUG] Successfully registered/updated server: {server_id}")
            
            # Verify the server was saved
            try:
                saved_server = session.query(ServerStatus).filter(
                    ServerStatus.server_id == server_id
                ).first()
                if saved_server:
                    print(f"[DEBUG] Verification: Server {server_id} exists in database")
                else:
                    print(f"[ERROR] Verification failed: Server {server_id} NOT found in database after save")
            except Exception as verify_error:
                print(f"[ERROR] Verification check failed: {verify_error}")
                
        except Exception as e:
            print(f"[ERROR] Failed to register server {server_id}: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_server_heartbeat(
        self,
        server_id: str,
        total_requests: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        avg_response_time: Optional[int] = None,
        last_request_at: Optional[datetime] = None
    ) -> None:
        """Update server heartbeat and statistics."""
        session = self.get_session()
        try:
            server = session.query(ServerStatus).filter(
                ServerStatus.server_id == server_id
            ).first()
            
            if server:
                server.last_seen = datetime.utcnow()
                
                if total_requests is not None:
                    server.total_requests = total_requests
                if requests_per_minute is not None:
                    server.requests_per_minute = requests_per_minute
                if avg_response_time is not None:
                    server.avg_response_time = avg_response_time
                if last_request_at is not None:
                    server.last_request_at = last_request_at
                
                session.commit()
        finally:
            session.close()
    
    def mark_server_inactive(self, server_id: str) -> None:
        """Mark a server as inactive."""
        session = self.get_session()
        try:
            server = session.query(ServerStatus).filter(
                ServerStatus.server_id == server_id
            ).first()
            
            if server:
                server.status = 'inactive'
                server.last_seen = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def get_active_servers(self, campaign: Optional[str] = None) -> List[ServerStatus]:
        """Get list of active servers."""
        session = self.get_session()
        try:
            from datetime import timedelta
            # Consider servers active if they've been seen in the last 2 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=2)
            
            query = session.query(ServerStatus).filter(
                ServerStatus.last_seen >= cutoff_time
            )
            
            if campaign:
                query = query.filter(ServerStatus.campaign == campaign)
            
            return query.order_by(desc(ServerStatus.started_at)).all()
        finally:
            session.close()
    
    def get_all_servers(self, include_inactive: bool = False) -> List[ServerStatus]:
        """Get all servers, optionally including inactive ones."""
        session = self.get_session()
        try:
            from datetime import timedelta
            query = session.query(ServerStatus)
            
            total_servers = query.count()
            print(f"[DEBUG] Total servers in database: {total_servers}")
            
            if not include_inactive:
                # Only show servers that have been seen in the last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                print(f"[DEBUG] Cutoff time for active servers: {cutoff_time}")
                query = query.filter(ServerStatus.last_seen >= cutoff_time)
                active_servers_count = query.count()
                print(f"[DEBUG] Servers active within 24h: {active_servers_count}")
            
            result = query.order_by(desc(ServerStatus.started_at)).all()
            print(f"[DEBUG] Returning {len(result)} servers from get_all_servers")
            return result
        finally:
            session.close()
    
    def cleanup_old_servers(self, max_age_hours: int = 168) -> int:
        """Clean up old server entries (default: 1 week)."""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            deleted_count = session.query(ServerStatus).filter(
                ServerStatus.last_seen < cutoff_time
            ).delete()
            
            session.commit()
            return deleted_count
        finally:
            session.close()
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get overall server statistics."""
        session = self.get_session()
        try:
            from datetime import timedelta
            # Active servers (seen in last 2 minutes)
            active_cutoff = datetime.utcnow() - timedelta(minutes=2)
            active_count = session.query(ServerStatus).filter(
                ServerStatus.last_seen >= active_cutoff
            ).count()
            
            # Recently active servers (seen in last hour)
            recent_cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_count = session.query(ServerStatus).filter(
                ServerStatus.last_seen >= recent_cutoff
            ).count()
            
            # Total requests across all servers
            total_requests = session.query(func.sum(ServerStatus.total_requests)).scalar() or 0
            
            # Average uptime of active servers
            active_servers = session.query(ServerStatus).filter(
                ServerStatus.last_seen >= active_cutoff
            ).all()
            
            avg_uptime = 0
            if active_servers:
                total_uptime = sum(
                    (datetime.utcnow() - server.started_at).total_seconds()
                    for server in active_servers if server.started_at
                )
                avg_uptime = total_uptime / len(active_servers)
            
            return {
                'active_servers': active_count,
                'recent_servers': recent_count,
                'total_requests_all_servers': total_requests,
                'average_uptime_seconds': int(avg_uptime),
                'average_uptime_formatted': self._format_uptime(avg_uptime) if avg_uptime > 0 else '0s'
            }
        finally:
            session.close()
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            minutes = int(uptime_seconds / 60)
            seconds = int(uptime_seconds % 60)
            return f"{minutes}m {seconds}s"
        elif uptime_seconds < 86400:
            hours = int(uptime_seconds / 3600)
            minutes = int((uptime_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(uptime_seconds / 86400)
            hours = int((uptime_seconds % 86400) / 3600)
            return f"{days}d {hours}h"