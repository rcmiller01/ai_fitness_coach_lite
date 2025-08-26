"""
Unit Tests for A/B Testing Framework

Comprehensive tests covering:
- Experiment creation and management
- User assignment and variant serving
- Event tracking and metrics
- Statistical analysis
- API endpoints
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core.ab_testing import (
    ABTestingFramework,
    Experiment,
    ExperimentVariant,
    ExperimentMetric,
    ExperimentStatus,
    VariantType,
    MetricType,
    UserAssignment,
    ExperimentEvent,
    ExperimentResults,
    create_ab_testing_framework,
    create_plugin_recommendation_experiment
)


class TestABTestingFramework:
    """Test cases for AB Testing Framework"""
    
    @pytest.fixture
    def framework(self):
        """Create test framework instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework = ABTestingFramework()
            framework.data_dir = temp_dir
            yield framework
    
    @pytest.fixture
    def sample_experiment(self):
        """Create sample experiment for testing"""
        variants = [
            ExperimentVariant(
                variant_id="control",
                name="Control",
                variant_type=VariantType.CONTROL,
                traffic_allocation=0.5,
                configuration={"algorithm": "default"}
            ),
            ExperimentVariant(
                variant_id="treatment",
                name="Treatment",
                variant_type=VariantType.TREATMENT,
                traffic_allocation=0.5,
                configuration={"algorithm": "new_algorithm"}
            )
        ]
        
        metrics = [
            ExperimentMetric(
                metric_id="conversion_rate",
                metric_type=MetricType.CONVERSION_RATE,
                name="Conversion Rate",
                description="Plugin download conversion rate",
                is_primary=True
            )
        ]
        
        return Experiment(
            experiment_id="test_exp_001",
            name="Test Experiment",
            description="Test experiment for unit tests",
            status=ExperimentStatus.DRAFT,
            variants=variants,
            metrics=metrics,
            target_audience={"all_users": True},
            start_date="",
            end_date=(datetime.now() + timedelta(days=30)).isoformat(),
            created_by="test_user",
            created_at=datetime.now().isoformat(),
            sample_size=1000
        )
    
    @pytest.mark.asyncio
    async def test_create_experiment(self, framework, sample_experiment):
        """Test experiment creation"""
        experiment_id = await framework.create_experiment(sample_experiment)
        
        assert experiment_id == sample_experiment.experiment_id
        assert experiment_id in framework.experiments
        
        stored_experiment = framework.experiments[experiment_id]
        assert stored_experiment.name == sample_experiment.name
        assert stored_experiment.status == ExperimentStatus.DRAFT
        assert len(stored_experiment.variants) == 2
        assert len(stored_experiment.metrics) == 1
    
    @pytest.mark.asyncio
    async def test_start_experiment(self, framework, sample_experiment):
        """Test starting an experiment"""
        # Create experiment first
        experiment_id = await framework.create_experiment(sample_experiment)
        
        # Start experiment
        success = await framework.start_experiment(experiment_id)
        
        assert success is True
        
        experiment = framework.experiments[experiment_id]
        assert experiment.status == ExperimentStatus.ACTIVE
        assert experiment.start_date != ""
    
    @pytest.mark.asyncio
    async def test_user_assignment(self, framework, sample_experiment):
        """Test user assignment to experiment variants"""
        # Create and start experiment
        experiment_id = await framework.create_experiment(sample_experiment)
        await framework.start_experiment(experiment_id)
        
        # Test user assignment
        user_id = "test_user_123"
        variant_id = await framework.assign_user_to_experiment(user_id, experiment_id)
        
        assert variant_id is not None
        assert variant_id in ["control", "treatment"]
        
        # Test consistency - same user should get same variant
        variant_id_2 = await framework.assign_user_to_experiment(user_id, experiment_id)
        assert variant_id == variant_id_2
        
        # Check assignment record
        assignment_key = f"{user_id}:{experiment_id}"
        assert assignment_key in framework.user_assignments
        
        assignment = framework.user_assignments[assignment_key]
        assert assignment.user_id == user_id
        assert assignment.experiment_id == experiment_id
        assert assignment.variant_id == variant_id
    
    @pytest.mark.asyncio
    async def test_event_tracking(self, framework, sample_experiment):
        """Test experiment event tracking"""
        # Setup experiment and user assignment
        experiment_id = await framework.create_experiment(sample_experiment)
        await framework.start_experiment(experiment_id)
        
        user_id = "test_user_123"
        variant_id = await framework.assign_user_to_experiment(user_id, experiment_id)
        
        # Track an event
        event_id = await framework.track_experiment_event(
            user_id=user_id,
            experiment_id=experiment_id,
            metric_id="conversion_rate",
            event_type="plugin_download",
            event_value=1.0,
            metadata={"plugin_id": "test_plugin"}
        )
        
        assert event_id != ""
        
        # Check event was stored
        events = [e for e in framework.experiment_events if e.event_id == event_id]
        assert len(events) == 1
        
        event = events[0]
        assert event.user_id == user_id
        assert event.experiment_id == experiment_id
        assert event.variant_id == variant_id
        assert event.metric_id == "conversion_rate"
        assert event.event_type == "plugin_download"
        assert event.event_value == 1.0
    
    @pytest.mark.asyncio
    async def test_experiment_results(self, framework, sample_experiment):
        """Test experiment results calculation"""
        # Setup experiment
        experiment_id = await framework.create_experiment(sample_experiment)
        await framework.start_experiment(experiment_id)
        
        # Create test data with multiple users
        users = ["user_1", "user_2", "user_3", "user_4"]
        
        for user_id in users:
            variant_id = await framework.assign_user_to_experiment(user_id, experiment_id)
            
            # Simulate conversion events (some users convert, some don't)
            if user_id in ["user_1", "user_3"]:  # 50% conversion rate
                await framework.track_experiment_event(
                    user_id=user_id,
                    experiment_id=experiment_id,
                    metric_id="conversion_rate",
                    event_type="conversion",
                    event_value=1.0
                )
        
        # Get results
        results = await framework.get_experiment_results(experiment_id)
        
        assert results is not None
        assert results.experiment_id == experiment_id
        assert "control" in results.variant_results
        assert "treatment" in results.variant_results
        assert len(results.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_active_experiments_for_user(self, framework, sample_experiment):
        """Test getting active experiments for a user"""
        # Setup experiment
        experiment_id = await framework.create_experiment(sample_experiment)
        await framework.start_experiment(experiment_id)
        
        user_id = "test_user_123"
        await framework.assign_user_to_experiment(user_id, experiment_id)
        
        # Get active experiments
        active_experiments = await framework.get_active_experiments_for_user(user_id)
        
        assert len(active_experiments) == 1
        
        exp = active_experiments[0]
        assert exp["experiment_id"] == experiment_id
        assert exp["experiment_name"] == sample_experiment.name
        assert "variant_id" in exp
        assert "configuration" in exp
    
    def test_variant_assignment_consistency(self, framework):
        """Test that variant assignment is consistent for same user"""
        experiment = Experiment(
            experiment_id="consistency_test",
            name="Consistency Test",
            description="Test variant assignment consistency",
            status=ExperimentStatus.ACTIVE,
            variants=[
                ExperimentVariant(
                    variant_id="control",
                    name="Control",
                    variant_type=VariantType.CONTROL,
                    traffic_allocation=0.5,
                    configuration={}
                ),
                ExperimentVariant(
                    variant_id="treatment",
                    name="Treatment",
                    variant_type=VariantType.TREATMENT,
                    traffic_allocation=0.5,
                    configuration={}
                )
            ],
            metrics=[],
            target_audience={},
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(days=30)).isoformat(),
            created_by="test",
            created_at=datetime.now().isoformat()
        )
        
        user_id = "consistent_user"
        
        # Multiple assignments should return same variant
        variant_1 = framework._assign_variant(user_id, experiment)
        variant_2 = framework._assign_variant(user_id, experiment)
        variant_3 = framework._assign_variant(user_id, experiment)
        
        assert variant_1 == variant_2 == variant_3
    
    def test_traffic_allocation_distribution(self, framework):
        """Test that traffic allocation works approximately correctly"""
        experiment = Experiment(
            experiment_id="traffic_test",
            name="Traffic Test",
            description="Test traffic allocation",
            status=ExperimentStatus.ACTIVE,
            variants=[
                ExperimentVariant(
                    variant_id="control",
                    name="Control",
                    variant_type=VariantType.CONTROL,
                    traffic_allocation=0.3,
                    configuration={}
                ),
                ExperimentVariant(
                    variant_id="treatment",
                    name="Treatment",
                    variant_type=VariantType.TREATMENT,
                    traffic_allocation=0.7,
                    configuration={}
                )
            ],
            metrics=[],
            target_audience={},
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(days=30)).isoformat(),
            created_by="test",
            created_at=datetime.now().isoformat()
        )
        
        # Simulate many users
        control_count = 0
        treatment_count = 0
        
        for i in range(1000):
            user_id = f"user_{i}"
            variant = framework._assign_variant(user_id, experiment)
            
            if variant == "control":
                control_count += 1
            else:
                treatment_count += 1
        
        # Check approximate distribution (allow 5% margin)
        control_ratio = control_count / 1000
        treatment_ratio = treatment_count / 1000
        
        assert 0.25 <= control_ratio <= 0.35  # Expected 30% ± 5%
        assert 0.65 <= treatment_ratio <= 0.75  # Expected 70% ± 5%
    
    def test_experiment_validation(self, framework):
        """Test experiment validation logic"""
        # Test experiment with no variants (this will fail at traffic allocation check first)
        with pytest.raises(ValueError, match="must sum to 1.0"):
            framework._validate_experiment(Experiment(
                experiment_id="invalid_1",
                name="Invalid",
                description="No variants",
                status=ExperimentStatus.DRAFT,
                variants=[],
                metrics=[],
                target_audience={},
                start_date="",
                end_date="",
                created_by="test",
                created_at=datetime.now().isoformat()
            ))
        
        # Test experiment with proper variants but invalid traffic allocation
        with pytest.raises(ValueError, match="must sum to 1.0"):
            Experiment(
                experiment_id="invalid_2",
                name="Invalid",
                description="Bad allocation",
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        variant_id="control",
                        name="Control",
                        variant_type=VariantType.CONTROL,
                        traffic_allocation=0.6,
                        configuration={}
                    ),
                    ExperimentVariant(
                        variant_id="treatment",
                        name="Treatment",
                        variant_type=VariantType.TREATMENT,
                        traffic_allocation=0.6,  # Total = 1.2, should fail
                        configuration={}
                    )
                ],
                metrics=[],
                target_audience={},
                start_date="",
                end_date="",
                created_by="test",
                created_at=datetime.now().isoformat()
            )


