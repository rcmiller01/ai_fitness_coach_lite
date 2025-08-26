"""
Performance Monitoring and Error Tracking System

Comprehensive monitoring system for AI Fitness Coach that tracks:
- Application performance metrics
- System resource usage
- Error tracking and alerting
- API response times
- Database performance
- Real-time health monitoring
"""

import os
import time
import asyncio
import logging
import traceback
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict
import threading
import json

# Monitoring dependencies
try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Using basic monitoring.")

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Performance metric types"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    DATABASE_CONNECTIONS = "database_connections"
    ACTIVE_USERS = "active_users"

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: str
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}

@dataclass
class ErrorEvent:
    """Error event data structure"""
    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    timestamp: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    context: Dict[str, Any] = None
    resolved: bool = False
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}

@dataclass
class HealthCheckResult:
    """Health check result"""
    service_name: str
    status: str  # healthy, unhealthy, degraded
    response_time: float
    timestamp: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class SystemAlert:
    """System alert"""
    alert_id: str
    alert_level: AlertLevel
    title: str
    description: str
    timestamp: str
    resolved: bool = False
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PerformanceMonitor:
    """Main performance monitoring system"""
    
    def __init__(self, db_manager=None, analytics_collector=None):
        self.db_manager = db_manager
        self.analytics_collector = analytics_collector
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.error_events = {}
        self.alerts = {}
        self.health_checks = {}
        
        # Performance tracking
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.api_metrics = defaultdict(list)
        
        # System monitoring
        self.system_metrics = {}
        self.last_system_check = 0
        
        # Configuration
        self.monitoring_interval = 30  # seconds
        self.alert_thresholds = {
            "response_time": 5.0,  # seconds
            "error_rate": 5.0,     # percentage
            "cpu_usage": 80.0,     # percentage
            "memory_usage": 85.0,  # percentage
            "disk_usage": 90.0     # percentage
        }
        
        # Prometheus metrics (if available)
        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()
            self._setup_prometheus_metrics()
        
        # Start background monitoring
        asyncio.create_task(self._background_monitoring())
        asyncio.create_task(self._periodic_health_checks())
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        try:
            self.prom_request_duration = Histogram(
                'http_request_duration_seconds',
                'HTTP request duration in seconds',
                ['method', 'endpoint', 'status_code'],
                registry=self.registry
            )
            
            self.prom_request_count = Counter(
                'http_requests_total',
                'Total HTTP requests',
                ['method', 'endpoint', 'status_code'],
                registry=self.registry
            )
            
            self.prom_error_count = Counter(
                'errors_total',
                'Total errors',
                ['error_type', 'service'],
                registry=self.registry
            )
            
            self.prom_active_users = Gauge(
                'active_users_current',
                'Current active users',
                registry=self.registry
            )
            
            self.prom_system_cpu = Gauge(
                'system_cpu_usage_percent',
                'System CPU usage percentage',
                registry=self.registry
            )
            
            self.prom_system_memory = Gauge(
                'system_memory_usage_percent',
                'System memory usage percentage',
                registry=self.registry
            )
            
            self.logger.info("✅ Prometheus metrics initialized")
            
        except Exception as e:
            self.logger.error(f"Prometheus metrics setup failed: {e}")
    
    async def track_request(self, method: str, endpoint: str, duration: float, status_code: int):
        """Track API request performance"""
        try:
            # Store request time
            self.request_times.append(duration)
            
            # Track in API metrics
            self.api_metrics[f"{method}:{endpoint}"].append({
                "duration": duration,
                "status_code": status_code,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)
                
                self.prom_request_count.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
            
            # Create performance metric
            metric = PerformanceMetric(
                metric_name="api_response_time",
                metric_type=MetricType.RESPONSE_TIME,
                value=duration,
                timestamp=datetime.now().isoformat(),
                labels={
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": str(status_code)
                }
            )
            
            await self._store_metric(metric)
            
            # Check for performance alerts
            if duration > self.alert_thresholds["response_time"]:
                await self._create_alert(
                    AlertLevel.WARNING,
                    "Slow API Response",
                    f"API {method} {endpoint} took {duration:.2f}s (threshold: {self.alert_thresholds['response_time']}s)",
                    {"method": method, "endpoint": endpoint, "duration": duration}
                )
            
        except Exception as e:
            self.logger.error(f"Request tracking failed: {e}")
    
    async def track_error(self, error_type: str, error_message: str, 
                         user_id: str = None, context: Dict[str, Any] = None) -> str:
        """Track error occurrence"""
        try:
            error_id = f"error_{int(time.time() * 1000)}"
            
            error_event = ErrorEvent(
                error_id=error_id,
                error_type=error_type,
                error_message=error_message,
                stack_trace=traceback.format_exc(),
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                context=context or {}
            )
            
            # Store error
            self.error_events[error_id] = error_event
            
            # Update error counts
            self.error_counts[error_type] += 1
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_error_count.labels(
                    error_type=error_type,
                    service="fitness_coach"
                ).inc()
            
            # Track in analytics if available
            if self.analytics_collector and user_id:
                await self.analytics_collector.track_error(
                    user_id, "system_session", error_type, error_message, context
                )
            
            # Check error rate
            await self._check_error_rate()
            
            # Create critical alert for certain error types
            critical_errors = ["database_error", "payment_error", "auth_error"]
            if error_type in critical_errors:
                await self._create_alert(
                    AlertLevel.CRITICAL,
                    f"Critical Error: {error_type}",
                    error_message,
                    {"error_id": error_id, "error_type": error_type}
                )
            
            self.logger.error(f"Error tracked: {error_type} - {error_message}")
            return error_id
            
        except Exception as e:
            self.logger.error(f"Error tracking failed: {e}")
            return ""
    
    async def add_health_check(self, service_name: str, check_function: Callable):
        """Add a health check for a service"""
        self.health_checks[service_name] = check_function
        self.logger.info(f"Health check added for service: {service_name}")
    
    async def run_health_check(self, service_name: str) -> HealthCheckResult:
        """Run health check for a specific service"""
        try:
            if service_name not in self.health_checks:
                return HealthCheckResult(
                    service_name=service_name,
                    status="unknown",
                    response_time=0.0,
                    timestamp=datetime.now().isoformat(),
                    details={"error": "Health check not found"}
                )
            
            start_time = time.time()
            check_function = self.health_checks[service_name]
            
            # Run health check
            result = await check_function() if asyncio.iscoroutinefunction(check_function) else check_function()
            
            response_time = time.time() - start_time
            
            status = "healthy" if result.get("healthy", False) else "unhealthy"
            
            health_result = HealthCheckResult(
                service_name=service_name,
                status=status,
                response_time=response_time,
                timestamp=datetime.now().isoformat(),
                details=result
            )
            
            # Create alert for unhealthy services
            if status == "unhealthy":
                await self._create_alert(
                    AlertLevel.ERROR,
                    f"Service Unhealthy: {service_name}",
                    f"Health check failed for {service_name}",
                    {"service": service_name, "details": result}
                )
            
            return health_result
            
        except Exception as e:
            self.logger.error(f"Health check failed for {service_name}: {e}")
            return HealthCheckResult(
                service_name=service_name,
                status="error",
                response_time=0.0,
                timestamp=datetime.now().isoformat(),
                details={"error": str(e)}
            )
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "memory_total": memory.total,
                "memory_used": memory.used,
                "disk_usage": disk_percent,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "process_memory_rss": process_memory.rss,
                "process_memory_vms": process_memory.vms,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_system_cpu.set(cpu_percent)
                self.prom_system_memory.set(memory_percent)
            
            # Store metrics
            for metric_name, value in [("cpu_usage", cpu_percent), ("memory_usage", memory_percent), ("disk_usage", disk_percent)]:
                metric = PerformanceMetric(
                    metric_name=metric_name,
                    metric_type=MetricType(metric_name),
                    value=value,
                    timestamp=datetime.now().isoformat()
                )
                await self._store_metric(metric)
            
            # Check for system alerts
            await self._check_system_alerts(metrics)
            
            self.system_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            return {}
    
    async def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter recent metrics
            recent_metrics = [
                metric for metric in self.metrics_buffer
                if datetime.fromisoformat(metric.timestamp) >= cutoff_time
            ]
            
            # Calculate averages
            response_times = [m.value for m in recent_metrics if m.metric_type == MetricType.RESPONSE_TIME]
            cpu_usage = [m.value for m in recent_metrics if m.metric_type == MetricType.CPU_USAGE]
            memory_usage = [m.value for m in recent_metrics if m.metric_type == MetricType.MEMORY_USAGE]
            
            # Error statistics
            recent_errors = [
                error for error in self.error_events.values()
                if datetime.fromisoformat(error.timestamp) >= cutoff_time
            ]
            
            summary = {
                "period_hours": hours,
                "total_requests": len(response_times),
                "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "average_cpu_usage": sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                "average_memory_usage": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "total_errors": len(recent_errors),
                "error_types": dict(Counter(error.error_type for error in recent_errors)),
                "current_system_metrics": self.system_metrics,
                "generated_at": datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Performance summary generation failed: {e}")
            return {}
    
    async def get_alerts(self, resolved: bool = None, level: AlertLevel = None) -> List[SystemAlert]:
        """Get system alerts with optional filtering"""
        try:
            alerts = list(self.alerts.values())
            
            # Filter by resolved status
            if resolved is not None:
                alerts = [alert for alert in alerts if alert.resolved == resolved]
            
            # Filter by alert level
            if level is not None:
                alerts = [alert for alert in alerts if alert.alert_level == level]
            
            # Sort by timestamp (most recent first)
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Get alerts failed: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a system alert"""
        try:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.now().isoformat()
                
                self.logger.info(f"Alert resolved: {alert_id}")
                return True
            else:
                self.logger.warning(f"Alert not found: {alert_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Alert resolution failed: {e}")
            return False
    
    # Private helper methods
    async def _store_metric(self, metric: PerformanceMetric):
        """Store performance metric"""
        self.metrics_buffer.append(metric)
        
        # Save to database if available
        if self.db_manager:
            try:
                metric_data = asdict(metric)
                metric_data["metric_type"] = metric.metric_type.value
                # This would save to database
                self.logger.debug(f"Metric stored: {metric.metric_name}")
            except Exception as e:
                self.logger.error(f"Database metric storage failed: {e}")
    
    async def _create_alert(self, level: AlertLevel, title: str, description: str, metadata: Dict[str, Any] = None):
        """Create a system alert"""
        try:
            alert_id = f"alert_{int(time.time() * 1000)}"
            
            alert = SystemAlert(
                alert_id=alert_id,
                alert_level=level,
                title=title,
                description=description,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            
            self.alerts[alert_id] = alert
            
            # Log alert
            log_level = {
                AlertLevel.INFO: logging.info,
                AlertLevel.WARNING: logging.warning,
                AlertLevel.ERROR: logging.error,
                AlertLevel.CRITICAL: logging.critical
            }.get(level, logging.info)
            
            log_level(f"ALERT [{level.value.upper()}] {title}: {description}")
            
            # Send notifications for critical alerts
            if level == AlertLevel.CRITICAL:
                await self._send_critical_alert_notification(alert)
            
        except Exception as e:
            self.logger.error(f"Alert creation failed: {e}")
    
    async def _check_error_rate(self):
        """Check if error rate exceeds threshold"""
        try:
            # Calculate error rate over last 10 minutes
            recent_requests = len([t for t in self.request_times if time.time() - t < 600])
            recent_errors = sum(count for count in self.error_counts.values())
            
            if recent_requests > 0:
                error_rate = (recent_errors / recent_requests) * 100
                
                if error_rate > self.alert_thresholds["error_rate"]:
                    await self._create_alert(
                        AlertLevel.ERROR,
                        "High Error Rate",
                        f"Error rate is {error_rate:.2f}% (threshold: {self.alert_thresholds['error_rate']}%)",
                        {"error_rate": error_rate, "recent_errors": recent_errors, "recent_requests": recent_requests}
                    )
        except Exception as e:
            self.logger.error(f"Error rate check failed: {e}")
    
    async def _check_system_alerts(self, metrics: Dict[str, Any]):
        """Check system metrics against alert thresholds"""
        try:
            checks = [
                ("cpu_usage", "High CPU Usage"),
                ("memory_usage", "High Memory Usage"),
                ("disk_usage", "High Disk Usage")
            ]
            
            for metric_name, alert_title in checks:
                if metric_name in metrics:
                    value = metrics[metric_name]
                    threshold = self.alert_thresholds[metric_name]
                    
                    if value > threshold:
                        await self._create_alert(
                            AlertLevel.WARNING,
                            alert_title,
                            f"{metric_name.replace('_', ' ').title()} is {value:.1f}% (threshold: {threshold}%)",
                            {"metric": metric_name, "value": value, "threshold": threshold}
                        )
        except Exception as e:
            self.logger.error(f"System alerts check failed: {e}")
    
    async def _send_critical_alert_notification(self, alert: SystemAlert):
        """Send notification for critical alerts"""
        try:
            # This would integrate with notification systems (email, Slack, etc.)
            self.logger.critical(f"CRITICAL ALERT NOTIFICATION: {alert.title}")
        except Exception as e:
            self.logger.error(f"Critical alert notification failed: {e}")
    
    async def _background_monitoring(self):
        """Background system monitoring"""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                await self.get_system_metrics()
            except Exception as e:
                self.logger.error(f"Background monitoring failed: {e}")
    
    async def _periodic_health_checks(self):
        """Run periodic health checks"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                for service_name in self.health_checks:
                    await self.run_health_check(service_name)
                    
            except Exception as e:
                self.logger.error(f"Periodic health checks failed: {e}")

# Health check functions
async def database_health_check() -> Dict[str, Any]:
    """Database health check"""
    try:
        # Mock database check
        return {"healthy": True, "response_time": 0.05, "connections": 5}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def storage_health_check() -> Dict[str, Any]:
    """Storage health check"""
    try:
        # Mock storage check
        return {"healthy": True, "available_space": "500GB", "connection": "ok"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def payment_health_check() -> Dict[str, Any]:
    """Payment service health check"""
    try:
        # Mock payment service check
        return {"healthy": True, "stripe_status": "operational", "last_transaction": "2024-01-01T12:00:00Z"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

# Factory function
def create_performance_monitor(db_manager=None, analytics_collector=None) -> PerformanceMonitor:
    """Create performance monitor with dependencies"""
    return PerformanceMonitor(db_manager, analytics_collector)

# Usage example
async def test_performance_monitor():
    """Test performance monitoring system"""
    monitor = create_performance_monitor()
    
    # Add health checks
    await monitor.add_health_check("database", database_health_check)
    await monitor.add_health_check("storage", storage_health_check)
    await monitor.add_health_check("payments", payment_health_check)
    
    # Track some metrics
    await monitor.track_request("GET", "/api/workouts", 0.15, 200)
    await monitor.track_error("validation_error", "Invalid workout data")
    
    # Get system metrics
    system_metrics = await monitor.get_system_metrics()
    print(f"System metrics: {system_metrics}")
    
    # Get performance summary
    summary = await monitor.get_performance_summary(1)
    print(f"Performance summary: {summary}")

if __name__ == "__main__":
    asyncio.run(test_performance_monitor())