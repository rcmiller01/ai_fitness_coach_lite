"""
Monitoring API Integration for AI Fitness Coach

FastAPI routes for:
- Performance metrics and monitoring
- System health checks
- Error tracking and alerts
- Real-time monitoring dashboards
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
from datetime import datetime
import time

# Import monitoring system
from .performance_monitor import PerformanceMonitor, AlertLevel, create_performance_monitor

# Prometheus metrics endpoint
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Pydantic models
class ErrorReportRequest(BaseModel):
    """Error report request"""
    error_type: str
    error_message: str
    context: Optional[Dict[str, Any]] = None

class AlertResolutionRequest(BaseModel):
    """Alert resolution request"""
    alert_id: str
    resolution_notes: Optional[str] = None

# Global performance monitor
performance_monitor: Optional[PerformanceMonitor] = None

# API Router
router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])
health_router = APIRouter(prefix="/api/health", tags=["Health Checks"])

async def get_performance_monitor() -> PerformanceMonitor:
    """Dependency to get performance monitor"""
    global performance_monitor
    if performance_monitor is None:
        # In real implementation, pass db_manager and analytics_collector
        performance_monitor = create_performance_monitor()
        
        # Add default health checks
        await _setup_default_health_checks(performance_monitor)
    
    return performance_monitor

async def _setup_default_health_checks(monitor: PerformanceMonitor):
    """Setup default health checks"""
    from .performance_monitor import database_health_check, storage_health_check, payment_health_check
    
    await monitor.add_health_check("database", database_health_check)
    await monitor.add_health_check("storage", storage_health_check)
    await monitor.add_health_check("payments", payment_health_check)

# Middleware for request tracking
class MonitoringMiddleware:
    """Middleware to track request performance"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Create a custom send function to capture response
            response_status = None
            
            async def custom_send(message):
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = message["status"]
                await send(message)
            
            # Process request
            await self.app(scope, receive, custom_send)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            try:
                monitor = await get_performance_monitor()
                method = scope.get("method", "UNKNOWN")
                path = scope.get("path", "unknown")
                
                await monitor.track_request(method, path, duration, response_status or 500)
            except Exception as e:
                logging.error(f"Request tracking failed: {e}")
        else:
            await self.app(scope, receive, send)

