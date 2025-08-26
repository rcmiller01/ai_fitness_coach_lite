"""
A/B Testing API Endpoints

FastAPI endpoints for managing A/B testing experiments:
- Create and manage experiments
- User assignment and variant serving
- Event tracking for experiment metrics
- Results and analytics endpoints
- Admin interface for experiment management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

from ..core.ab_testing import (
    ABTestingFramework, 
    Experiment, 
    ExperimentVariant, 
    ExperimentMetric,
    ExperimentResults,
    ExperimentStatus,
    VariantType,
    MetricType,
    create_ab_testing_framework,
    create_plugin_recommendation_experiment
)

# Initialize router
router = APIRouter(prefix="/api/ab-testing", tags=["A/B Testing"])
security = HTTPBearer()

# Global framework instance
ab_framework: Optional[ABTestingFramework] = None

def get_ab_framework() -> ABTestingFramework:
    """Get A/B testing framework instance"""
    global ab_framework
    if ab_framework is None:
        ab_framework = create_ab_testing_framework()
    return ab_framework

# Pydantic models for API
class ExperimentVariantCreate(BaseModel):
    name: str
    variant_type: str = Field(..., regex="^(control|treatment)$")
    traffic_allocation: float = Field(..., ge=0.0, le=1.0)
    configuration: Dict[str, Any]
    description: str = ""

class ExperimentMetricCreate(BaseModel):
    metric_type: str
    name: str
    description: str
    target_value: Optional[float] = None
    is_primary: bool = False

class ExperimentCreate(BaseModel):
    name: str
    description: str
    variants: List[ExperimentVariantCreate]
    metrics: List[ExperimentMetricCreate]
    target_audience: Dict[str, Any] = {}
    end_date: str
    sample_size: int = 1000
    confidence_level: float = 0.95
    minimum_effect_size: float = 0.05

class EventTrack(BaseModel):
    metric_id: str
    event_type: str
    event_value: float = 1.0
    metadata: Dict[str, Any] = {}

class ExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    description: str
    status: str
    variants: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    start_date: Optional[str]
    end_date: str
    created_at: str

class UserExperimentResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    variant_id: str
    variant_name: str
    configuration: Dict[str, Any]

# Admin endpoints
@router.post("/experiments", response_model=Dict[str, str])
async def create_experiment(
    experiment_data: ExperimentCreate,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Create a new A/B testing experiment"""
    try:
        # Convert API models to core models
        variants = []
        for v_data in experiment_data.variants:
            variant = ExperimentVariant(
                variant_id=f"variant_{len(variants)}",
                name=v_data.name,
                variant_type=VariantType(v_data.variant_type),
                traffic_allocation=v_data.traffic_allocation,
                configuration=v_data.configuration,
                description=v_data.description
            )
            variants.append(variant)
        
        metrics = []
        for m_data in experiment_data.metrics:
            metric = ExperimentMetric(
                metric_id=f"metric_{len(metrics)}",
                metric_type=MetricType(m_data.metric_type),
                name=m_data.name,
                description=m_data.description,
                target_value=m_data.target_value,
                is_primary=m_data.is_primary
            )
            metrics.append(metric)
        
        # Create experiment
        experiment = Experiment(
            experiment_id=f"exp_{int(datetime.now().timestamp())}",
            name=experiment_data.name,
            description=experiment_data.description,
            status=ExperimentStatus.DRAFT,
            variants=variants,
            metrics=metrics,
            target_audience=experiment_data.target_audience,
            start_date="",
            end_date=experiment_data.end_date,
            created_by="api_user",
            created_at=datetime.now().isoformat(),
            sample_size=experiment_data.sample_size,
            confidence_level=experiment_data.confidence_level,
            minimum_effect_size=experiment_data.minimum_effect_size
        )
        
        experiment_id = await framework.create_experiment(experiment)
        
        return {"experiment_id": experiment_id, "status": "created"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Start an experiment"""
    try:
        success = await framework.start_experiment(experiment_id)
        if success:
            return {"status": "started", "experiment_id": experiment_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to start experiment")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[str] = None,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """List all experiments with optional status filter"""
    try:
        experiments = []
        for exp in framework.experiments.values():
            if status is None or exp.status.value == status:
                experiments.append(ExperimentResponse(
                    experiment_id=exp.experiment_id,
                    name=exp.name,
                    description=exp.description,
                    status=exp.status.value,
                    variants=[{
                        "variant_id": v.variant_id,
                        "name": v.name,
                        "variant_type": v.variant_type.value,
                        "traffic_allocation": v.traffic_allocation,
                        "configuration": v.configuration
                    } for v in exp.variants],
                    metrics=[{
                        "metric_id": m.metric_id,
                        "metric_type": m.metric_type.value,
                        "name": m.name,
                        "description": m.description,
                        "is_primary": m.is_primary
                    } for m in exp.metrics],
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    created_at=exp.created_at
                ))
        
        return experiments
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Get experiment results and analysis"""
    try:
        results = await framework.get_experiment_results(experiment_id)
        if results is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        return {
            "experiment_id": results.experiment_id,
            "variant_results": results.variant_results,
            "statistical_significance": results.statistical_significance,
            "confidence_intervals": {
                variant_id: {"lower": ci[0], "upper": ci[1]}
                for variant_id, ci in results.confidence_intervals.items()
            },
            "sample_sizes": results.sample_sizes,
            "recommendations": results.recommendations,
            "generated_at": results.generated_at
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User-facing endpoints
@router.get("/users/{user_id}/experiments", response_model=List[UserExperimentResponse])
async def get_user_experiments(
    user_id: str,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Get active experiments for a user"""
    try:
        experiments = await framework.get_active_experiments_for_user(user_id)
        return [UserExperimentResponse(**exp) for exp in experiments]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/experiments/{experiment_id}/assign")
async def assign_user_to_experiment(
    user_id: str,
    experiment_id: str,
    session_id: Optional[str] = None,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Assign user to experiment variant"""
    try:
        variant_id = await framework.assign_user_to_experiment(
            user_id, experiment_id, session_id
        )
        
        if variant_id:
            return {
                "user_id": user_id,
                "experiment_id": experiment_id,
                "variant_id": variant_id,
                "assigned_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to assign user to experiment")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{user_id}/experiments/{experiment_id}/events")
async def track_experiment_event(
    user_id: str,
    experiment_id: str,
    event_data: EventTrack,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Track user event for experiment analysis"""
    try:
        event_id = await framework.track_experiment_event(
            user_id=user_id,
            experiment_id=experiment_id,
            metric_id=event_data.metric_id,
            event_type=event_data.event_type,
            event_value=event_data.event_value,
            metadata=event_data.metadata
        )
        
        if event_id:
            return {
                "event_id": event_id,
                "user_id": user_id,
                "experiment_id": experiment_id,
                "status": "tracked"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to track event")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Feature flag endpoints
@router.get("/users/{user_id}/features/{feature_name}")
async def get_feature_flag(
    user_id: str,
    feature_name: str,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Get feature flag value for user (based on experiments)"""
    try:
        user_experiments = await framework.get_active_experiments_for_user(user_id)
        
        # Look for experiment that controls this feature
        for exp in user_experiments:
            config = exp.get("configuration", {})
            if feature_name in config:
                return {
                    "feature_name": feature_name,
                    "value": config[feature_name],
                    "experiment_id": exp["experiment_id"],
                    "variant_id": exp["variant_id"]
                }
        
        # Default value if no experiment found
        return {
            "feature_name": feature_name,
            "value": False,
            "experiment_id": None,
            "variant_id": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Plugin recommendation experiment helpers
@router.post("/experiments/plugin-recommendation")
async def create_plugin_rec_experiment(
    name: str,
    control_algorithm: str,
    treatment_algorithm: str,
    target_users: Dict[str, Any] = {},
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Create a plugin recommendation A/B test"""
    try:
        experiment_id = await create_plugin_recommendation_experiment(
            framework, name, control_algorithm, treatment_algorithm, target_users
        )
        
        return {
            "experiment_id": experiment_id,
            "name": name,
            "type": "plugin_recommendation",
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}/plugin-recommendations")
async def get_plugin_recommendations(
    user_id: str,
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Get plugin recommendations based on active experiments"""
    try:
        # Get user's active experiments
        user_experiments = await framework.get_active_experiments_for_user(user_id)
        
        # Find plugin recommendation experiments
        rec_experiments = [
            exp for exp in user_experiments
            if "algorithm" in exp.get("configuration", {})
        ]
        
        recommendations = []
        
        if rec_experiments:
            # Use experimental algorithm
            exp = rec_experiments[0]  # Use first matching experiment
            algorithm = exp["configuration"]["algorithm"]
            
            # Mock recommendations based on algorithm
            if algorithm == "collaborative_filtering":
                recommendations = [
                    {"plugin_id": "tennis_pro", "score": 0.95, "reason": "Similar users liked this"},
                    {"plugin_id": "golf_swing", "score": 0.88, "reason": "Based on your activity"},
                    {"plugin_id": "basketball_skills", "score": 0.82, "reason": "Trending in your area"}
                ]
            elif algorithm == "content_based":
                recommendations = [
                    {"plugin_id": "yoga_flow", "score": 0.92, "reason": "Matches your preferences"},
                    {"plugin_id": "strength_training", "score": 0.85, "reason": "Complements your workouts"},
                    {"plugin_id": "cardio_blast", "score": 0.78, "reason": "For your fitness goals"}
                ]
            else:
                recommendations = [
                    {"plugin_id": "tennis_pro", "score": 0.85, "reason": "Popular choice"},
                    {"plugin_id": "golf_swing", "score": 0.80, "reason": "Highly rated"},
                    {"plugin_id": "basketball_skills", "score": 0.75, "reason": "New release"}
                ]
            
            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "algorithm": algorithm,
                "experiment_id": exp["experiment_id"],
                "variant_id": exp["variant_id"]
            }
        else:
            # Default recommendations
            recommendations = [
                {"plugin_id": "tennis_pro", "score": 0.80, "reason": "Default recommendation"},
                {"plugin_id": "golf_swing", "score": 0.75, "reason": "Popular choice"},
                {"plugin_id": "basketball_skills", "score": 0.70, "reason": "Trending"}
            ]
            
            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "algorithm": "default",
                "experiment_id": None,
                "variant_id": None
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@router.get("/health")
async def ab_testing_health():
    """Health check for A/B testing system"""
    try:
        framework = get_ab_framework()
        return {
            "status": "healthy",
            "service": "ab_testing",
            "experiments_count": len(framework.experiments),
            "assignments_count": len(framework.user_assignments),
            "events_count": len(framework.experiment_events),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ab_testing",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Analytics endpoint
@router.get("/analytics/summary")
async def get_ab_testing_analytics(
    framework: ABTestingFramework = Depends(get_ab_framework)
):
    """Get A/B testing analytics summary"""
    try:
        total_experiments = len(framework.experiments)
        active_experiments = len([
            exp for exp in framework.experiments.values()
            if exp.status == ExperimentStatus.ACTIVE
        ])
        
        total_users_in_experiments = len(set(
            assignment.user_id for assignment in framework.user_assignments.values()
        ))
        
        total_events = len(framework.experiment_events)
        
        # Recent activity (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_events = [
            event for event in framework.experiment_events
            if datetime.fromisoformat(event.timestamp) >= cutoff_time
        ]
        
        return {
            "total_experiments": total_experiments,
            "active_experiments": active_experiments,
            "total_users_in_experiments": total_users_in_experiments,
            "total_events": total_events,
            "recent_events_24h": len(recent_events),
            "experiment_status_breakdown": {
                status.value: len([
                    exp for exp in framework.experiments.values()
                    if exp.status == status
                ]) for status in ExperimentStatus
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))