"""
A/B Testing Framework for Plugin Recommendations

Comprehensive A/B testing system that allows:
- Creating and managing experiments for plugin recommendations
- User segmentation for targeted testing
- Statistical analysis of conversion rates
- Real-time experiment monitoring
- Feature flag integration
"""

import os
import time
import asyncio
import logging
import hashlib
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

class ExperimentStatus(Enum):
    """Experiment status states"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class VariantType(Enum):
    """A/B test variant types"""
    CONTROL = "control"
    TREATMENT = "treatment"

class MetricType(Enum):
    """Experiment metric types"""
    CONVERSION_RATE = "conversion_rate"
    CLICK_THROUGH_RATE = "click_through_rate"
    PURCHASE_RATE = "purchase_rate"
    ENGAGEMENT_TIME = "engagement_time"
    PLUGIN_DOWNLOADS = "plugin_downloads"

@dataclass
class ExperimentVariant:
    """A/B test variant configuration"""
    variant_id: str
    name: str
    variant_type: VariantType
    traffic_allocation: float  # Percentage of traffic (0.0-1.0)
    configuration: Dict[str, Any]
    description: str = ""
    
    def __post_init__(self):
        if not 0.0 <= self.traffic_allocation <= 1.0:
            raise ValueError("Traffic allocation must be between 0.0 and 1.0")

@dataclass
class ExperimentMetric:
    """Experiment success metric"""
    metric_id: str
    metric_type: MetricType
    name: str
    description: str
    target_value: float = None
    is_primary: bool = False

@dataclass
class Experiment:
    """A/B testing experiment"""
    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus
    variants: List[ExperimentVariant]
    metrics: List[ExperimentMetric]
    target_audience: Dict[str, Any]
    start_date: str
    end_date: str
    created_by: str
    created_at: str
    sample_size: int = 1000
    confidence_level: float = 0.95
    minimum_effect_size: float = 0.05
    
    def __post_init__(self):
        # Validate traffic allocation sums to 1.0
        total_allocation = sum(v.traffic_allocation for v in self.variants)
        if abs(total_allocation - 1.0) > 0.001:
            raise ValueError(f"Variant traffic allocations must sum to 1.0, got {total_allocation}")

@dataclass
class UserAssignment:
    """User assignment to experiment variant"""
    user_id: str
    experiment_id: str
    variant_id: str
    assigned_at: str
    session_id: Optional[str] = None

@dataclass
class ExperimentEvent:
    """User interaction event for experiment tracking"""
    event_id: str
    user_id: str
    experiment_id: str
    variant_id: str
    metric_id: str
    event_type: str
    event_value: float
    timestamp: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ExperimentResults:
    """Experiment statistical results"""
    experiment_id: str
    variant_results: Dict[str, Dict[str, Any]]
    statistical_significance: Dict[str, bool]
    confidence_intervals: Dict[str, Tuple[float, float]]
    sample_sizes: Dict[str, int]
    generated_at: str
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []

class ABTestingFramework:
    """Main A/B testing framework"""
    
    def __init__(self, db_manager=None, analytics_collector=None):
        self.db_manager = db_manager
        self.analytics_collector = analytics_collector
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage (for development/testing)
        self.experiments = {}
        self.user_assignments = {}
        self.experiment_events = []
        
        # Configuration
        self.data_dir = "data/ab_testing"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing data
        self._load_experiments()
    
    async def create_experiment(self, experiment: Experiment) -> str:
        """Create a new A/B testing experiment"""
        try:
            # Validate experiment
            self._validate_experiment(experiment)
            
            # Store experiment
            self.experiments[experiment.experiment_id] = experiment
            
            # Save to storage
            await self._save_experiment(experiment)
            
            # Track experiment creation
            if self.analytics_collector:
                await self.analytics_collector.track_event(
                    experiment.created_by,
                    "system_session",
                    "experiment_created",
                    {"experiment_id": experiment.experiment_id, "name": experiment.name}
                )
            
            self.logger.info(f"Experiment created: {experiment.name} ({experiment.experiment_id})")
            return experiment.experiment_id
            
        except Exception as e:
            self.logger.error(f"Failed to create experiment: {e}")
            raise
    
    async def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment"""
        try:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment not found: {experiment_id}")
            
            experiment = self.experiments[experiment_id]
            
            # Validate experiment can be started
            if experiment.status != ExperimentStatus.DRAFT:
                raise ValueError(f"Experiment must be in DRAFT status to start, current: {experiment.status}")
            
            # Update status
            experiment.status = ExperimentStatus.ACTIVE
            experiment.start_date = datetime.now().isoformat()
            
            # Save changes
            await self._save_experiment(experiment)
            
            self.logger.info(f"Experiment started: {experiment.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start experiment: {e}")
            return False
    
    async def assign_user_to_experiment(self, user_id: str, experiment_id: str, 
                                      session_id: str = None) -> Optional[str]:
        """Assign user to experiment variant"""
        try:
            if experiment_id not in self.experiments:
                return None
            
            experiment = self.experiments[experiment_id]
            
            # Check if experiment is active
            if experiment.status != ExperimentStatus.ACTIVE:
                return None
            
            # Check if user already assigned
            assignment_key = f"{user_id}:{experiment_id}"
            if assignment_key in self.user_assignments:
                return self.user_assignments[assignment_key].variant_id
            
            # Check if user qualifies for experiment
            if not self._user_qualifies_for_experiment(user_id, experiment):
                return None
            
            # Assign to variant based on hash
            variant_id = self._assign_variant(user_id, experiment)
            
            # Create assignment record
            assignment = UserAssignment(
                user_id=user_id,
                experiment_id=experiment_id,
                variant_id=variant_id,
                assigned_at=datetime.now().isoformat(),
                session_id=session_id
            )
            
            self.user_assignments[assignment_key] = assignment
            
            # Save assignment
            await self._save_user_assignment(assignment)
            
            self.logger.debug(f"User {user_id} assigned to variant {variant_id} in experiment {experiment_id}")
            return variant_id
            
        except Exception as e:
            self.logger.error(f"Failed to assign user to experiment: {e}")
            return None
    
    async def track_experiment_event(self, user_id: str, experiment_id: str, 
                                   metric_id: str, event_type: str, 
                                   event_value: float = 1.0, 
                                   metadata: Dict[str, Any] = None) -> str:
        """Track user event for experiment analysis"""
        try:
            # Get user's variant assignment
            assignment_key = f"{user_id}:{experiment_id}"
            if assignment_key not in self.user_assignments:
                self.logger.warning(f"No assignment found for user {user_id} in experiment {experiment_id}")
                return ""
            
            assignment = self.user_assignments[assignment_key]
            
            # Create event
            event = ExperimentEvent(
                event_id=str(uuid.uuid4()),
                user_id=user_id,
                experiment_id=experiment_id,
                variant_id=assignment.variant_id,
                metric_id=metric_id,
                event_type=event_type,
                event_value=event_value,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            
            # Store event
            self.experiment_events.append(event)
            
            # Save to storage
            await self._save_experiment_event(event)
            
            self.logger.debug(f"Event tracked: {event_type} for user {user_id}")
            return event.event_id
            
        except Exception as e:
            self.logger.error(f"Failed to track experiment event: {e}")
            return ""
    
    async def get_experiment_results(self, experiment_id: str) -> Optional[ExperimentResults]:
        """Get statistical results for an experiment"""
        try:
            if experiment_id not in self.experiments:
                return None
            
            experiment = self.experiments[experiment_id]
            
            # Get events for this experiment
            experiment_events = [
                event for event in self.experiment_events
                if event.experiment_id == experiment_id
            ]
            
            # Calculate results for each variant
            variant_results = {}
            sample_sizes = {}
            
            for variant in experiment.variants:
                variant_events = [
                    event for event in experiment_events
                    if event.variant_id == variant.variant_id
                ]
                
                # Count unique users in this variant
                unique_users = set(event.user_id for event in variant_events)
                sample_sizes[variant.variant_id] = len(unique_users)
                
                # Calculate metrics
                variant_metrics = {}
                for metric in experiment.metrics:
                    metric_events = [
                        event for event in variant_events
                        if event.metric_id == metric.metric_id
                    ]
                    
                    if metric.metric_type == MetricType.CONVERSION_RATE:
                        conversions = len(set(event.user_id for event in metric_events))
                        conversion_rate = conversions / len(unique_users) if unique_users else 0
                        variant_metrics[metric.metric_id] = {
                            "value": conversion_rate,
                            "count": conversions,
                            "total_users": len(unique_users)
                        }
                    elif metric.metric_type == MetricType.CLICK_THROUGH_RATE:
                        clicks = len(metric_events)
                        ctr = clicks / len(unique_users) if unique_users else 0
                        variant_metrics[metric.metric_id] = {
                            "value": ctr,
                            "clicks": clicks,
                            "total_users": len(unique_users)
                        }
                    else:
                        # For other metrics, calculate average
                        values = [event.event_value for event in metric_events]
                        avg_value = sum(values) / len(values) if values else 0
                        variant_metrics[metric.metric_id] = {
                            "value": avg_value,
                            "count": len(values),
                            "total": sum(values)
                        }
                
                variant_results[variant.variant_id] = variant_metrics
            
            # Calculate statistical significance (simplified)
            significance = self._calculate_statistical_significance(variant_results, experiment)
            confidence_intervals = self._calculate_confidence_intervals(variant_results, experiment)
            recommendations = self._generate_recommendations(variant_results, experiment)
            
            results = ExperimentResults(
                experiment_id=experiment_id,
                variant_results=variant_results,
                statistical_significance=significance,
                confidence_intervals=confidence_intervals,
                sample_sizes=sample_sizes,
                generated_at=datetime.now().isoformat(),
                recommendations=recommendations
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get experiment results: {e}")
            return None
    
    async def get_active_experiments_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active experiments for a user"""
        try:
            active_experiments = []
            
            for experiment in self.experiments.values():
                if experiment.status == ExperimentStatus.ACTIVE:
                    # Check if user is assigned
                    assignment_key = f"{user_id}:{experiment.experiment_id}"
                    if assignment_key in self.user_assignments:
                        assignment = self.user_assignments[assignment_key]
                        variant = next(
                            (v for v in experiment.variants if v.variant_id == assignment.variant_id),
                            None
                        )
                        
                        active_experiments.append({
                            "experiment_id": experiment.experiment_id,
                            "experiment_name": experiment.name,
                            "variant_id": assignment.variant_id,
                            "variant_name": variant.name if variant else "Unknown",
                            "configuration": variant.configuration if variant else {}
                        })
            
            return active_experiments
            
        except Exception as e:
            self.logger.error(f"Failed to get active experiments for user: {e}")
            return []
    
    # Private helper methods
    def _validate_experiment(self, experiment: Experiment):
        """Validate experiment configuration"""
        if len(experiment.variants) < 2:
            raise ValueError("Experiment must have at least 2 variants")
        
        if len(experiment.metrics) == 0:
            raise ValueError("Experiment must have at least 1 metric")
        
        # Check for control variant
        control_variants = [v for v in experiment.variants if v.variant_type == VariantType.CONTROL]
        if len(control_variants) != 1:
            raise ValueError("Experiment must have exactly 1 control variant")
    
    def _user_qualifies_for_experiment(self, user_id: str, experiment: Experiment) -> bool:
        """Check if user qualifies for experiment based on targeting rules"""
        try:
            target_audience = experiment.target_audience
            
            # Simple qualification logic (can be extended)
            if "user_segments" in target_audience:
                # This would check user segments from analytics
                pass
            
            if "user_properties" in target_audience:
                # This would check user properties
                pass
            
            # For now, qualify all users
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking user qualification: {e}")
            return False
    
    def _assign_variant(self, user_id: str, experiment: Experiment) -> str:
        """Assign user to variant using consistent hashing"""
        # Create hash from user_id and experiment_id for consistency
        hash_input = f"{user_id}:{experiment.experiment_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        hash_number = int(hash_value[:8], 16) / (16**8)  # Convert to 0-1 range
        
        # Assign based on traffic allocation
        cumulative_allocation = 0.0
        for variant in experiment.variants:
            cumulative_allocation += variant.traffic_allocation
            if hash_number <= cumulative_allocation:
                return variant.variant_id
        
        # Fallback to control variant
        control_variant = next(v for v in experiment.variants if v.variant_type == VariantType.CONTROL)
        return control_variant.variant_id
    
    def _calculate_statistical_significance(self, variant_results: Dict, experiment: Experiment) -> Dict[str, bool]:
        """Calculate statistical significance (simplified implementation)"""
        significance = {}
        
        # Find control variant
        control_variant = next(v for v in experiment.variants if v.variant_type == VariantType.CONTROL)
        control_id = control_variant.variant_id
        
        for variant in experiment.variants:
            if variant.variant_type == VariantType.TREATMENT:
                # Simple significance check based on sample size and effect size
                control_data = variant_results.get(control_id, {})
                treatment_data = variant_results.get(variant.variant_id, {})
                
                # Use primary metric for significance
                primary_metric = next((m for m in experiment.metrics if m.is_primary), experiment.metrics[0])
                
                control_metric = control_data.get(primary_metric.metric_id, {})
                treatment_metric = treatment_data.get(primary_metric.metric_id, {})
                
                control_value = control_metric.get("value", 0)
                treatment_value = treatment_metric.get("value", 0)
                
                # Simple effect size check
                if control_value > 0:
                    effect_size = abs(treatment_value - control_value) / control_value
                    significance[variant.variant_id] = effect_size >= experiment.minimum_effect_size
                else:
                    significance[variant.variant_id] = False
        
        return significance
    
    def _calculate_confidence_intervals(self, variant_results: Dict, experiment: Experiment) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals (simplified)"""
        intervals = {}
        
        for variant in experiment.variants:
            variant_data = variant_results.get(variant.variant_id, {})
            primary_metric = next((m for m in experiment.metrics if m.is_primary), experiment.metrics[0])
            metric_data = variant_data.get(primary_metric.metric_id, {})
            
            value = metric_data.get("value", 0)
            # Simplified confidence interval (normally would use proper statistical calculation)
            margin = value * 0.1  # 10% margin as approximation
            intervals[variant.variant_id] = (max(0, value - margin), value + margin)
        
        return intervals
    
    def _generate_recommendations(self, variant_results: Dict, experiment: Experiment) -> List[str]:
        """Generate experiment recommendations"""
        recommendations = []
        
        # Find control and best performing variant
        control_variant = next(v for v in experiment.variants if v.variant_type == VariantType.CONTROL)
        primary_metric = next((m for m in experiment.metrics if m.is_primary), experiment.metrics[0])
        
        control_value = variant_results.get(control_variant.variant_id, {}).get(primary_metric.metric_id, {}).get("value", 0)
        
        best_variant = None
        best_value = control_value
        
        for variant in experiment.variants:
            if variant.variant_type == VariantType.TREATMENT:
                variant_value = variant_results.get(variant.variant_id, {}).get(primary_metric.metric_id, {}).get("value", 0)
                if variant_value > best_value:
                    best_value = variant_value
                    best_variant = variant
        
        if best_variant:
            improvement = ((best_value - control_value) / control_value * 100) if control_value > 0 else 0
            recommendations.append(f"Variant '{best_variant.name}' shows {improvement:.1f}% improvement over control")
            
            if improvement > 10:
                recommendations.append(f"Consider implementing variant '{best_variant.name}' for all users")
            elif improvement > 5:
                recommendations.append(f"Variant '{best_variant.name}' shows promising results, consider extending test duration")
            else:
                recommendations.append("No significant improvement detected, consider testing different approaches")
        else:
            recommendations.append("Control variant is performing best, maintain current implementation")
        
        return recommendations
    
    # Storage methods
    async def _save_experiment(self, experiment: Experiment):
        """Save experiment to storage"""
        try:
            file_path = os.path.join(self.data_dir, f"experiment_{experiment.experiment_id}.json")
            
            # Convert experiment to serializable dict
            experiment_data = {
                "experiment_id": experiment.experiment_id,
                "name": experiment.name,
                "description": experiment.description,
                "status": experiment.status.value,
                "variants": [
                    {
                        "variant_id": v.variant_id,
                        "name": v.name,
                        "variant_type": v.variant_type.value,
                        "traffic_allocation": v.traffic_allocation,
                        "configuration": v.configuration,
                        "description": v.description
                    } for v in experiment.variants
                ],
                "metrics": [
                    {
                        "metric_id": m.metric_id,
                        "metric_type": m.metric_type.value,
                        "name": m.name,
                        "description": m.description,
                        "target_value": m.target_value,
                        "is_primary": m.is_primary
                    } for m in experiment.metrics
                ],
                "target_audience": experiment.target_audience,
                "start_date": experiment.start_date,
                "end_date": experiment.end_date,
                "created_by": experiment.created_by,
                "created_at": experiment.created_at,
                "sample_size": experiment.sample_size,
                "confidence_level": experiment.confidence_level,
                "minimum_effect_size": experiment.minimum_effect_size
            }
            
            with open(file_path, 'w') as f:
                json.dump(experiment_data, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save experiment: {e}")
    
    async def _save_user_assignment(self, assignment: UserAssignment):
        """Save user assignment to storage"""
        try:
            assignments_file = os.path.join(self.data_dir, "user_assignments.jsonl")
            assignment_data = asdict(assignment)
            
            with open(assignments_file, 'a') as f:
                f.write(json.dumps(assignment_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to save user assignment: {e}")
    
    async def _save_experiment_event(self, event: ExperimentEvent):
        """Save experiment event to storage"""
        try:
            events_file = os.path.join(self.data_dir, "experiment_events.jsonl")
            event_data = asdict(event)
            
            with open(events_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to save experiment event: {e}")
    
    def _load_experiments(self):
        """Load experiments from storage"""
        try:
            if not os.path.exists(self.data_dir):
                return
            
            for filename in os.listdir(self.data_dir):
                if filename.startswith("experiment_") and filename.endswith(".json"):
                    file_path = os.path.join(self.data_dir, filename)
                    with open(file_path, 'r') as f:
                        experiment_data = json.load(f)
                    
                    # Convert back to objects
                    experiment_data["status"] = ExperimentStatus(experiment_data["status"])
                    
                    # Reconstruct variants
                    variants = []
                    for v_data in experiment_data["variants"]:
                        variant = ExperimentVariant(
                            variant_id=v_data["variant_id"],
                            name=v_data["name"],
                            variant_type=VariantType(v_data["variant_type"]),
                            traffic_allocation=v_data["traffic_allocation"],
                            configuration=v_data["configuration"],
                            description=v_data.get("description", "")
                        )
                        variants.append(variant)
                    
                    # Reconstruct metrics
                    metrics = []
                    for m_data in experiment_data["metrics"]:
                        metric = ExperimentMetric(
                            metric_id=m_data["metric_id"],
                            metric_type=MetricType(m_data["metric_type"]),
                            name=m_data["name"],
                            description=m_data["description"],
                            target_value=m_data.get("target_value"),
                            is_primary=m_data.get("is_primary", False)
                        )
                        metrics.append(metric)
                    
                    # Create experiment object
                    experiment = Experiment(
                        experiment_id=experiment_data["experiment_id"],
                        name=experiment_data["name"],
                        description=experiment_data["description"],
                        status=experiment_data["status"],
                        variants=variants,
                        metrics=metrics,
                        target_audience=experiment_data["target_audience"],
                        start_date=experiment_data["start_date"],
                        end_date=experiment_data["end_date"],
                        created_by=experiment_data["created_by"],
                        created_at=experiment_data["created_at"],
                        sample_size=experiment_data.get("sample_size", 1000),
                        confidence_level=experiment_data.get("confidence_level", 0.95),
                        minimum_effect_size=experiment_data.get("minimum_effect_size", 0.05)
                    )
                    
                    self.experiments[experiment.experiment_id] = experiment
            
            # Load user assignments
            assignments_file = os.path.join(self.data_dir, "user_assignments.jsonl")
            if os.path.exists(assignments_file):
                with open(assignments_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            assignment_data = json.loads(line.strip())
                            assignment = UserAssignment(**assignment_data)
                            key = f"{assignment.user_id}:{assignment.experiment_id}"
                            self.user_assignments[key] = assignment
            
            # Load experiment events
            events_file = os.path.join(self.data_dir, "experiment_events.jsonl")
            if os.path.exists(events_file):
                with open(events_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            event_data = json.loads(line.strip())
                            event = ExperimentEvent(**event_data)
                            self.experiment_events.append(event)
            
            self.logger.info(f"Loaded {len(self.experiments)} experiments from storage")
            
        except Exception as e:
            self.logger.error(f"Failed to load experiments: {e}")

# Factory function
def create_ab_testing_framework(db_manager=None, analytics_collector=None) -> ABTestingFramework:
    """Create A/B testing framework with dependencies"""
    return ABTestingFramework(db_manager, analytics_collector)

# Helper functions for creating common experiments
async def create_plugin_recommendation_experiment(
    framework: ABTestingFramework,
    name: str,
    control_algorithm: str,
    treatment_algorithm: str,
    target_users: Dict[str, Any] = None
) -> str:
    """Create a plugin recommendation A/B test"""
    
    experiment_id = f"plugin_rec_{int(time.time())}"
    
    variants = [
        ExperimentVariant(
            variant_id="control",
            name="Current Algorithm",
            variant_type=VariantType.CONTROL,
            traffic_allocation=0.5,
            configuration={"algorithm": control_algorithm}
        ),
        ExperimentVariant(
            variant_id="treatment",
            name="New Algorithm",
            variant_type=VariantType.TREATMENT,
            traffic_allocation=0.5,
            configuration={"algorithm": treatment_algorithm}
        )
    ]
    
    metrics = [
        ExperimentMetric(
            metric_id="plugin_download_rate",
            metric_type=MetricType.CONVERSION_RATE,
            name="Plugin Download Rate",
            description="Percentage of users who download recommended plugins",
            is_primary=True
        ),
        ExperimentMetric(
            metric_id="recommendation_ctr",
            metric_type=MetricType.CLICK_THROUGH_RATE,
            name="Recommendation Click-Through Rate",
            description="CTR on plugin recommendations"
        )
    ]
    
    experiment = Experiment(
        experiment_id=experiment_id,
        name=name,
        description=f"Testing {treatment_algorithm} vs {control_algorithm} for plugin recommendations",
        status=ExperimentStatus.DRAFT,
        variants=variants,
        metrics=metrics,
        target_audience=target_users or {},
        start_date="",
        end_date=(datetime.now() + timedelta(days=30)).isoformat(),
        created_by="system",
        created_at=datetime.now().isoformat(),
        sample_size=1000
    )
    
    return await framework.create_experiment(experiment)