# Performance metrics endpoints
@router.get("/metrics/system")
async def get_system_metrics(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get current system performance metrics"""
    try:
        metrics = await monitor.get_system_metrics()
        
        return {
            "system_metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"System metrics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/performance")
async def get_performance_metrics(
    hours: int = 24,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get performance summary"""
    try:
        summary = await monitor.get_performance_summary(hours)
        
        return {
            "performance_summary": summary,
            "query_hours": hours,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Performance metrics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/api")
async def get_api_metrics(
    endpoint: Optional[str] = None,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get API performance metrics"""
    try:
        # Get API metrics from monitor
        api_metrics = monitor.api_metrics
        
        if endpoint:
            # Filter by specific endpoint
            filtered_metrics = {k: v for k, v in api_metrics.items() if endpoint in k}
        else:
            filtered_metrics = dict(api_metrics)
        
        # Calculate statistics
        stats = {}
        for endpoint_key, requests in filtered_metrics.items():
            if requests:
                durations = [req["duration"] for req in requests]
                status_codes = [req["status_code"] for req in requests]
                
                stats[endpoint_key] = {
                    "total_requests": len(requests),
                    "average_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "success_rate": len([s for s in status_codes if 200 <= s < 300]) / len(status_codes) * 100,
                    "recent_requests": requests[-10:]  # Last 10 requests
                }
        
        return {
            "api_metrics": stats,
            "endpoint_filter": endpoint,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"API metrics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error tracking endpoints
@router.post("/errors/report")
async def report_error(
    error_request: ErrorReportRequest,
    request: Request,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Report an error occurrence"""
    try:
        # Get user context from request
        user_id = request.headers.get("X-User-ID")
        
        # Add request context
        context = error_request.context or {}
        context.update({
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": request.client.host if request.client else "",
            "endpoint": str(request.url)
        })
        
        error_id = await monitor.track_error(
            error_type=error_request.error_type,
            error_message=error_request.error_message,
            user_id=user_id,
            context=context
        )
        
        return {
            "success": True,
            "error_id": error_id,
            "message": "Error reported successfully"
        }
        
    except Exception as e:
        logging.error(f"Error reporting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors")
async def get_errors(
    error_type: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get error events"""
    try:
        # Filter errors
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        errors = []
        for error in monitor.error_events.values():
            error_time = datetime.fromisoformat(error.timestamp).timestamp()
            
            if error_time >= cutoff_time:
                if error_type is None or error.error_type == error_type:
                    errors.append({
                        "error_id": error.error_id,
                        "error_type": error.error_type,
                        "error_message": error.error_message,
                        "timestamp": error.timestamp,
                        "user_id": error.user_id,
                        "resolved": error.resolved
                    })
        
        # Sort by timestamp (most recent first) and limit
        errors.sort(key=lambda x: x["timestamp"], reverse=True)
        errors = errors[:limit]
        
        return {
            "errors": errors,
            "total_errors": len(errors),
            "error_type_filter": error_type,
            "period_hours": hours,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Get errors failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Alerts endpoints
@router.get("/alerts")
async def get_alerts(
    level: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get system alerts"""
    try:
        # Convert level string to enum
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")
        
        alerts = await monitor.get_alerts(resolved=resolved, level=alert_level)
        
        # Limit results
        alerts = alerts[:limit]
        
        # Convert to response format
        alert_list = []
        for alert in alerts:
            alert_list.append({
                "alert_id": alert.alert_id,
                "alert_level": alert.alert_level.value,
                "title": alert.title,
                "description": alert.description,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at,
                "metadata": alert.metadata
            })
        
        return {
            "alerts": alert_list,
            "total_alerts": len(alert_list),
            "filters": {
                "level": level,
                "resolved": resolved
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/resolve")
async def resolve_alert(
    resolution_request: AlertResolutionRequest,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Resolve a system alert"""
    try:
        success = await monitor.resolve_alert(resolution_request.alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "success": True,
            "alert_id": resolution_request.alert_id,
            "resolution_notes": resolution_request.resolution_notes,
            "resolved_at": datetime.now().isoformat(),
            "message": "Alert resolved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Alert resolution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoints
@health_router.get("/")
async def overall_health_check(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Overall system health check"""
    try:
        health_results = {}
        overall_healthy = True
        
        # Run all health checks
        for service_name in monitor.health_checks:
            result = await monitor.run_health_check(service_name)
            
            health_results[service_name] = {
                "status": result.status,
                "response_time": result.response_time,
                "details": result.details
            }
            
            if result.status != "healthy":
                overall_healthy = False
        
        # Get system metrics
        system_metrics = await monitor.get_system_metrics()
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "services": health_results,
            "system_metrics": {
                "cpu_usage": system_metrics.get("cpu_usage"),
                "memory_usage": system_metrics.get("memory_usage"),
                "disk_usage": system_metrics.get("disk_usage")
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Overall health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@health_router.get("/{service_name}")
async def service_health_check(
    service_name: str,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Health check for specific service"""
    try:
        result = await monitor.run_health_check(service_name)
        
        return {
            "service_name": service_name,
            "status": result.status,
            "response_time": result.response_time,
            "details": result.details,
            "timestamp": result.timestamp
        }
        
    except Exception as e:
        logging.error(f"Service health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Prometheus metrics endpoint
@router.get("/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Prometheus metrics endpoint"""
    try:
        if not PROMETHEUS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Prometheus metrics not available")
        
        # Generate metrics from the registry
        metrics_data = generate_latest(monitor.registry)
        
        return PlainTextResponse(
            content=metrics_data.decode('utf-8'),
            media_type=CONTENT_TYPE_LATEST
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Prometheus metrics generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard endpoints
@router.get("/dashboard/realtime")
async def realtime_monitoring_dashboard(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Real-time monitoring dashboard data"""
    try:
        # Get system metrics
        system_metrics = await monitor.get_system_metrics()
        
        # Get recent performance data
        performance_summary = await monitor.get_performance_summary(1)  # Last hour
        
        # Get active alerts
        active_alerts = await monitor.get_alerts(resolved=False)
        
        # Get recent errors
        recent_errors = list(monitor.error_events.values())[-10:]  # Last 10 errors
        
        return {
            "system_metrics": system_metrics,
            "performance_summary": performance_summary,
            "active_alerts": len(active_alerts),
            "critical_alerts": len([a for a in active_alerts if a.alert_level == AlertLevel.CRITICAL]),
            "recent_errors": len(recent_errors),
            "request_throughput": len(monitor.request_times),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Realtime dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/trends")
async def monitoring_trends_dashboard(
    hours: int = 24,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Monitoring trends dashboard"""
    try:
        # Get performance trends
        performance_data = await monitor.get_performance_summary(hours)
        
        # Calculate hourly metrics (mock data for demo)
        hourly_metrics = []
        for i in range(hours):
            hour_start = datetime.now().timestamp() - (i * 3600)
            hourly_metrics.append({
                "hour": datetime.fromtimestamp(hour_start).isoformat(),
                "requests": 150 - (i * 2),  # Mock decreasing trend
                "avg_response_time": 0.2 + (i * 0.01),  # Mock increasing trend
                "error_rate": 1.0 + (i * 0.1),  # Mock trend
                "cpu_usage": 45.0 + (i % 10),  # Mock variation
                "memory_usage": 60.0 + (i % 15)  # Mock variation
            })
        
        return {
            "period_hours": hours,
            "hourly_metrics": hourly_metrics,
            "performance_summary": performance_data,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Trends dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Administrative endpoints
@router.post("/admin/clear-metrics")
async def clear_metrics(
    confirm: bool = False,
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Clear metrics buffer (admin only)"""
    try:
        if not confirm:
            raise HTTPException(status_code=400, detail="Must confirm metrics clearing")
        
        metrics_count = len(monitor.metrics_buffer)
        monitor.metrics_buffer.clear()
        
        return {
            "success": True,
            "metrics_cleared": metrics_count,
            "message": "Metrics buffer cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Clear metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/stats")
async def get_monitoring_stats(
    monitor: PerformanceMonitor = Depends(get_performance_monitor)
):
    """Get monitoring system statistics"""
    try:
        return {
            "metrics_buffer_size": len(monitor.metrics_buffer),
            "error_events_count": len(monitor.error_events),
            "alerts_count": len(monitor.alerts),
            "health_checks_count": len(monitor.health_checks),
            "active_alerts": len([a for a in monitor.alerts.values() if not a.resolved]),
            "monitoring_interval": monitor.monitoring_interval,
            "alert_thresholds": monitor.alert_thresholds,
            "system_status": "operational"
        }
        
    except Exception as e:
        logging.error(f"Monitoring stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include routers in main app
def include_monitoring_routes(app):
    """Include monitoring routes in FastAPI app"""
    app.include_router(router)
    app.include_router(health_router)
    
    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware)