# A/B Testing Framework Documentation

## Overview

The AI Fitness Coach A/B Testing Framework provides a comprehensive solution for running controlled experiments to optimize user experience, plugin recommendations, and feature rollouts. This framework enables data-driven decision making through statistical analysis and real-time experiment monitoring.

## Architecture

### Core Components

1. **ABTestingFramework** - Main orchestrator for all A/B testing operations
2. **Experiment Management** - Create, start, pause, and analyze experiments
3. **User Assignment** - Consistent variant assignment using hashing
4. **Event Tracking** - Real-time user behavior and conversion tracking
5. **Statistical Analysis** - Automated significance testing and confidence intervals
6. **API Integration** - RESTful endpoints for frontend/mobile integration

### Data Models

#### Experiment
```python
@dataclass
class Experiment:
    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus  # DRAFT, ACTIVE, PAUSED, COMPLETED, ARCHIVED
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
```

#### ExperimentVariant
```python
@dataclass
class ExperimentVariant:
    variant_id: str
    name: str
    variant_type: VariantType  # CONTROL, TREATMENT
    traffic_allocation: float  # 0.0-1.0
    configuration: Dict[str, Any]
    description: str = ""
```

#### ExperimentMetric
```python
@dataclass
class ExperimentMetric:
    metric_id: str
    metric_type: MetricType  # CONVERSION_RATE, CLICK_THROUGH_RATE, etc.
    name: str
    description: str
    target_value: float = None
    is_primary: bool = False
```

## Key Features

### 1. Plugin Recommendation Optimization
- Test different recommendation algorithms
- Compare collaborative filtering vs. content-based approaches
- Measure plugin download conversion rates
- A/B test recommendation UI layouts

### 2. User Segmentation and Targeting
- Target specific user segments for experiments
- Support for demographic and behavioral targeting
- Gradual rollout capabilities
- Geographic and device-based targeting

### 3. Statistical Analysis
- Automated significance testing
- Confidence interval calculations
- Effect size measurements
- Bayesian statistical methods (planned)

### 4. Feature Flag Integration
- Dynamic feature toggles based on experiment variants
- Progressive feature rollouts
- Emergency rollback capabilities
- Environment-specific configurations

### 5. Real-time Monitoring
- Live experiment metrics dashboard
- Performance impact monitoring
- Error rate tracking during experiments
- Automated alerting for anomalies

## Usage Examples

### 1. Creating a Plugin Recommendation Experiment

```python
from core.ab_testing import create_plugin_recommendation_experiment

# Create experiment
experiment_id = await create_plugin_recommendation_experiment(
    framework=ab_framework,
    name="Algorithm Optimization Test",
    control_algorithm="popularity_based",
    treatment_algorithm="ai_personalized",
    target_users={"segment": "active_users", "min_workouts": 5}
)

# Start experiment
await ab_framework.start_experiment(experiment_id)
```

### 2. User Assignment and Feature Flags

```python
# Assign user to experiment
user_id = "user_12345"
variant_id = await ab_framework.assign_user_to_experiment(user_id, experiment_id)

# Get feature configuration
active_experiments = await ab_framework.get_active_experiments_for_user(user_id)
for exp in active_experiments:
    config = exp["configuration"]
    algorithm = config.get("algorithm", "default")
    
    # Use algorithm for recommendations
    recommendations = get_recommendations(user_id, algorithm)
```

### 3. Event Tracking

```python
# Track user interactions
await ab_framework.track_experiment_event(
    user_id=user_id,
    experiment_id=experiment_id,
    metric_id="plugin_download_rate",
    event_type="plugin_download",
    event_value=1.0,
    metadata={"plugin_id": "tennis_pro", "price": 9.99}
)

# Track click-through events
await ab_framework.track_experiment_event(
    user_id=user_id,
    experiment_id=experiment_id,
    metric_id="recommendation_ctr",
    event_type="recommendation_click",
    event_value=1.0,
    metadata={"position": 1, "plugin_id": "golf_swing"}
)
```

### 4. Results Analysis

```python
# Get experiment results
results = await ab_framework.get_experiment_results(experiment_id)

print(f"Experiment: {results.experiment_id}")
for variant_id, metrics in results.variant_results.items():
    conversion_rate = metrics["plugin_download_rate"]["value"] * 100
    sample_size = results.sample_sizes[variant_id]
    print(f"{variant_id}: {conversion_rate:.2f}% conversion ({sample_size} users)")

# Check statistical significance
for variant_id, is_significant in results.statistical_significance.items():
    status = "✅ Significant" if is_significant else "❌ Not Significant"
    print(f"{variant_id}: {status}")

# View recommendations
for recommendation in results.recommendations:
    print(f"💡 {recommendation}")
```

