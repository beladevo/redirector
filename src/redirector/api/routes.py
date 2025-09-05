"""API routes for the dashboard."""
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from ..core.config import RedirectorConfig
from ..core.models import DatabaseManager, Campaign, LogEntry, ServerStatus


# Pydantic models for API
class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    is_active: bool


class LogResponse(BaseModel):
    id: int
    timestamp: str
    ip: Optional[str]
    x_forwarded_for: Optional[str]
    user_agent: Optional[str]
    method: str
    url: str
    path: str
    query: Optional[str]
    headers: Dict[str, Any]
    referer: Optional[str]
    accept_language: Optional[str]
    campaign: str
    response_time_ms: Optional[int]
    has_body: bool
    via_tunnel: bool


class CampaignCardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    is_active: bool
    request_count: int
    recent_count: int
    tunnel_requests: int
    tunnel_percentage: float
    latest_request: Optional[str]
    top_methods: List[Dict[str, Any]]
    tunnel_url: Optional[str] = None


class CampaignCardsResponse(BaseModel):
    campaign_cards: List[CampaignCardResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LogsResponse(BaseModel):
    logs: List[LogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class StatsResponse(BaseModel):
    total_requests: int
    recent_requests: int
    methods: Dict[str, int]
    top_user_agents: Dict[str, int]
    campaign: Optional[str]


class ServerStatusResponse(BaseModel):
    id: int
    server_id: str
    campaign: str
    redirect_url: str
    redirect_port: int
    dashboard_port: Optional[int]
    host: str
    pid: Optional[int]
    status: str
    started_at: str
    last_seen: str
    last_request_at: Optional[str]
    uptime_seconds: int
    uptime_formatted: str
    last_seen_seconds: int
    is_active: bool
    total_requests: int
    requests_per_minute: int
    avg_response_time: int
    tunnel_enabled: bool
    tunnel_url: Optional[str]
    version: Optional[str]
    python_version: Optional[str]
    platform: Optional[str]


class ServerStatsResponse(BaseModel):
    active_servers: int
    recent_servers: int
    total_requests_all_servers: int
    average_uptime_seconds: int
    average_uptime_formatted: str


def create_api_router(config: RedirectorConfig, db_manager: DatabaseManager) -> APIRouter:
    """Create API router with all endpoints."""
    
    router = APIRouter(prefix="/api", tags=["api"])
    
    @router.get("/health")
    async def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "service": "dashboard"}
    
    @router.get("/campaign-cards", response_model=CampaignCardsResponse)
    async def get_campaign_cards(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Cards per page")
    ) -> CampaignCardsResponse:
        """Get campaign cards with metadata for dashboard."""
        offset = (page - 1) * per_page
        
        campaign_cards = db_manager.get_campaign_cards(limit=per_page, offset=offset)
        total = db_manager.get_campaign_cards_count()
        pages = (total + per_page - 1) // per_page
        
        # Add current tunnel URL to cards if available
        for card in campaign_cards:
            if card['name'] == config.campaign and config.tunnel_url:
                card['tunnel_url'] = config.tunnel_url
            else:
                card['tunnel_url'] = None
        
        # Convert to response models
        card_responses = []
        for card in campaign_cards:
            card_response = CampaignCardResponse(**card)
            card_responses.append(card_response)
        
        return CampaignCardsResponse(
            campaign_cards=card_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )

    @router.get("/campaigns", response_model=List[CampaignResponse])
    async def get_campaigns() -> List[CampaignResponse]:
        """Get all campaigns."""
        campaigns = db_manager.get_campaigns()
        return [
            CampaignResponse(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                created_at=campaign.created_at.isoformat(),
                updated_at=campaign.updated_at.isoformat(),
                is_active=campaign.is_active
            )
            for campaign in campaigns
        ]
    
    @router.post("/campaigns", response_model=CampaignResponse)
    async def create_campaign(campaign_data: CampaignCreate) -> CampaignResponse:
        """Create a new campaign."""
        session = db_manager.get_session()
        try:
            # Check if campaign already exists
            existing = session.query(Campaign).filter(Campaign.name == campaign_data.name).first()
            if existing:
                raise HTTPException(status_code=400, detail="Campaign already exists")
            
            # Create new campaign
            campaign = Campaign(
                name=campaign_data.name,
                description=campaign_data.description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
            
            return CampaignResponse(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                created_at=campaign.created_at.isoformat(),
                updated_at=campaign.updated_at.isoformat(),
                is_active=campaign.is_active
            )
        finally:
            session.close()
    
    @router.get("/logs", response_model=LogsResponse)
    async def get_logs(
        campaign: Optional[str] = Query(None, description="Filter by campaign"),
        start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
        end_time: Optional[str] = Query(None, description="End time (ISO format)"),
        ip_filter: Optional[str] = Query(None, description="Filter by IP address"),
        ua_filter: Optional[str] = Query(None, description="Filter by User Agent"),
        method_filter: Optional[str] = Query(None, description="Filter by HTTP method"),
        path_filter: Optional[str] = Query(None, description="Filter by path"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
        sort_desc: bool = Query(True, description="Sort by timestamp descending")
    ) -> LogsResponse:
        """Get logs with filtering and pagination."""
        
        # Parse datetime strings
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get logs and total count
        logs = db_manager.search_logs(
            campaign=campaign,
            start_time=start_dt,
            end_time=end_dt,
            ip_filter=ip_filter,
            ua_filter=ua_filter,
            method_filter=method_filter,
            path_filter=path_filter,
            limit=per_page,
            offset=offset,
            sort_desc=sort_desc
        )
        
        total = db_manager.count_logs(
            campaign=campaign,
            start_time=start_dt,
            end_time=end_dt,
            ip_filter=ip_filter,
            ua_filter=ua_filter,
            method_filter=method_filter,
            path_filter=path_filter
        )
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page
        
        # Convert to response models
        log_responses = []
        for log in logs:
            log_dict = log.to_dict()
            log_responses.append(LogResponse(**log_dict))
        
        return LogsResponse(
            logs=log_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    
    @router.get("/logs/export.csv")
    async def export_logs_csv(
        campaign: Optional[str] = Query(None),
        start_time: Optional[str] = Query(None),
        end_time: Optional[str] = Query(None),
        ip_filter: Optional[str] = Query(None),
        ua_filter: Optional[str] = Query(None),
        method_filter: Optional[str] = Query(None),
        path_filter: Optional[str] = Query(None)
    ) -> Response:
        """Export logs as CSV."""
        
        # Parse datetime strings (same as get_logs)
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")
        
        # Get all logs (no pagination for export)
        logs = db_manager.search_logs(
            campaign=campaign,
            start_time=start_dt,
            end_time=end_dt,
            ip_filter=ip_filter,
            ua_filter=ua_filter,
            method_filter=method_filter,
            path_filter=path_filter,
            limit=10000,  # Reasonable export limit
            offset=0,
            sort_desc=True
        )
        
        # Create CSV
        output = io.StringIO()
        if logs:
            # Use first log to get fieldnames
            fieldnames = logs[0].to_csv_row().keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs:
                writer.writerow(log.to_csv_row())
        
        csv_content = output.getvalue()
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"redirector_logs_{campaign or 'all'}_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    @router.get("/logs/export.jsonl")
    async def export_logs_jsonl(
        campaign: Optional[str] = Query(None),
        start_time: Optional[str] = Query(None),
        end_time: Optional[str] = Query(None),
        ip_filter: Optional[str] = Query(None),
        ua_filter: Optional[str] = Query(None),
        method_filter: Optional[str] = Query(None),
        path_filter: Optional[str] = Query(None)
    ) -> Response:
        """Export logs as JSONL."""
        
        # Parse datetime strings (same as get_logs)
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")
        
        # Get all logs (no pagination for export)
        logs = db_manager.search_logs(
            campaign=campaign,
            start_time=start_dt,
            end_time=end_dt,
            ip_filter=ip_filter,
            ua_filter=ua_filter,
            method_filter=method_filter,
            path_filter=path_filter,
            limit=10000,  # Reasonable export limit
            offset=0,
            sort_desc=True
        )
        
        # Create JSONL
        lines = []
        for log in logs:
            lines.append(json.dumps(log.to_dict()))
        
        jsonl_content = "\n".join(lines)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"redirector_logs_{campaign or 'all'}_{timestamp}.jsonl"
        
        return Response(
            content=jsonl_content,
            media_type="application/jsonl",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats(
        campaign: Optional[str] = Query(None, description="Get stats for specific campaign")
    ) -> StatsResponse:
        """Get campaign statistics."""
        stats = db_manager.get_campaign_stats(campaign)
        
        return StatsResponse(
            total_requests=stats['total_requests'],
            recent_requests=stats['recent_requests'],
            methods=stats['methods'],
            top_user_agents=stats['top_user_agents'],
            campaign=stats['campaign']
        )
    
    @router.delete("/logs")
    async def clear_logs(
        campaign: Optional[str] = Query(None, description="Campaign to clear logs for (if not provided, clears all)")
    ) -> Dict[str, Any]:
        """Clear logs from database."""
        session = db_manager.get_session()
        try:
            if campaign:
                # Clear logs for specific campaign
                deleted_count = session.query(LogEntry).filter(LogEntry.campaign == campaign).count()
                session.query(LogEntry).filter(LogEntry.campaign == campaign).delete()
                message = f"Cleared {deleted_count} logs for campaign '{campaign}'"
            else:
                # Clear all logs
                deleted_count = session.query(LogEntry).count()
                session.query(LogEntry).delete()
                message = f"Cleared all {deleted_count} logs from database"
            
            session.commit()
            
            return {
                "success": True,
                "message": message,
                "deleted_count": deleted_count
            }
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")
        finally:
            session.close()

    @router.delete("/campaigns/{campaign_id}")
    async def delete_campaign(campaign_id: int) -> Dict[str, Any]:
        """Delete a campaign and all its logs."""
        session = db_manager.get_session()
        try:
            # Get campaign
            campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            
            campaign_name = campaign.name
            
            # Delete logs for this campaign
            logs_deleted = session.query(LogEntry).filter(LogEntry.campaign == campaign_name).count()
            session.query(LogEntry).filter(LogEntry.campaign == campaign_name).delete()
            
            # Delete campaign
            session.delete(campaign)
            session.commit()
            
            return {
                "success": True,
                "message": f"Deleted campaign '{campaign_name}' and {logs_deleted} associated logs",
                "campaign_name": campaign_name,
                "logs_deleted": logs_deleted
            }
        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")
        finally:
            session.close()

    @router.delete("/campaigns")
    async def delete_all_campaigns() -> Dict[str, Any]:
        """Delete all campaigns and their associated logs."""
        session = db_manager.get_session()
        try:
            # Get count of campaigns to delete
            campaigns_count = session.query(Campaign).count()
            
            if campaigns_count == 0:
                return {
                    "success": True,
                    "message": "No campaigns to delete",
                    "campaigns_deleted": 0,
                    "logs_deleted": 0
                }
            
            # Get total logs count before deletion
            logs_count = session.query(LogEntry).count()
            
            # Delete all logs first (they reference campaigns)
            session.query(LogEntry).delete()
            
            # Delete all campaigns
            session.query(Campaign).delete()
            
            session.commit()
            
            return {
                "success": True,
                "message": f"Deleted {campaigns_count} campaigns and {logs_count} associated logs",
                "campaigns_deleted": campaigns_count,
                "logs_deleted": logs_count
            }
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete all campaigns: {str(e)}")
        finally:
            session.close()
    
    # ==================== SERVER STATUS ENDPOINTS ====================
    
    @router.get("/servers", response_model=List[ServerStatusResponse])
    async def get_servers(
        campaign: Optional[str] = Query(None, description="Filter by campaign"),
        include_inactive: bool = Query(False, description="Include inactive servers")
    ) -> List[ServerStatusResponse]:
        """Get list of servers."""
        if campaign:
            servers = db_manager.get_active_servers(campaign=campaign)
        else:
            servers = db_manager.get_all_servers(include_inactive=include_inactive)
        
        return [ServerStatusResponse(**server.to_dict()) for server in servers]
    
    @router.get("/servers/stats", response_model=ServerStatsResponse)
    async def get_server_stats() -> ServerStatsResponse:
        """Get overall server statistics."""
        stats = db_manager.get_server_stats()
        return ServerStatsResponse(**stats)
    
    @router.post("/servers/cleanup")
    async def cleanup_old_servers(
        max_age_hours: int = Query(168, ge=1, description="Maximum age in hours (default: 168 = 1 week)")
    ) -> Dict[str, Any]:
        """Clean up old server entries."""
        try:
            deleted_count = db_manager.cleanup_old_servers(max_age_hours=max_age_hours)
            return {
                "success": True,
                "message": f"Cleaned up {deleted_count} old server entries",
                "deleted_count": deleted_count,
                "max_age_hours": max_age_hours
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to cleanup servers: {str(e)}")
    
    return router