"""Redirect server implementation."""
import time
import os
import socket
import uuid
import atexit
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import RedirectorConfig
from ..core.models import DatabaseManager, LogEntry


def create_redirect_app(config: RedirectorConfig) -> FastAPI:
    """Create and configure the redirect FastAPI application."""
    
    app = FastAPI(
        title="Redirector - Redirect Server",
        description="Professional URL redirection with comprehensive logging",
        version="2.0.0",
        docs_url=None,  # Disable docs on redirect server
        redoc_url=None,
        openapi_url=None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize database manager
    db_manager = DatabaseManager(config.database_url)
    
    # Generate unique server ID
    server_id = f"redirect-{config.campaign}-{config.redirect_port}-{uuid.uuid4().hex[:8]}"
    
    # Get server information
    hostname = socket.gethostname()
    pid = os.getpid()
    
    # Server statistics tracking
    server_stats = {
        'total_requests': 0,
        'start_time': datetime.utcnow(),
        'response_times': []
    }
    
    # Register this server instance
    try:
        db_manager.register_server(
            server_id=server_id,
            campaign=config.campaign,
            redirect_url=config.redirect_url,
            redirect_port=config.redirect_port,
            dashboard_port=getattr(config, 'dashboard_port', None),
            host=hostname,
            pid=pid,
            tunnel_enabled=getattr(config, 'tunnel', False),
            tunnel_url=getattr(config, 'tunnel_url', None),
            version="2.0.0"
        )
        print(f"[INFO] Server registered with ID: {server_id}")
    except Exception as e:
        print(f"[WARN] Failed to register server: {e}")
    
    # Set up server cleanup on exit
    def cleanup_server():
        try:
            db_manager.mark_server_inactive(server_id)
            print(f"[INFO] Server {server_id} marked as inactive")
        except Exception as e:
            print(f"[WARN] Failed to mark server inactive: {e}")
    
    atexit.register(cleanup_server)
    
    # Background task to update server heartbeat
    import asyncio
    async def heartbeat_task():
        """Update server heartbeat every 30 seconds."""
        while True:
            try:
                await asyncio.sleep(30)
                
                # Calculate requests per minute
                current_time = datetime.utcnow()
                time_diff = (current_time - server_stats['start_time']).total_seconds() / 60
                rpm = int(server_stats['total_requests'] / time_diff) if time_diff > 0 else 0
                
                # Calculate average response time
                avg_response_time = 0
                if server_stats['response_times']:
                    avg_response_time = int(sum(server_stats['response_times']) / len(server_stats['response_times']))
                    # Keep only last 100 response times to prevent memory bloat
                    if len(server_stats['response_times']) > 100:
                        server_stats['response_times'] = server_stats['response_times'][-100:]
                
                # Update server status
                db_manager.update_server_heartbeat(
                    server_id=server_id,
                    total_requests=server_stats['total_requests'],
                    requests_per_minute=rpm,
                    avg_response_time=avg_response_time,
                    last_request_at=server_stats.get('last_request_time')
                )
                
            except Exception as e:
                print(f"[WARN] Heartbeat update failed: {e}")
    
    # Start heartbeat task
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(heartbeat_task())
    
    @app.middleware("http")
    async def log_and_redirect(request: Request, call_next: Any) -> RedirectResponse:
        """Log request and redirect to target URL."""
        start_time = time.time()
        
        try:
            # Determine if request came through tunnel
            # Check for cloudflare headers or if tunnel is enabled and tunnel_url exists
            via_tunnel = bool(
                config.tunnel and config.tunnel_url and (
                    request.headers.get("cf-ray") or  # Cloudflare Ray ID header
                    request.headers.get("cf-ipcountry") or  # Cloudflare IP country
                    request.headers.get("x-forwarded-for")  # Proxy header (common with tunnels)
                )
            )
            
            # Create log entry
            log_entry = LogEntry.from_request(
                request=request,
                campaign=config.campaign,
                store_body=config.store_body,
                via_tunnel=via_tunnel
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            log_entry.response_time_ms = response_time_ms
            
            # Update server statistics
            server_stats['total_requests'] += 1
            server_stats['response_times'].append(response_time_ms)
            server_stats['last_request_time'] = datetime.utcnow()
            
            # Store in database
            session = db_manager.get_session()
            try:
                session.add(log_entry)
                session.commit()
            finally:
                session.close()
            
            # Redirect to target URL
            return RedirectResponse(
                url=config.redirect_url,
                status_code=302,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
            
        except Exception as e:
            # Even if logging fails, still redirect
            print(f"Logging error: {e}")
            return RedirectResponse(
                url=config.redirect_url,
                status_code=302
            )
    
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "service": "redirect", "campaign": config.campaign}
    
    return app