## API Endpoints

### Admin Endpoints

- `POST /api/ab-testing/experiments` - Create new experiment
- `POST /api/ab-testing/experiments/{id}/start` - Start experiment
- `GET /api/ab-testing/experiments` - List all experiments
- `GET /api/ab-testing/experiments/{id}/results` - Get experiment results

### User-Facing Endpoints

- `GET /api/ab-testing/users/{user_id}/experiments` - Get user's active experiments
- `POST /api/ab-testing/users/{user_id}/experiments/{id}/assign` - Assign user to experiment
- `POST /api/ab-testing/users/{user_id}/experiments/{id}/events` - Track user events
- `GET /api/ab-testing/users/{user_id}/features/{feature_name}` - Get feature flag value

### Plugin Recommendation Endpoints

- `POST /api/ab-testing/experiments/plugin-recommendation` - Create plugin rec experiment
- `GET /api/ab-testing/users/{user_id}/plugin-recommendations` - Get recommendations

## Configuration

### Environment Variables

```bash
# A/B Testing Configuration
AB_TESTING_DATA_DIR=data/ab_testing
AB_TESTING_DEFAULT_CONFIDENCE=0.95
AB_TESTING_MIN_EFFECT_SIZE=0.05
AB_TESTING_AUTO_STOP_ENABLED=true
AB_TESTING_MAX_EXPERIMENT_DURATION=90  # days
```

### Experiment Configuration

```json
{
  "experiment_id": "plugin_rec_001",
  "name": "Plugin Recommendation Algorithm Test",
  "description": "Testing AI-powered vs popularity-based recommendations",
  "variants": [
    {
      "variant_id": "control",
      "name": "Popularity Based",
      "variant_type": "control",
      "traffic_allocation": 0.5,
      "configuration": {
        "algorithm": "popularity_based",
        "max_recommendations": 5,
        "include_trending": true
      }
    },
    {
      "variant_id": "treatment",
      "name": "AI Personalized",
      "variant_type": "treatment",
      "traffic_allocation": 0.5,
      "configuration": {
        "algorithm": "ai_personalized",
        "max_recommendations": 5,
        "personalization_weight": 0.8
      }
    }
  ],
  "metrics": [
    {
      "metric_id": "download_rate",
      "metric_type": "conversion_rate",
      "name": "Plugin Download Rate",
      "description": "Percentage of users who download recommended plugins",
      "is_primary": true
    },
    {
      "metric_id": "click_rate",
      "metric_type": "click_through_rate",
      "name": "Recommendation CTR",
      "description": "Click-through rate on plugin recommendations"
    }
  ],
  "target_audience": {
    "user_segments": ["active_users"],
    "min_workouts": 5,
    "platforms": ["ios", "android", "web"]
  }
}
```

## Best Practices

### 1. Experiment Design

- **Clear Hypothesis**: Define what you're testing and expected outcomes
- **Single Variable**: Test one change at a time for clear attribution
- **Sufficient Sample Size**: Ensure statistical power for meaningful results
- **Control Group**: Always include a proper control variant
- **Duration Planning**: Run experiments long enough to capture user behavior patterns

### 2. Metrics Selection

- **Primary Metric**: Choose one key metric for decision making
- **Secondary Metrics**: Track additional metrics for insights
- **Leading Indicators**: Use early signals to predict longer-term outcomes
- **Guardrail Metrics**: Monitor for negative impacts on key business metrics

### 3. Statistical Considerations

- **Multiple Testing**: Account for multiple comparisons when testing multiple metrics
- **Early Stopping**: Use proper statistical methods for early experiment termination
- **Practical Significance**: Consider both statistical and practical significance
- **Confidence Intervals**: Report confidence intervals along with point estimates

### 4. Implementation Guidelines

- **Consistent Assignment**: Ensure users get consistent experience across sessions
- **Randomization Quality**: Use proper randomization techniques
- **Instrumentation**: Implement comprehensive event tracking
- **Error Handling**: Gracefully handle assignment and tracking failures

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Assignment Rate**: Percentage of eligible users assigned to experiments
2. **Event Tracking Rate**: Successful event capture rate
3. **Experiment Performance**: Real-time metric calculations
4. **System Performance**: Impact on application performance
5. **Error Rates**: Failed assignments and tracking errors

