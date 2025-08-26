"""
User Analytics and Plugin Usage Tracking System

Comprehensive analytics system for AI Fitness Coach that tracks:
- User behavior and engagement
- Plugin usage and performance
- Workout analytics and trends
- Revenue and conversion metrics
- Real-time dashboards and reporting
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid
from collections import defaultdict, Counter

# Analytics dependencies
try:
    import numpy as np
    import pandas as pd
    ANALYTICS_LIBS_AVAILABLE = True
except ImportError:
    ANALYTICS_LIBS_AVAILABLE = False
    logging.warning("Analytics libraries not available. Using basic tracking.")

class EventType(Enum):
    """Analytics event types"""
    # User Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    USER_PROFILE_UPDATE = "user_profile_update"
    
    # Workout Events
    WORKOUT_STARTED = "workout_started"
    WORKOUT_COMPLETED = "workout_completed"
    WORKOUT_PAUSED = "workout_paused"
    WORKOUT_RESUMED = "workout_resumed"
    EXERCISE_COMPLETED = "exercise_completed"
    
    # Plugin Events
    PLUGIN_VIEWED = "plugin_viewed"
    PLUGIN_TRIAL_STARTED = "plugin_trial_started"
    PLUGIN_PURCHASED = "plugin_purchased"
    PLUGIN_ACTIVATED = "plugin_activated"
    PLUGIN_DEACTIVATED = "plugin_deactivated"
    PLUGIN_USAGE = "plugin_usage"
    
    # Voice Events
    VOICE_COMMAND = "voice_command"
    VOICE_FEEDBACK = "voice_feedback"
    
    # UI Events
    PAGE_VIEW = "page_view"
    BUTTON_CLICK = "button_click"
    FEATURE_USED = "feature_used"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    API_ERROR = "api_error"
    
    # Business Events
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    event_id: str
    user_id: str
    session_id: str
    event_type: EventType
    timestamp: str
    properties: Dict[str, Any]
    device_info: Dict[str, Any] = None
    location_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.device_info is None:
            self.device_info = {}
        if self.location_info is None:
            self.location_info = {}

@dataclass
class UserSession:
    """User session tracking"""
    session_id: str
    user_id: str
    start_time: str
    end_time: Optional[str] = None
    page_views: int = 0
    events_count: int = 0
    device_type: str = "unknown"
    user_agent: str = ""
    ip_address: str = ""
    referrer: str = ""

@dataclass
class PluginUsageMetrics:
    """Plugin usage metrics"""
    plugin_id: str
    total_activations: int = 0
    total_usage_time: int = 0  # seconds
    unique_users: int = 0
    trial_conversions: int = 0
    average_session_time: float = 0.0
    retention_rate_7d: float = 0.0
    retention_rate_30d: float = 0.0
    error_rate: float = 0.0
    satisfaction_score: float = 0.0

@dataclass
class UserEngagementMetrics:
    """User engagement metrics"""
    user_id: str
    total_sessions: int = 0
    total_time_spent: int = 0  # seconds
    total_workouts: int = 0
    plugins_used: int = 0
    last_activity: str = ""
    engagement_score: float = 0.0
    retention_cohort: str = ""
    lifetime_value: float = 0.0

class AnalyticsCollector:
    """Main analytics collection system"""
    
    def __init__(self, db_manager=None, storage_manager=None):
        self.db_manager = db_manager
        self.storage_manager = storage_manager
        self.events_buffer = []
        self.sessions = {}
        self.plugin_metrics = {}
        self.user_metrics = {}
        self.logger = logging.getLogger(__name__)
        
        # Analytics configuration
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        self.retention_days = 90
        
        # Real-time metrics
        self.realtime_metrics = {
            "active_users": set(),
            "active_sessions": {},
            "current_workouts": 0,
            "plugin_usage": defaultdict(int),
            "error_count": 0
        }
        
        # Start background tasks
        asyncio.create_task(self._periodic_flush())
        asyncio.create_task(self._calculate_metrics())
    
    async def track_event(self, user_id: str, session_id: str, event_type: EventType, 
                         properties: Dict[str, Any] = None, device_info: Dict[str, Any] = None) -> str:
        """Track an analytics event"""
        try:
            event_id = str(uuid.uuid4())
            
            if properties is None:
                properties = {}
            
            event = AnalyticsEvent(
                event_id=event_id,
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                timestamp=datetime.now().isoformat(),
                properties=properties,
                device_info=device_info or {}
            )
            
            # Add to buffer
            self.events_buffer.append(event)
            
            # Update real-time metrics
            self._update_realtime_metrics(event)
            
            # Update session info
            await self._update_session(session_id, user_id, event_type)
            
            # Flush if buffer is full
            if len(self.events_buffer) >= self.buffer_size:
                await self._flush_events()
            
            self.logger.debug(f"Event tracked: {event_type.value} for user {user_id}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"Event tracking failed: {e}")
            return ""
    
    async def start_session(self, user_id: str, device_info: Dict[str, Any] = None) -> str:
        """Start a new user session"""
        try:
            session_id = str(uuid.uuid4())
            
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                start_time=datetime.now().isoformat(),
                device_type=device_info.get("device_type", "unknown") if device_info else "unknown",
                user_agent=device_info.get("user_agent", "") if device_info else "",
                ip_address=device_info.get("ip_address", "") if device_info else ""
            )
            
            self.sessions[session_id] = session
            self.realtime_metrics["active_users"].add(user_id)
            self.realtime_metrics["active_sessions"][session_id] = session
            
            # Track session start event
            await self.track_event(user_id, session_id, EventType.USER_LOGIN, {
                "device_type": session.device_type,
                "user_agent": session.user_agent
            })
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Session start failed: {e}")
            return ""
    
    async def end_session(self, session_id: str):
        """End a user session"""
        try:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.end_time = datetime.now().isoformat()
                
                # Calculate session duration
                start_time = datetime.fromisoformat(session.start_time)
                end_time = datetime.fromisoformat(session.end_time)
                duration = (end_time - start_time).total_seconds()
                
                # Track session end event
                await self.track_event(session.user_id, session_id, EventType.USER_LOGOUT, {
                    "session_duration": duration,
                    "page_views": session.page_views,
                    "events_count": session.events_count
                })
                
                # Remove from active tracking
                self.realtime_metrics["active_users"].discard(session.user_id)
                self.realtime_metrics["active_sessions"].pop(session_id, None)
            
        except Exception as e:
            self.logger.error(f"Session end failed: {e}")
    
    async def track_workout(self, user_id: str, session_id: str, workout_data: Dict[str, Any]):
        """Track workout completion"""
        try:
            await self.track_event(user_id, session_id, EventType.WORKOUT_COMPLETED, {
                "workout_type": workout_data.get("workout_type"),
                "duration": workout_data.get("duration"),
                "exercises_count": len(workout_data.get("exercises", [])),
                "total_volume": workout_data.get("total_volume"),
                "calories_burned": workout_data.get("calories_burned"),
                "difficulty_rating": workout_data.get("difficulty_rating")
            })
            
            # Update user metrics
            if user_id not in self.user_metrics:
                self.user_metrics[user_id] = UserEngagementMetrics(user_id=user_id)
            
            self.user_metrics[user_id].total_workouts += 1
            self.user_metrics[user_id].last_activity = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Workout tracking failed: {e}")
    
    async def track_plugin_usage(self, user_id: str, session_id: str, plugin_id: str, 
                                action: str, duration: int = 0, properties: Dict[str, Any] = None):
        """Track plugin usage"""
        try:
            event_properties = {
                "plugin_id": plugin_id,
                "action": action,
                "duration": duration
            }
            
            if properties:
                event_properties.update(properties)
            
            await self.track_event(user_id, session_id, EventType.PLUGIN_USAGE, event_properties)
            
            # Update plugin metrics
            if plugin_id not in self.plugin_metrics:
                self.plugin_metrics[plugin_id] = PluginUsageMetrics(plugin_id=plugin_id)
            
            metrics = self.plugin_metrics[plugin_id]
            
            if action == "activated":
                metrics.total_activations += 1
            elif action == "usage":
                metrics.total_usage_time += duration
            
            # Update real-time plugin usage
            self.realtime_metrics["plugin_usage"][plugin_id] += 1
            
        except Exception as e:
            self.logger.error(f"Plugin usage tracking failed: {e}")
    
    async def track_error(self, user_id: str, session_id: str, error_type: str, 
                         error_message: str, context: Dict[str, Any] = None):
        """Track error occurrence"""
        try:
            await self.track_event(user_id, session_id, EventType.ERROR_OCCURRED, {
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            })
            
            self.realtime_metrics["error_count"] += 1
            
        except Exception as e:
            self.logger.error(f"Error tracking failed: {e}")
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        try:
            # Get user events from the last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            user_events = []
            
            for event in self.events_buffer:
                if (event.user_id == user_id and 
                    datetime.fromisoformat(event.timestamp) >= cutoff_date):
                    user_events.append(event)
            
            # Calculate metrics
            total_sessions = len(set(event.session_id for event in user_events))
            total_events = len(user_events)
            
            # Event type breakdown
            event_counts = Counter(event.event_type.value for event in user_events)
            
            # Workout analytics
            workout_events = [e for e in user_events if e.event_type == EventType.WORKOUT_COMPLETED]
            total_workouts = len(workout_events)
            
            total_workout_time = sum(
                event.properties.get("duration", 0) for event in workout_events
            )
            
            # Plugin usage
            plugin_events = [e for e in user_events if e.event_type == EventType.PLUGIN_USAGE]
            unique_plugins = len(set(event.properties.get("plugin_id") for event in plugin_events))
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_sessions": total_sessions,
                "total_events": total_events,
                "total_workouts": total_workouts,
                "total_workout_time": total_workout_time,
                "unique_plugins_used": unique_plugins,
                "event_breakdown": dict(event_counts),
                "last_activity": max((event.timestamp for event in user_events), default=""),
                "engagement_score": self._calculate_engagement_score(user_events)
            }
            
        except Exception as e:
            self.logger.error(f"User analytics failed: {e}")
            return {}
    
    async def get_plugin_analytics(self, plugin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific plugin"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            plugin_events = []
            
            for event in self.events_buffer:
                if (event.properties.get("plugin_id") == plugin_id and 
                    datetime.fromisoformat(event.timestamp) >= cutoff_date):
                    plugin_events.append(event)
            
            # Calculate metrics
            unique_users = len(set(event.user_id for event in plugin_events))
            total_usage_events = len([e for e in plugin_events if e.event_type == EventType.PLUGIN_USAGE])
            
            # Usage time
            total_usage_time = sum(
                event.properties.get("duration", 0) 
                for event in plugin_events 
                if event.event_type == EventType.PLUGIN_USAGE
            )
            
            # Trial conversions
            trial_events = [e for e in plugin_events if e.event_type == EventType.PLUGIN_TRIAL_STARTED]
            purchase_events = [e for e in plugin_events if e.event_type == EventType.PLUGIN_PURCHASED]
            
            conversion_rate = (len(purchase_events) / len(trial_events) * 100) if trial_events else 0
            
            return {
                "plugin_id": plugin_id,
                "period_days": days,
                "unique_users": unique_users,
                "total_usage_events": total_usage_events,
                "total_usage_time": total_usage_time,
                "average_session_time": total_usage_time / total_usage_events if total_usage_events else 0,
                "trial_starts": len(trial_events),
                "purchases": len(purchase_events),
                "conversion_rate": round(conversion_rate, 2),
                "daily_active_users": self._calculate_daily_active_users(plugin_events)
            }
            
        except Exception as e:
            self.logger.error(f"Plugin analytics failed: {e}")
            return {}
    
    async def get_platform_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get overall platform analytics"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_events = [
                event for event in self.events_buffer
                if datetime.fromisoformat(event.timestamp) >= cutoff_date
            ]
            
            # User metrics
            unique_users = len(set(event.user_id for event in recent_events))
            total_sessions = len(set(event.session_id for event in recent_events))
            
            # Workout metrics
            workout_events = [e for e in recent_events if e.event_type == EventType.WORKOUT_COMPLETED]
            total_workouts = len(workout_events)
            
            # Plugin metrics
            plugin_events = [e for e in recent_events if e.event_type == EventType.PLUGIN_USAGE]
            plugin_usage_breakdown = Counter(
                event.properties.get("plugin_id") for event in plugin_events
            )
            
            # Error metrics
            error_events = [e for e in recent_events if e.event_type == EventType.ERROR_OCCURRED]
            error_rate = (len(error_events) / len(recent_events) * 100) if recent_events else 0
            
            # Revenue events
            payment_events = [e for e in recent_events if e.event_type == EventType.PAYMENT_COMPLETED]
            
            return {
                "period_days": days,
                "unique_users": unique_users,
                "total_sessions": total_sessions,
                "total_events": len(recent_events),
                "total_workouts": total_workouts,
                "plugin_usage": dict(plugin_usage_breakdown),
                "error_rate": round(error_rate, 2),
                "successful_payments": len(payment_events),
                "realtime_metrics": {
                    "active_users": len(self.realtime_metrics["active_users"]),
                    "active_sessions": len(self.realtime_metrics["active_sessions"]),
                    "current_workouts": self.realtime_metrics["current_workouts"],
                    "error_count": self.realtime_metrics["error_count"]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Platform analytics failed: {e}")
            return {}
    
    async def generate_report(self, report_type: str, period_days: int = 30) -> Dict[str, Any]:
        """Generate analytics report"""
        try:
            if report_type == "engagement":
                return await self._generate_engagement_report(period_days)
            elif report_type == "revenue":
                return await self._generate_revenue_report(period_days)
            elif report_type == "plugin_performance":
                return await self._generate_plugin_performance_report(period_days)
            elif report_type == "user_retention":
                return await self._generate_retention_report(period_days)
            else:
                raise ValueError(f"Unknown report type: {report_type}")
                
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return {}
    
    # Private helper methods
    def _update_realtime_metrics(self, event: AnalyticsEvent):
        """Update real-time metrics"""
        self.realtime_metrics["active_users"].add(event.user_id)
        
        if event.event_type == EventType.WORKOUT_STARTED:
            self.realtime_metrics["current_workouts"] += 1
        elif event.event_type == EventType.WORKOUT_COMPLETED:
            self.realtime_metrics["current_workouts"] = max(0, self.realtime_metrics["current_workouts"] - 1)
        elif event.event_type == EventType.ERROR_OCCURRED:
            self.realtime_metrics["error_count"] += 1
    
    async def _update_session(self, session_id: str, user_id: str, event_type: EventType):
        """Update session information"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.events_count += 1
            
            if event_type == EventType.PAGE_VIEW:
                session.page_views += 1
    
    async def _periodic_flush(self):
        """Periodically flush events to storage"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.events_buffer:
                    await self._flush_events()
            except Exception as e:
                self.logger.error(f"Periodic flush failed: {e}")
    
    async def _flush_events(self):
        """Flush events to database/storage"""
        if not self.events_buffer:
            return
        
        try:
            # Convert events to database format
            events_data = []
            for event in self.events_buffer:
                events_data.append({
                    "event_id": event.event_id,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp,
                    "properties": event.properties,
                    "device_info": event.device_info
                })
            
            # Save to database if available
            if self.db_manager:
                for event_data in events_data:
                    await self.db_manager.log_analytics_event(event_data)
            
            # Save to storage if available
            if self.storage_manager:
                events_json = json.dumps(events_data, indent=2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                storage_key = f"analytics/events_{timestamp}.json"
                
                await self.storage_manager.upload_file(
                    events_json.encode(),
                    storage_key,
                    "application/json"
                )
            
            # Clear buffer
            flushed_count = len(self.events_buffer)
            self.events_buffer.clear()
            
            self.logger.info(f"✅ Flushed {flushed_count} analytics events")
            
        except Exception as e:
            self.logger.error(f"Event flushing failed: {e}")
    
    async def _calculate_metrics(self):
        """Periodically calculate aggregated metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._update_plugin_metrics()
                await self._update_user_metrics()
            except Exception as e:
                self.logger.error(f"Metrics calculation failed: {e}")
    
    async def _update_plugin_metrics(self):
        """Update plugin metrics"""
        # This would calculate metrics from stored events
        pass
    
    async def _update_user_metrics(self):
        """Update user engagement metrics"""
        # This would calculate user engagement scores
        pass
    
    def _calculate_engagement_score(self, events: List[AnalyticsEvent]) -> float:
        """Calculate user engagement score"""
        if not events:
            return 0.0
        
        # Simple engagement scoring
        weights = {
            EventType.WORKOUT_COMPLETED: 10,
            EventType.PLUGIN_USAGE: 5,
            EventType.PAGE_VIEW: 1,
            EventType.BUTTON_CLICK: 2
        }
        
        score = sum(weights.get(event.event_type, 1) for event in events)
        return min(100.0, score / len(events) * 10)
    
    def _calculate_daily_active_users(self, events: List[AnalyticsEvent]) -> List[Dict[str, Any]]:
        """Calculate daily active users from events"""
        daily_users = defaultdict(set)
        
        for event in events:
            date = event.timestamp[:10]  # YYYY-MM-DD
            daily_users[date].add(event.user_id)
        
        return [
            {"date": date, "active_users": len(users)}
            for date, users in sorted(daily_users.items())
        ]
    
    async def _generate_engagement_report(self, days: int) -> Dict[str, Any]:
        """Generate user engagement report"""
        # Mock engagement report
        return {
            "report_type": "engagement",
            "period_days": days,
            "total_users": 1250,
            "active_users": 890,
            "average_session_time": 25.5,
            "bounce_rate": 15.2,
            "retention_rate": 68.5
        }
    
    async def _generate_revenue_report(self, days: int) -> Dict[str, Any]:
        """Generate revenue report"""
        # Mock revenue report
        return {
            "report_type": "revenue",
            "period_days": days,
            "total_revenue": 5420.50,
            "plugin_revenue": 3850.00,
            "subscription_revenue": 1570.50,
            "conversion_rate": 12.8,
            "average_order_value": 18.75
        }
    
    async def _generate_plugin_performance_report(self, days: int) -> Dict[str, Any]:
        """Generate plugin performance report"""
        # Mock plugin performance report
        return {
            "report_type": "plugin_performance",
            "period_days": days,
            "top_plugins": [
                {"plugin_id": "golf_pro", "users": 245, "revenue": 3910.55},
                {"plugin_id": "tennis_pro", "users": 189, "revenue": 2451.11},
                {"plugin_id": "basketball_skills", "users": 156, "revenue": 2340.44}
            ],
            "trial_conversion_rate": 24.5,
            "average_usage_time": 42.3
        }
    
    async def _generate_retention_report(self, days: int) -> Dict[str, Any]:
        """Generate user retention report"""
        # Mock retention report
        return {
            "report_type": "user_retention",
            "period_days": days,
            "day_1_retention": 85.2,
            "day_7_retention": 65.8,
            "day_30_retention": 42.1,
            "cohort_analysis": {
                "2024_01": {"users": 150, "retention_30d": 45.2},
                "2024_02": {"users": 180, "retention_30d": 42.8},
                "2024_03": {"users": 220, "retention_30d": 48.1}
            }
        }

# Factory function
def create_analytics_collector(db_manager=None, storage_manager=None) -> AnalyticsCollector:
    """Create analytics collector with dependencies"""
    return AnalyticsCollector(db_manager, storage_manager)

# Usage example
async def test_analytics():
    """Test analytics system"""
    collector = create_analytics_collector()
    
    # Start session
    session_id = await collector.start_session("test_user", {
        "device_type": "mobile",
        "user_agent": "Test App/1.0"
    })
    
    # Track some events
    await collector.track_event("test_user", session_id, EventType.PAGE_VIEW, {
        "page": "/dashboard"
    })
    
    await collector.track_plugin_usage("test_user", session_id, "golf_pro", "activated")
    
    # Get analytics
    user_analytics = await collector.get_user_analytics("test_user")
    print(f"User analytics: {user_analytics}")
    
    platform_analytics = await collector.get_platform_analytics()
    print(f"Platform analytics: {platform_analytics}")

if __name__ == "__main__":
    asyncio.run(test_analytics())