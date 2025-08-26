"""
A/B Testing Framework Demo

Interactive demonstration of the A/B testing framework featuring:
- Plugin recommendation experiments
- User segmentation and targeting
- Real-time results analysis
- Statistical significance testing
- Feature flag integration
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from core.ab_testing import (
    ABTestingFramework,
    Experiment,
    ExperimentVariant,
    ExperimentMetric,
    ExperimentStatus,
    VariantType,
    MetricType,
    create_ab_testing_framework,
    create_plugin_recommendation_experiment
)


class ABTestingDemo:
    """Interactive A/B testing framework demonstration"""
    
    def __init__(self):
        self.framework = create_ab_testing_framework()
        self.demo_users = self._generate_demo_users()
        self.plugins = [
            "tennis_pro", "golf_swing", "basketball_skills",
            "yoga_flow", "strength_training", "cardio_blast",
            "running_coach", "swimming_technique", "cycling_optimizer"
        ]
    
    def _generate_demo_users(self) -> List[str]:
        """Generate demo user IDs"""
        return [f"demo_user_{i:03d}" for i in range(1, 201)]  # 200 demo users
    
    async def run_complete_demo(self):
        """Run complete A/B testing demonstration"""
        print("🧪 AI Fitness Coach - A/B Testing Framework Demo")
        print("=" * 60)
        
        # Step 1: Create plugin recommendation experiment
        print("\n📊 Step 1: Creating Plugin Recommendation Experiment")
        experiment_id = await self._create_recommendation_experiment()
        
        # Step 2: Simulate user interactions
        print("\n👥 Step 2: Simulating User Interactions")
        await self._simulate_user_interactions(experiment_id)
        
        # Step 3: Analyze results
        print("\n📈 Step 3: Analyzing Experiment Results")
        await self._analyze_experiment_results(experiment_id)
        
        # Step 4: Feature flag demonstration
        print("\n🚩 Step 4: Feature Flag Integration Demo")
        await self._demonstrate_feature_flags(experiment_id)
        
        # Step 5: Multiple experiments
        print("\n🔬 Step 5: Multiple Experiments Demo")
        await self._demonstrate_multiple_experiments()
        
        print("\n✅ Demo Complete!")
        print("🎯 The A/B testing framework successfully demonstrated:")
        print("   • Plugin recommendation optimization")
        print("   • User segmentation and targeting")
        print("   • Real-time statistical analysis")
        print("   • Feature flag integration")
        print("   • Multi-experiment management")
    
    async def _create_recommendation_experiment(self) -> str:
        """Create plugin recommendation experiment"""
        print("   Creating experiment: 'Plugin Recommendation Algorithm Test'")
        
        experiment_id = await create_plugin_recommendation_experiment(
            framework=self.framework,
            name="Plugin Recommendation Algorithm Test",
            control_algorithm="popularity_based",
            treatment_algorithm="ai_personalized",
            target_users={"segment": "active_users", "min_workouts": 5}
        )
        
        print(f"   ✅ Experiment created: {experiment_id}")
        
        # Start the experiment
        success = await self.framework.start_experiment(experiment_id)
        if success:
            print("   ✅ Experiment started successfully")
        else:
            print("   ❌ Failed to start experiment")
        
        return experiment_id
    
    async def _simulate_user_interactions(self, experiment_id: str):
        """Simulate realistic user interactions"""
        print("   Assigning users to experiment variants...")
        
        assignments = {"control": 0, "treatment": 0}
        conversions = {"control": 0, "treatment": 0}
        clicks = {"control": 0, "treatment": 0}
        
        for i, user_id in enumerate(self.demo_users):
            # Assign user to experiment
            variant_id = await self.framework.assign_user_to_experiment(user_id, experiment_id)
            
            if variant_id:
                assignments[variant_id] += 1
                
                # Simulate user behavior based on variant
                await self._simulate_user_behavior(user_id, experiment_id, variant_id, conversions, clicks)
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"   Processed {i + 1}/{len(self.demo_users)} users...")
        
        print(f"   📊 Assignment Results:")
        print(f"      Control: {assignments['control']} users")
        print(f"      Treatment: {assignments['treatment']} users")
        print(f"   📈 Conversion Results:")
        print(f"      Control: {conversions['control']} conversions")
        print(f"      Treatment: {conversions['treatment']} conversions")
        print(f"   👆 Click Results:")
        print(f"      Control: {clicks['control']} clicks")
        print(f"      Treatment: {clicks['treatment']} clicks")
    
    async def _simulate_user_behavior(self, user_id: str, experiment_id: str, variant_id: str,
                                    conversions: Dict, clicks: Dict):
        """Simulate realistic user behavior patterns"""
        
        # Different behavior based on variant
        if variant_id == "control":
            # Popularity-based recommendations (lower engagement)
            click_probability = 0.15
            conversion_probability = 0.08
        else:
            # AI-personalized recommendations (higher engagement)
            click_probability = 0.25
            conversion_probability = 0.15
        
        # Simulate click behavior
        if random.random() < click_probability:
            clicks[variant_id] += 1
            
            # Track click event
            await self.framework.track_experiment_event(
                user_id=user_id,
                experiment_id=experiment_id,
                metric_id="recommendation_ctr",
                event_type="recommendation_click",
                event_value=1.0,
                metadata={
                    "clicked_plugin": random.choice(self.plugins),
                    "position": random.randint(1, 5)
                }
            )
            
            # If user clicked, they might convert
            if random.random() < conversion_probability:
                conversions[variant_id] += 1
                
                # Track conversion event
                await self.framework.track_experiment_event(
                    user_id=user_id,
                    experiment_id=experiment_id,
                    metric_id="plugin_download_rate",
                    event_type="plugin_download",
                    event_value=1.0,
                    metadata={
                        "downloaded_plugin": random.choice(self.plugins),
                        "time_to_convert": random.randint(5, 300)  # seconds
                    }
                )
    
    async def _analyze_experiment_results(self, experiment_id: str):
        """Analyze and display experiment results"""
        print("   Calculating statistical results...")
        
        results = await self.framework.get_experiment_results(experiment_id)
        
        if results:
            print(f"   📊 Experiment Results for {experiment_id}:")
            print(f"   Generated at: {results.generated_at}")
            
            # Display variant results
            for variant_id, metrics in results.variant_results.items():
                print(f"\n   🎯 Variant: {variant_id.upper()}")
                print(f"      Sample Size: {results.sample_sizes.get(variant_id, 0)} users")
                
                for metric_id, metric_data in metrics.items():
                    if metric_id == "plugin_download_rate":
                        conversion_rate = metric_data.get("value", 0) * 100
                        print(f"      Plugin Download Rate: {conversion_rate:.2f}%")
                        print(f"      Total Conversions: {metric_data.get('count', 0)}")
                    elif metric_id == "recommendation_ctr":
                        ctr = metric_data.get("value", 0) * 100
                        print(f"      Click-Through Rate: {ctr:.2f}%")
                        print(f"      Total Clicks: {metric_data.get('clicks', 0)}")
            
            # Display statistical significance
            print(f"\n   📈 Statistical Significance:")
            for variant_id, is_significant in results.statistical_significance.items():
                status = "✅ Significant" if is_significant else "❌ Not Significant"
                print(f"      {variant_id}: {status}")
            
            # Display confidence intervals
            print(f"\n   📊 Confidence Intervals (Primary Metric):")
            for variant_id, (lower, upper) in results.confidence_intervals.items():
                print(f"      {variant_id}: [{lower:.3f}, {upper:.3f}]")
            
            # Display recommendations
            print(f"\n   💡 Recommendations:")
            for i, recommendation in enumerate(results.recommendations, 1):
                print(f"      {i}. {recommendation}")
        
        else:
            print("   ❌ Failed to generate results")
    
    async def _demonstrate_feature_flags(self, experiment_id: str):
        """Demonstrate feature flag integration"""
        print("   Demonstrating feature flags based on experiment variants...")
        
        # Test feature flags for different users
        test_users = ["demo_user_001", "demo_user_050", "demo_user_100"]
        
        for user_id in test_users:
            active_experiments = await self.framework.get_active_experiments_for_user(user_id)
            
            print(f"\n   👤 User: {user_id}")
            
            if active_experiments:
                exp = active_experiments[0]
                config = exp["configuration"]
                algorithm = config.get("algorithm", "default")
                
                # Simulate feature flags based on algorithm
                features = self._get_features_for_algorithm(algorithm)
                
                print(f"      Experiment: {exp['experiment_name']}")
                print(f"      Variant: {exp['variant_name']}")
                print(f"      Algorithm: {algorithm}")
                print(f"      Feature Flags:")
                for feature, enabled in features.items():
                    status = "✅ ON" if enabled else "❌ OFF"
                    print(f"         {feature}: {status}")
            else:
                print("      No active experiments")
    
    def _get_features_for_algorithm(self, algorithm: str) -> Dict[str, bool]:
        """Get feature flags based on recommendation algorithm"""
        if algorithm == "ai_personalized":
            return {
                "advanced_recommendations": True,
                "personalized_ui": True,
                "smart_notifications": True,
                "adaptive_content": True
            }
        else:
            return {
                "advanced_recommendations": False,
                "personalized_ui": False,
                "smart_notifications": False,
                "adaptive_content": False
            }
    
    async def _demonstrate_multiple_experiments(self):
        """Demonstrate running multiple experiments simultaneously"""
        print("   Creating additional experiments for multi-testing...")
        
        # Create UI/UX experiment
        ui_experiment = await self._create_ui_experiment()
        
        # Create pricing experiment
        pricing_experiment = await self._create_pricing_experiment()
        
        # Start both experiments
        await self.framework.start_experiment(ui_experiment)
        await self.framework.start_experiment(pricing_experiment)
        
        print("   Simulating concurrent experiment participation...")
        
        # Simulate some users in multiple experiments
        multi_exp_users = self.demo_users[:50]  # First 50 users
        
        for user_id in multi_exp_users:
            # Assign to UI experiment
            ui_variant = await self.framework.assign_user_to_experiment(user_id, ui_experiment)
            
            # Assign to pricing experiment
            pricing_variant = await self.framework.assign_user_to_experiment(user_id, pricing_experiment)
            
            # Simulate interactions
            if random.random() < 0.3:  # 30% interaction rate
                # UI experiment event
                await self.framework.track_experiment_event(
                    user_id=user_id,
                    experiment_id=ui_experiment,
                    metric_id="ui_engagement",
                    event_type="button_click",
                    event_value=1.0
                )
                
                # Pricing experiment event
                if random.random() < 0.1:  # 10% purchase rate
                    await self.framework.track_experiment_event(
                        user_id=user_id,
                        experiment_id=pricing_experiment,
                        metric_id="purchase_rate",
                        event_type="subscription_purchase",
                        event_value=random.choice([9.99, 19.99, 39.99])
                    )
        
        # Show experiment summary
        print(f"\n   📋 Multi-Experiment Summary:")
        print(f"      Total Active Experiments: {len([e for e in self.framework.experiments.values() if e.status == ExperimentStatus.ACTIVE])}")
        print(f"      Total User Assignments: {len(self.framework.user_assignments)}")
        print(f"      Total Events Tracked: {len(self.framework.experiment_events)}")
    
    async def _create_ui_experiment(self) -> str:
        """Create UI/UX experiment"""
        variants = [
            ExperimentVariant(
                variant_id="ui_control",
                name="Current UI",
                variant_type=VariantType.CONTROL,
                traffic_allocation=0.5,
                configuration={"ui_theme": "classic", "button_style": "default"}
            ),
            ExperimentVariant(
                variant_id="ui_treatment",
                name="New UI",
                variant_type=VariantType.TREATMENT,
                traffic_allocation=0.5,
                configuration={"ui_theme": "modern", "button_style": "floating"}
            )
        ]
        
        metrics = [
            ExperimentMetric(
                metric_id="ui_engagement",
                metric_type=MetricType.CLICK_THROUGH_RATE,
                name="UI Engagement",
                description="User engagement with UI elements",
                is_primary=True
            )
        ]
        
        experiment = Experiment(
            experiment_id=f"ui_exp_{int(time.time())}",
            name="UI/UX Optimization Test",
            description="Testing new UI design for better user engagement",
            status=ExperimentStatus.DRAFT,
            variants=variants,
            metrics=metrics,
            target_audience={"platform": "mobile"},
            start_date="",
            end_date=(datetime.now() + timedelta(days=14)).isoformat(),
            created_by="ui_team",
            created_at=datetime.now().isoformat()
        )
        
        return await self.framework.create_experiment(experiment)
    
    async def _create_pricing_experiment(self) -> str:
        """Create pricing experiment"""
        variants = [
            ExperimentVariant(
                variant_id="price_control",
                name="Current Pricing",
                variant_type=VariantType.CONTROL,
                traffic_allocation=0.5,
                configuration={"premium_price": 19.99, "trial_days": 7}
            ),
            ExperimentVariant(
                variant_id="price_treatment",
                name="New Pricing",
                variant_type=VariantType.TREATMENT,
                traffic_allocation=0.5,
                configuration={"premium_price": 14.99, "trial_days": 14}
            )
        ]
        
        metrics = [
            ExperimentMetric(
                metric_id="purchase_rate",
                metric_type=MetricType.CONVERSION_RATE,
                name="Purchase Rate",
                description="Subscription purchase conversion rate",
                is_primary=True
            )
        ]
        
        experiment = Experiment(
            experiment_id=f"pricing_exp_{int(time.time())}",
            name="Pricing Strategy Test",
            description="Testing new pricing model for premium subscriptions",
            status=ExperimentStatus.DRAFT,
            variants=variants,
            metrics=metrics,
            target_audience={"user_type": "trial_users"},
            start_date="",
            end_date=(datetime.now() + timedelta(days=30)).isoformat(),
            created_by="product_team",
            created_at=datetime.now().isoformat()
        )
        
        return await self.framework.create_experiment(experiment)
    
    async def run_interactive_demo(self):
        """Run interactive demo with user choices"""
        print("🧪 Interactive A/B Testing Demo")
        print("=" * 40)
        
        while True:
            print("\nChoose an option:")
            print("1. Create new experiment")
            print("2. View experiment results")
            print("3. Simulate user interactions")
            print("4. Test feature flags")
            print("5. View all experiments")
            print("6. Exit")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                await self._interactive_create_experiment()
            elif choice == "2":
                await self._interactive_view_results()
            elif choice == "3":
                await self._interactive_simulate_users()
            elif choice == "4":
                await self._interactive_feature_flags()
            elif choice == "5":
                self._view_all_experiments()
            elif choice == "6":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    async def _interactive_create_experiment(self):
        """Interactive experiment creation"""
        print("\n📊 Creating New Experiment")
        name = input("Experiment name: ")
        description = input("Description: ")
        
        # Quick setup for demo
        experiment_id = await create_plugin_recommendation_experiment(
            framework=self.framework,
            name=name,
            control_algorithm="popularity_based",
            treatment_algorithm="ai_personalized"
        )
        
        print(f"✅ Experiment created: {experiment_id}")
        
        start = input("Start experiment now? (y/n): ").strip().lower()
        if start == "y":
            success = await self.framework.start_experiment(experiment_id)
            if success:
                print("✅ Experiment started!")
            else:
                print("❌ Failed to start experiment")
    
    async def _interactive_view_results(self):
        """Interactive results viewing"""
        experiments = [exp for exp in self.framework.experiments.values() 
                      if exp.status == ExperimentStatus.ACTIVE]
        
        if not experiments:
            print("❌ No active experiments found")
            return
        
        print("\n📈 Active Experiments:")
        for i, exp in enumerate(experiments, 1):
            print(f"{i}. {exp.name} ({exp.experiment_id})")
        
        try:
            choice = int(input("\nSelect experiment (number): ")) - 1
            if 0 <= choice < len(experiments):
                selected_exp = experiments[choice]
                await self._analyze_experiment_results(selected_exp.experiment_id)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Please enter a valid number")
    
    async def _interactive_simulate_users(self):
        """Interactive user simulation"""
        experiments = [exp for exp in self.framework.experiments.values() 
                      if exp.status == ExperimentStatus.ACTIVE]
        
        if not experiments:
            print("❌ No active experiments found")
            return
        
        print("\n👥 Simulating Users")
        print(f"Available experiments: {len(experiments)}")
        
        try:
            num_users = int(input("Number of users to simulate (1-100): "))
            if 1 <= num_users <= 100:
                demo_users = [f"interactive_user_{i}" for i in range(num_users)]
                
                # Use first active experiment
                experiment_id = experiments[0].experiment_id
                print(f"Using experiment: {experiments[0].name}")
                
                conversions = {"control": 0, "treatment": 0}
                clicks = {"control": 0, "treatment": 0}
                
                for user_id in demo_users:
                    variant_id = await self.framework.assign_user_to_experiment(user_id, experiment_id)
                    if variant_id:
                        await self._simulate_user_behavior(user_id, experiment_id, variant_id, conversions, clicks)
                
                print(f"✅ Simulated {num_users} users")
                print(f"Conversions - Control: {conversions.get('control', 0)}, Treatment: {conversions.get('treatment', 0)}")
            else:
                print("❌ Please enter a number between 1 and 100")
        except ValueError:
            print("❌ Please enter a valid number")
    
    async def _interactive_feature_flags(self):
        """Interactive feature flag testing"""
        user_id = input("\nEnter user ID to test: ").strip()
        if not user_id:
            user_id = "test_user_001"
        
        active_experiments = await self.framework.get_active_experiments_for_user(user_id)
        
        print(f"\n🚩 Feature Flags for {user_id}:")
        
        if active_experiments:
            for exp in active_experiments:
                print(f"\nExperiment: {exp['experiment_name']}")
                print(f"Variant: {exp['variant_name']}")
                config = exp['configuration']
                algorithm = config.get('algorithm', 'default')
                features = self._get_features_for_algorithm(algorithm)
                
                for feature, enabled in features.items():
                    status = "✅ ON" if enabled else "❌ OFF"
                    print(f"  {feature}: {status}")
        else:
            print("No active experiments for this user")
    
    def _view_all_experiments(self):
        """View all experiments"""
        print("\n📋 All Experiments:")
        
        if not self.framework.experiments:
            print("No experiments found")
            return
        
        for exp in self.framework.experiments.values():
            print(f"\n🧪 {exp.name}")
            print(f"   ID: {exp.experiment_id}")
            print(f"   Status: {exp.status.value}")
            print(f"   Variants: {len(exp.variants)}")
            print(f"   Metrics: {len(exp.metrics)}")
            print(f"   Created: {exp.created_at}")


async def main():
    """Main demo function"""
    demo = ABTestingDemo()
    
    print("Choose demo mode:")
    print("1. Complete automated demo")
    print("2. Interactive demo")
    
    choice = input("\nEnter your choice (1-2): ").strip()
    
    if choice == "1":
        await demo.run_complete_demo()
    elif choice == "2":
        await demo.run_interactive_demo()
    else:
        print("Running automated demo...")
        await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())