### Alerts Configuration

```python
# Performance alerts
ab_framework.alert_thresholds = {
    "assignment_failure_rate": 5.0,  # percentage
    "event_tracking_failure_rate": 2.0,  # percentage
    "response_time_degradation": 20.0,  # percentage increase
    "significant_result_achieved": True  # alert when significance reached
}
```

## Integration Examples

### 1. Plugin Store Integration

```python
class PluginRecommendationService:
    def __init__(self, ab_framework):
        self.ab_framework = ab_framework
    
    async def get_recommendations(self, user_id: str) -> List[Dict]:
        # Check for active experiments
        experiments = await self.ab_framework.get_active_experiments_for_user(user_id)
        
        # Find recommendation experiment
        rec_experiment = next(
            (exp for exp in experiments if "algorithm" in exp["configuration"]),
            None
        )
        
        if rec_experiment:
            algorithm = rec_experiment["configuration"]["algorithm"]
            recommendations = await self._get_recommendations_with_algorithm(user_id, algorithm)
            
            # Track recommendation display
            await self.ab_framework.track_experiment_event(
                user_id=user_id,
                experiment_id=rec_experiment["experiment_id"],
                metric_id="recommendation_display",
                event_type="recommendations_shown",
                event_value=len(recommendations)
            )
            
            return recommendations
        else:
            # Default recommendations
            return await self._get_default_recommendations(user_id)
    
    async def track_plugin_download(self, user_id: str, plugin_id: str):
        # Track conversion for all active experiments
        experiments = await self.ab_framework.get_active_experiments_for_user(user_id)
        
        for exp in experiments:
            await self.ab_framework.track_experiment_event(
                user_id=user_id,
                experiment_id=exp["experiment_id"],
                metric_id="plugin_download_rate",
                event_type="plugin_download",
                event_value=1.0,
                metadata={"plugin_id": plugin_id}
            )
```

### 2. Mobile App Integration

```swift
// iOS Swift integration example
class ABTestingManager {
    func getRecommendations(for userId: String) async -> [PluginRecommendation] {
        // Get user's active experiments
        let experiments = await APIClient.shared.getActiveExperiments(userId: userId)
        
        // Check for recommendation experiment
        if let recExp = experiments.first(where: { $0.configuration["algorithm"] != nil }) {
            let algorithm = recExp.configuration["algorithm"] as! String
            let recommendations = await getRecommendations(userId: userId, algorithm: algorithm)
            
            // Track display event
            await APIClient.shared.trackEvent(
                userId: userId,
                experimentId: recExp.experimentId,
                metricId: "recommendation_display",
                eventType: "recommendations_shown",
                eventValue: Double(recommendations.count)
            )
            
            return recommendations
        }
        
        return await getDefaultRecommendations(userId: userId)
    }
}
```

## Testing

The A/B testing framework includes comprehensive unit tests covering:

- Experiment creation and validation
- User assignment consistency
- Event tracking reliability
- Statistical calculations
- API endpoint functionality
- Data persistence

Run tests with:
```bash
python -m pytest tests/test_ab_testing.py -v
```

## Demo

Try the interactive demo to explore the framework:

```bash
cd ai_fitness_coach_lite
python demos/ab_testing_demo.py
```

The demo includes:
- Automated experiment simulation
- Interactive experiment management
- Real-time results analysis
- Feature flag demonstrations
- Multi-experiment scenarios

## Roadmap

### Planned Features

1. **Advanced Statistical Methods**
   - Bayesian A/B testing
   - Multi-armed bandit algorithms
   - Sequential testing procedures

2. **Enhanced Targeting**
   - Machine learning-based user segmentation
   - Dynamic audience optimization
   - Contextual bandit recommendations

3. **Integration Enhancements**
   - Slack/Discord notifications
   - Grafana dashboard integration
   - Automated experiment scheduling

4. **Performance Optimizations**
   - Redis caching for assignments
   - Batch event processing
   - Streaming analytics integration

## Support

For questions or issues:
- Check the test files for usage examples
- Review the demo script for implementation patterns
- Consult the API documentation for endpoint details

---

**AI Fitness Coach A/B Testing Framework**  
Version 1.0.0 - Production Ready  
© 2024 AI Fitness Coach Team