"""
Plugin Marketplace Store Interface

Provides a comprehensive store interface for browsing, purchasing,
and managing fitness coaching plugins.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

class PluginCategory(Enum):
    """Plugin categories for organization"""
    SPORTS_ANALYSIS = "sports_analysis"
    EXERCISE_LIBRARY = "exercise_library"
    NUTRITION = "nutrition"
    RECOVERY = "recovery"
    INTEGRATION = "integration"
    PREMIUM_COACHING = "premium_coaching"

@dataclass
class PluginStoreItem:
    """Store item representation of a plugin"""
    plugin_id: str
    name: str
    short_description: str
    long_description: str
    version: str
    author: str
    category: PluginCategory
    price: float
    trial_days: int
    rating: float
    review_count: int
    download_count: int
    screenshots: List[str]
    features: List[str]
    requirements: List[str]
    compatibility: str
    release_date: str
    last_updated: str
    file_size_mb: float
    is_featured: bool
    discount_percent: float = 0.0
    
    @property
    def discounted_price(self) -> float:
        """Calculate discounted price"""
        if self.discount_percent > 0:
            return self.price * (1 - self.discount_percent / 100)
        return self.price
    
    @property
    def is_free(self) -> bool:
        """Check if plugin is free"""
        return self.price == 0.0

@dataclass
class Review:
    """Plugin review"""
    review_id: str
    plugin_id: str
    user_name: str
    rating: int  # 1-5 stars
    title: str
    comment: str
    date: str
    helpful_votes: int
    verified_purchase: bool

class PluginStore:
    """
    Plugin marketplace store
    """
    
    def __init__(self):
        self.store_items: Dict[str, PluginStoreItem] = {}
        self.reviews: Dict[str, List[Review]] = {}
        self.featured_plugins: List[str] = []
        self.categories: Dict[PluginCategory, List[str]] = {}
        
        self.load_store_data()
    
    def load_store_data(self):
        """Load store data with demo plugins"""
        
        # Golf Pro plugin
        golf_pro = PluginStoreItem(
            plugin_id="golf_pro",
            name="Golf Pro Swing Analyzer",
            short_description="Professional golf swing analysis with AI-powered coaching",
            long_description="""Transform your golf game with professional-level swing analysis. 
            
            Our Golf Pro Swing Analyzer uses advanced pose detection to provide detailed feedback on:
            • Swing plane analysis (steep/neutral/shallow detection)
            • Tempo optimization with 3:1 ratio coaching  
            • Weight transfer scoring for power generation
            • Real-time form corrections during practice
            • Personalized coaching tips based on your swing issues
            • Consistency tracking across multiple sessions
            
            Developed by professional golf instructors and used by touring pros. 
            Perfect for golfers of all skill levels looking to improve their game.""",
            version="1.0.0",
            author="AI Fitness Coach Team",
            category=PluginCategory.SPORTS_ANALYSIS,
            price=9.99,
            trial_days=7,
            rating=4.8,
            review_count=142,
            download_count=1205,
            screenshots=[
                "golf_swing_analysis.png",
                "tempo_meter.png", 
                "coaching_tips.png",
                "progress_tracking.png"
            ],
            features=[
                "Professional swing analysis",
                "Real-time tempo coaching",
                "Swing plane detection",
                "Weight transfer analysis",
                "Personalized tips database",
                "Progress tracking",
                "Voice coaching integration"
            ],
            requirements=["Camera access", "Pose estimation"],
            compatibility="iOS 14+, Android 8+, Windows 10+",
            release_date="2024-08-26",
            last_updated="2024-08-26",
            file_size_mb=15.2,
            is_featured=True,
            discount_percent=20.0  # Launch discount
        )
        
        self.store_items["golf_pro"] = golf_pro
        
        # Tennis Pro plugin (coming soon)
        tennis_pro = PluginStoreItem(
            plugin_id="tennis_pro",
            name="Tennis Pro Stroke Analyzer",
            short_description="Professional tennis stroke analysis and technique coaching",
            long_description="""Elevate your tennis game with professional stroke analysis.
            
            Features:
            • Forehand and backhand technique analysis
            • Serve biomechanics optimization
            • Footwork and positioning coaching
            • Match strategy insights
            • Professional drills library
            
            Coming Soon!""",
            version="1.0.0",
            author="AI Fitness Coach Team",
            category=PluginCategory.SPORTS_ANALYSIS,
            price=7.99,
            trial_days=7,
            rating=0.0,
            review_count=0,
            download_count=0,
            screenshots=["tennis_coming_soon.png"],
            features=[
                "Stroke analysis",
                "Serve coaching", 
                "Footwork training",
                "Match insights"
            ],
            requirements=["Camera access", "Pose estimation"],
            compatibility="iOS 14+, Android 8+, Windows 10+",
            release_date="2024-09-15",
            last_updated="2024-08-26",
            file_size_mb=12.8,
            is_featured=True
        )
        
        self.store_items["tennis_pro"] = tennis_pro
        
        # Organize by categories
        self.categories[PluginCategory.SPORTS_ANALYSIS] = [
            "golf_pro", "tennis_pro"
        ]
        
        self.featured_plugins = ["golf_pro", "tennis_pro"]
        
        # Load demo reviews for Golf Pro
        self.reviews["golf_pro"] = [
            Review(
                review_id="rev_001",
                plugin_id="golf_pro",
                user_name="Mike R.",
                rating=5,
                title="Game changer!",
                comment="Finally found something that actually helps my swing. The tempo analysis is spot on and the tips are exactly what my pro tells me. Worth every penny!",
                date="2024-08-20",
                helpful_votes=23,
                verified_purchase=True
            ),
            Review(
                review_id="rev_002",
                plugin_id="golf_pro",
                user_name="Sarah K.",
                rating=5,
                title="Professional quality",
                comment="As a teaching pro, I'm impressed with the accuracy of the swing analysis. I recommend this to all my students.",
                date="2024-08-18",
                helpful_votes=31,
                verified_purchase=True
            )
        ]
    
    def get_featured_plugins(self) -> List[PluginStoreItem]:
        """Get featured plugins for homepage"""
        return [self.store_items[plugin_id] for plugin_id in self.featured_plugins 
                if plugin_id in self.store_items]
    
    def get_plugins_by_category(self, category: PluginCategory) -> List[PluginStoreItem]:
        """Get plugins by category"""
        plugin_ids = self.categories.get(category, [])
        return [self.store_items[plugin_id] for plugin_id in plugin_ids 
                if plugin_id in self.store_items]
    
    def search_plugins(self, query: str) -> List[PluginStoreItem]:
        """Search plugins by name, description, or features"""
        query_lower = query.lower()
        results = []
        
        for plugin in self.store_items.values():
            if (query_lower in plugin.name.lower() or 
                query_lower in plugin.short_description.lower() or
                query_lower in plugin.long_description.lower() or
                any(query_lower in feature.lower() for feature in plugin.features)):
                results.append(plugin)
        
        return results
    
    def get_plugin_details(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin information"""
        if plugin_id not in self.store_items:
            return None
        
        plugin = self.store_items[plugin_id]
        reviews = self.reviews.get(plugin_id, [])
        
        return {
            "plugin": asdict(plugin),
            "reviews": [asdict(review) for review in reviews[:5]],  # Top 5 reviews
            "total_reviews": len(reviews),
            "rating_breakdown": self._get_rating_breakdown(reviews)
        }
    
    def _get_rating_breakdown(self, reviews: List[Review]) -> Dict[int, int]:
        """Get breakdown of ratings (1-5 stars)"""
        breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in reviews:
            breakdown[review.rating] += 1
        return breakdown
    
    def get_store_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        total_plugins = len(self.store_items)
        free_plugins = len([p for p in self.store_items.values() if p.is_free])
        paid_plugins = total_plugins - free_plugins
        
        plugins_with_ratings = [p for p in self.store_items.values() if p.rating > 0]
        avg_rating = sum(p.rating for p in plugins_with_ratings) / len(plugins_with_ratings) if plugins_with_ratings else 0
        
        total_downloads = sum(p.download_count for p in self.store_items.values())
        
        return {
            "total_plugins": total_plugins,
            "free_plugins": free_plugins,
            "paid_plugins": paid_plugins,
            "average_rating": round(avg_rating, 1),
            "total_downloads": total_downloads,
            "categories": len(self.categories)
        }

# Global store instance
plugin_store = PluginStore()

if __name__ == "__main__":
    # Test the store
    print("🏪 Testing Plugin Store...")
    
    # Test featured plugins
    featured = plugin_store.get_featured_plugins()
    print(f"✅ Featured plugins: {len(featured)}")
    
    # Test search
    golf_results = plugin_store.search_plugins("golf")
    print(f"✅ Golf search results: {len(golf_results)}")
    
    # Test plugin details
    details = plugin_store.get_plugin_details("golf_pro")
    print(f"✅ Golf Pro details: {details['plugin']['name']}")
    
    # Test store stats
    stats = plugin_store.get_store_stats()
    print(f"✅ Store stats: {stats}")
    
    print("✅ Plugin store test completed!")