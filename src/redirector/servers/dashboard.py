"""Dashboard server implementation."""
import secrets
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import RedirectorConfig
from ..core.models import DatabaseManager, LogEntry
from ..api.routes import create_api_router


def create_dashboard_app(config: RedirectorConfig) -> FastAPI:
    """Create and configure the dashboard FastAPI application."""
    
    app = FastAPI(
        title="Redirector - Dashboard",
        description="Professional URL redirection dashboard with analytics",
        version="2.0.0",
        docs_url="/docs" if not config.dashboard_auth else None,
        redoc_url="/redoc" if not config.dashboard_auth else None,
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
    
    # Mount static files
    import os
    from pathlib import Path
    
    # Try different possible static directory locations
    static_paths = [
        "static",
        Path(__file__).parent.parent.parent.parent / "static",
        Path.cwd() / "static"
    ]
    
    static_mounted = False
    for static_path in static_paths:
        if Path(static_path).exists():
            try:
                static_files = StaticFiles(directory=str(static_path))
                app.mount("/static", static_files, name="static")
                static_mounted = True
                print(f"[OK] Static files mounted from: {static_path}")
                break
            except Exception as e:
                print(f"[WARN] Failed to mount static from {static_path}: {e}")
                continue
    
    if not static_mounted:
        print("[ERROR] Warning: No static directory found. CSS and JS files will not be served.")
        # Create a basic static route fallback
        @app.get("/static/{file_path:path}")
        async def static_fallback(file_path: str):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Static file not found: {file_path}")
    
    # Templates
    template_paths = [
        "templates",
        Path(__file__).parent.parent.parent.parent / "templates",
        Path.cwd() / "templates"
    ]
    
    templates_dir = None
    for template_path in template_paths:
        if Path(template_path).exists():
            templates_dir = str(template_path)
            print(f"[OK] Templates found at: {template_path}")
            break
    
    if not templates_dir:
        templates_dir = "templates"  # fallback
        print(f"[WARN] No templates directory found, using fallback: {templates_dir}")
    
    templates = Jinja2Templates(directory=templates_dir)
    
    # Authentication setup
    security = HTTPBasic() if config.dashboard_auth else None
    
    def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
        """Verify authentication credentials."""
        if not config.dashboard_auth:
            return "anonymous"
        
        correct_username = secrets.compare_digest(credentials.username, config.auth_user or "")
        correct_password = secrets.compare_digest(credentials.password, config.auth_password or "")
        
        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home(
        request: Request,
        user: str = Depends(get_current_user) if config.dashboard_auth else None
    ) -> HTMLResponse:
        """Main dashboard page."""
        
        # Get recent logs for initial display
        recent_logs = db_manager.search_logs(limit=20)
        campaigns = db_manager.get_campaigns()
        stats = db_manager.get_campaign_stats()
        
        # Convert SQLAlchemy objects to dictionaries for JSON serialization
        logs_dict = [log.to_dict() for log in recent_logs]
        campaigns_dict = [campaign.to_dict() for campaign in campaigns]
        
        template_name = "dashboard_raw.html" if config.dashboard_raw else "dashboard.html"
        
        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "logs": logs_dict,
                "campaigns": campaigns_dict,
                "stats": stats,
                "config": config,
                "current_campaign": config.campaign,
            }
        )
    
    @app.get("/logs/{log_id}", response_class=HTMLResponse)
    async def log_detail(
        request: Request,
        log_id: int,
        user: str = Depends(get_current_user) if config.dashboard_auth else None
    ) -> HTMLResponse:
        """Detailed view of a specific log entry."""
        
        session = db_manager.get_session()
        try:
            log = session.query(LogEntry).filter(LogEntry.id == log_id).first()
            if not log:
                raise HTTPException(status_code=404, detail="Log entry not found")
            
            template_name = "log_detail_raw.html" if config.dashboard_raw else "log_detail.html"
            
            return templates.TemplateResponse(
                template_name,
                {
                    "request": request,
                    "log": log.to_dict(),
                    "config": config,
                }
            )
        finally:
            session.close()
    
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "service": "dashboard", "campaign": config.campaign}
    
    # Include API routes at the end
    app.include_router(create_api_router(config, db_manager))
    
    return app