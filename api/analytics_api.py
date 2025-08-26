"""
Analytics API Integration for AI Fitness Coach

FastAPI routes for:
- Event tracking
- Real-time analytics dashboards
- User engagement metrics
- Plugin performance analytics
- Revenue and business metrics
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta

# Import analytics system
from .analytics import AnalyticsCollector, EventType, create_analytics_collector

# Pydantic models
class EventTrackingRequest(BaseModel):
    """Event tracking request"""
    event_type: str
    properties: Dict[str, Any] = {}
    device_info: Optional[Dict[str, Any]] = None

class SessionStartRequest(BaseModel):
    """Session start request"""
    device_info: Optional[Dict[str, Any]] = None

class WorkoutTrackingRequest(BaseModel):
    """Workout tracking request"""
    workout_type: str
    duration: int
    exercises_count: int
    total_volume: Optional[float] = None
    calories_burned: Optional[int] = None
    difficulty_rating: Optional[int] = None

class PluginUsageRequest(BaseModel):
    """Plugin usage tracking request"""
    plugin_id: str
    action: str
    duration: int = 0
    properties: Optional[Dict[str, Any]] = None

class ErrorTrackingRequest(BaseModel):
    """Error tracking request"""
    error_type: str
    error_message: str
    context: Optional[Dict[str, Any]] = None

class AnalyticsQuery(BaseModel):
    """Analytics query parameters"""
    days: int = 30
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

# Global analytics collector
analytics_collector: Optional[AnalyticsCollector] = None

# API Router
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

async def get_analytics_collector() -> AnalyticsCollector:
    """Dependency to get analytics collector"""
    global analytics_collector
    if analytics_collector is None:
        # In real implementation, pass db_manager and storage_manager
        analytics_collector = create_analytics_collector()
    return analytics_collector

# Event tracking endpoints
@router.post("/track/event/{user_id}")
async def track_event(
    user_id: str,
    event_request: EventTrackingRequest,
    request: Request,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Track a user event"""
    try:
        # Get session ID from headers or create one
        session_id = request.headers.get("X-Session-ID", "default_session")
        
        # Convert string event type to enum
        try:
            event_type = EventType(event_request.event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_request.event_type}")
        
        # Add request metadata
        device_info = event_request.device_info or {}
        device_info.update({
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": request.client.host if request.client else ""
        })
        
        # Track the event
        event_id = await collector.track_event(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            properties=event_request.properties,
            device_info=device_info
        )
        
        return {
            "success": True,
            "event_id": event_id,
            "message": "Event tracked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Event tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/start/{user_id}")
