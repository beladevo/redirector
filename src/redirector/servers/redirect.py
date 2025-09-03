"""Redirect server implementation."""
import time
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
    
    @app.middleware("http")
    async def log_and_redirect(request: Request, call_next: Any) -> RedirectResponse:
        """Log request and redirect to target URL."""
        start_time = time.time()
        
        try:
            # Create log entry
            log_entry = LogEntry.from_request(
                request=request,
                campaign=config.campaign,
                store_body=config.store_body
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            log_entry.response_time_ms = response_time_ms
            
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