class TestPluginRecommendationExperiment:
    """Test plugin recommendation experiment helper"""
    
    @pytest.mark.asyncio
    async def test_create_plugin_recommendation_experiment(self):
        """Test creating plugin recommendation experiment"""
        framework = create_ab_testing_framework()
        
        experiment_id = await create_plugin_recommendation_experiment(
            framework=framework,
            name="Plugin Rec Test",
            control_algorithm="collaborative_filtering",
            treatment_algorithm="content_based",
            target_users={"segment": "premium_users"}
        )
        
        assert experiment_id.startswith("plugin_rec_")
        assert experiment_id in framework.experiments
        
        experiment = framework.experiments[experiment_id]
        assert experiment.name == "Plugin Rec Test"
        assert len(experiment.variants) == 2
        assert len(experiment.metrics) == 2
        
        # Check variant configurations
        control_variant = next(v for v in experiment.variants if v.variant_type == VariantType.CONTROL)
        treatment_variant = next(v for v in experiment.variants if v.variant_type == VariantType.TREATMENT)
        
        assert control_variant.configuration["algorithm"] == "collaborative_filtering"
        assert treatment_variant.configuration["algorithm"] == "content_based"


class TestABTestingStorage:
    """Test storage functionality"""
    
    @pytest.mark.asyncio
    async def test_experiment_persistence(self):
        """Test that experiments are saved and loaded correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create framework and experiment
            framework = ABTestingFramework()
            framework.data_dir = temp_dir
            
            experiment = Experiment(
                experiment_id="persist_test",
                name="Persistence Test",
                description="Test persistence",
                status=ExperimentStatus.DRAFT,
                variants=[
                    ExperimentVariant(
                        variant_id="control",
                        name="Control",
                        variant_type=VariantType.CONTROL,
                        traffic_allocation=0.5,
                        configuration={}
                    ),
                    ExperimentVariant(
                        variant_id="treatment",
                        name="Treatment",
                        variant_type=VariantType.TREATMENT,
                        traffic_allocation=0.5,
                        configuration={}
                    )
                ],
                metrics=[
                    ExperimentMetric(
                        metric_id="test_metric",
                        metric_type=MetricType.CONVERSION_RATE,
                        name="Test Metric",
                        description="Test metric",
                        is_primary=True
                    )
                ],
                target_audience={},
                start_date="",
                end_date="",
                created_by="test",
                created_at=datetime.now().isoformat()
            )
            
            await framework.create_experiment(experiment)
            
            # Create new framework instance and load data
            framework2 = ABTestingFramework()
            framework2.data_dir = temp_dir
            framework2._load_experiments()
            
            assert "persist_test" in framework2.experiments
            loaded_experiment = framework2.experiments["persist_test"]
            assert loaded_experiment.name == "Persistence Test"
            assert loaded_experiment.status == ExperimentStatus.DRAFT


@pytest.mark.asyncio
async def test_create_ab_testing_framework():
    """Test factory function"""
    framework = create_ab_testing_framework()
    
    assert isinstance(framework, ABTestingFramework)
    assert framework.experiments == {}
    assert framework.user_assignments == {}
    assert framework.experiment_events == []


if __name__ == "__main__":
    pytest.main([__file__])