async def start_session(
    user_id: str,
    session_request: SessionStartRequest,
    request: Request,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Start a new user session"""
    try:
        device_info = session_request.device_info or {}
        device_info.update({
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": request.client.host if request.client else "",
            "referrer": request.headers.get("referer", "")
        })
        
        session_id = await collector.start_session(user_id, device_info)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session started successfully"
        }
        
    except Exception as e:
        logging.error(f"Session start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/end/{session_id}")
async def end_session(
    session_id: str,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """End a user session"""
    try:
        await collector.end_session(session_id)
        
        return {
            "success": True,
            "message": "Session ended successfully"
        }
        
    except Exception as e:
        logging.error(f"Session end failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/workout/{user_id}")
async def track_workout(
    user_id: str,
    workout_request: WorkoutTrackingRequest,
    request: Request,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Track workout completion"""
    try:
        session_id = request.headers.get("X-Session-ID", "default_session")
        
        workout_data = {
            "workout_type": workout_request.workout_type,
            "duration": workout_request.duration,
            "exercises": [{"count": workout_request.exercises_count}],  # Mock exercises
            "total_volume": workout_request.total_volume,
            "calories_burned": workout_request.calories_burned,
            "difficulty_rating": workout_request.difficulty_rating
        }
        
        await collector.track_workout(user_id, session_id, workout_data)
        
        return {
            "success": True,
            "message": "Workout tracked successfully"
        }
        
    except Exception as e:
        logging.error(f"Workout tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/plugin/{user_id}")
async def track_plugin_usage(
    user_id: str,
    plugin_request: PluginUsageRequest,
    request: Request,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Track plugin usage"""
    try:
        session_id = request.headers.get("X-Session-ID", "default_session")
        
        await collector.track_plugin_usage(
            user_id=user_id,
            session_id=session_id,
            plugin_id=plugin_request.plugin_id,
            action=plugin_request.action,
            duration=plugin_request.duration,
            properties=plugin_request.properties
        )
        
        return {
            "success": True,
            "message": "Plugin usage tracked successfully"
        }
        
    except Exception as e:
        logging.error(f"Plugin usage tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/error/{user_id}")
async def track_error(
    user_id: str,
    error_request: ErrorTrackingRequest,
    request: Request,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Track error occurrence"""
    try:
        session_id = request.headers.get("X-Session-ID", "default_session")
        
        await collector.track_error(
            user_id=user_id,
            session_id=session_id,
            error_type=error_request.error_type,
            error_message=error_request.error_message,
            context=error_request.context
        )
        
        return {
            "success": True,
            "message": "Error tracked successfully"
        }
        
    except Exception as e:
        logging.error(f"Error tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics query endpoints
@router.get("/user/{user_id}")
async def get_user_analytics(
    user_id: str,
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get analytics for a specific user"""
    try:
        analytics = await collector.get_user_analytics(user_id, days)
        
        return {
            "user_id": user_id,
            "analytics": analytics,
            "query_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"User analytics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plugin/{plugin_id}")
async def get_plugin_analytics(
    plugin_id: str,
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get analytics for a specific plugin"""
    try:
        analytics = await collector.get_plugin_analytics(plugin_id, days)
        
        return {
            "plugin_id": plugin_id,
            "analytics": analytics,
            "query_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Plugin analytics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/platform")
async def get_platform_analytics(
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get overall platform analytics"""
    try:
        analytics = await collector.get_platform_analytics(days)
        
        return {
            "platform_analytics": analytics,
            "query_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Platform analytics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard endpoints
@dashboard_router.get("/realtime")
async def get_realtime_dashboard(
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get real-time dashboard data"""
    try:
        realtime_metrics = collector.realtime_metrics
        
        return {
            "active_users": len(realtime_metrics["active_users"]),
            "active_sessions": len(realtime_metrics["active_sessions"]),
            "current_workouts": realtime_metrics["current_workouts"],
            "plugin_usage": dict(realtime_metrics["plugin_usage"]),
            "error_count": realtime_metrics["error_count"],
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Realtime dashboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/engagement")
async def get_engagement_dashboard(
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get user engagement dashboard"""
    try:
        platform_analytics = await collector.get_platform_analytics(days)
        engagement_report = await collector.generate_report("engagement", days)
        
        return {
            "engagement_metrics": engagement_report,
            "platform_summary": platform_analytics,
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Engagement dashboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/revenue")
async def get_revenue_dashboard(
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get revenue dashboard"""
    try:
        revenue_report = await collector.generate_report("revenue", days)
        
        return {
            "revenue_metrics": revenue_report,
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Revenue dashboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.get("/plugins")
async def get_plugins_dashboard(
    days: int = 30,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get plugins performance dashboard"""
    try:
        plugin_report = await collector.generate_report("plugin_performance", days)
        
        # Get individual plugin analytics
        plugin_analytics = {}
        popular_plugins = ["golf_pro", "tennis_pro", "basketball_skills"]
        
        for plugin_id in popular_plugins:
            plugin_analytics[plugin_id] = await collector.get_plugin_analytics(plugin_id, days)
        
        return {
            "plugin_performance": plugin_report,
            "individual_plugins": plugin_analytics,
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Plugins dashboard query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Reporting endpoints
@router.get("/reports/{report_type}")
async def generate_analytics_report(
    report_type: str,
    days: int = 30,
    format: str = "json",
    background_tasks: BackgroundTasks = None,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Generate analytics report"""
    try:
        valid_report_types = ["engagement", "revenue", "plugin_performance", "user_retention"]
        
        if report_type not in valid_report_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid report type. Valid types: {valid_report_types}"
            )
        
        report_data = await collector.generate_report(report_type, days)
        
        if format == "json":
            return {
                "report_type": report_type,
                "format": format,
                "period_days": days,
                "data": report_data,
                "generated_at": datetime.now().isoformat()
            }
        elif format == "csv":
            # For CSV format, return download URL (implementation would generate CSV)
            return {
                "report_type": report_type,
                "format": format,
                "download_url": f"/api/analytics/reports/{report_type}/download",
                "generated_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'")
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export endpoints
@router.get("/export/user/{user_id}")
async def export_user_analytics(
    user_id: str,
    days: int = 90,
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Export user analytics data"""
    try:
        user_analytics = await collector.get_user_analytics(user_id, days)
        
        export_data = {
            "export_type": "user_analytics",
            "user_id": user_id,
            "period_days": days,
            "analytics": user_analytics,
            "exported_at": datetime.now().isoformat(),
            "privacy_notice": "This data export contains personal usage analytics. Handle according to privacy policy."
        }
        
        return export_data
        
    except Exception as e:
        logging.error(f"User analytics export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin endpoints (require admin privileges)
@router.get("/admin/system-stats")
async def get_system_stats(
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Get system statistics (admin only)"""
    try:
        return {
            "events_buffer_size": len(collector.events_buffer),
            "active_sessions": len(collector.sessions),
            "plugin_metrics_count": len(collector.plugin_metrics),
            "user_metrics_count": len(collector.user_metrics),
            "buffer_flush_interval": collector.flush_interval,
            "retention_days": collector.retention_days,
            "system_status": "operational"
        }
        
    except Exception as e:
        logging.error(f"System stats query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/flush-events")
async def flush_events(
    collector: AnalyticsCollector = Depends(get_analytics_collector)
):
    """Manually flush events to storage (admin only)"""
    try:
        events_count = len(collector.events_buffer)
        await collector._flush_events()
        
        return {
            "success": True,
            "events_flushed": events_count,
            "message": "Events flushed to storage successfully"
        }
        
    except Exception as e:
        logging.error(f"Manual flush failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@router.get("/health")
async def analytics_health_check():
    """Analytics system health check"""
    try:
        collector = await get_analytics_collector()
        
        # Test basic functionality
        test_session_id = await collector.start_session("health_check_user", {
            "device_type": "test"
        })
        
        test_event_id = await collector.track_event(
            "health_check_user",
            test_session_id,
            EventType.PAGE_VIEW,
            {"page": "health_check"}
        )
        
        await collector.end_session(test_session_id)
        
        return {
            "status": "healthy",
            "events_buffer_size": len(collector.events_buffer),
            "active_sessions": len(collector.sessions),
            "test_event_id": test_event_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Analytics health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Include routers in main app
def include_analytics_routes(app):
    """Include analytics routes in FastAPI app"""
    app.include_router(router)
    app.include_router(dashboard_router)