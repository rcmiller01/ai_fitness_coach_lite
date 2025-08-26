"""
Tennis Pro Plugin for AI Fitness Coach

Professional tennis stroke analysis including serves, forehands, backhands, and volleys.
Uses advanced pose estimation and biomechanical analysis to provide coaching feedback.
"""

import numpy as np
import cv2
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import time
from datetime import datetime

# Import core plugin classes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
from plugin_manager import SportPlugin, PluginManifest

class TennisStroke(Enum):
    """Types of tennis strokes"""
    SERVE = "serve"
    FOREHAND = "forehand"
    BACKHAND = "backhand"
    VOLLEY = "volley"
    OVERHEAD = "overhead"
    UNKNOWN = "unknown"

class StrokePhase(Enum):
    """Phases of tennis stroke execution"""
    PREPARATION = "preparation"
    BACKSWING = "backswing"
    FORWARD_SWING = "forward_swing"
    CONTACT = "contact"
    FOLLOW_THROUGH = "follow_through"
    RECOVERY = "recovery"

@dataclass
class TennisKeypoints:
    """Tennis-specific pose keypoints"""
    left_shoulder: Tuple[float, float]
    right_shoulder: Tuple[float, float]
    left_elbow: Tuple[float, float]
    right_elbow: Tuple[float, float]
    left_wrist: Tuple[float, float]
    right_wrist: Tuple[float, float]
    left_hip: Tuple[float, float]
    right_hip: Tuple[float, float]
    left_knee: Tuple[float, float]
    right_knee: Tuple[float, float]
    left_ankle: Tuple[float, float]
    right_ankle: Tuple[float, float]

@dataclass
class StrokeMetrics:
    """Tennis stroke analysis metrics"""
    stroke_type: TennisStroke
    stroke_phase: StrokePhase
    racket_speed: float  # km/h
    ball_contact_angle: float  # degrees
    body_rotation: float  # degrees
    weight_transfer: float  # percentage
    timing_score: float  # 0-100
    power_score: float  # 0-100
    accuracy_score: float  # 0-100
    overall_score: float  # 0-100
    timestamp: str

@dataclass
class TennisSession:
    """Tennis training session data"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    strokes_analyzed: int = 0
    stroke_breakdown: Dict[str, int] = None
    average_scores: Dict[str, float] = None
    improvements: List[str] = None
    recommendations: List[str] = None

class TennisProPlugin(SportPlugin):
    """Professional Tennis Stroke Analysis Plugin"""
    
    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)
        self.stroke_detector = TennisStrokeDetector()
        self.technique_analyzer = TennisTechniqueAnalyzer()
        self.coaching_system = TennisCoachingSystem()
        self.current_session = None
        
    def initialize(self) -> bool:
        """Initialize tennis analysis systems"""
        try:
            print("🎾 Initializing Tennis Pro Plugin...")
            
            # Initialize pose estimation
            self.stroke_detector.initialize()
            
            # Load tennis-specific models
            self.technique_analyzer.load_models()
            
            # Setup coaching database
            self.coaching_system.initialize()
            
            print("✅ Tennis Pro Plugin initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Tennis Pro Plugin: {e}")
            return False
    
    def analyze_movement(self, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tennis stroke from pose data"""
        try:
            # Extract tennis keypoints
            keypoints = self._extract_tennis_keypoints(pose_data)
            
            # Detect stroke type and phase
            stroke_info = self.stroke_detector.detect_stroke(keypoints)
            
            # Analyze technique
            technique_analysis = self.technique_analyzer.analyze_technique(
                keypoints, stroke_info
            )
            
            # Generate metrics
            metrics = self._calculate_stroke_metrics(keypoints, stroke_info, technique_analysis)
            
            # Update session data
            if self.current_session:
                self._update_session(metrics)
            
            return {
                "plugin_id": "tennis_pro",
                "analysis_type": "stroke_analysis",
                "stroke_type": stroke_info.stroke_type.value,
                "stroke_phase": stroke_info.stroke_phase.value,
                "metrics": asdict(metrics),
                "technique_analysis": technique_analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "plugin_id": "tennis_pro",
                "error": f"Analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_coaching_tips(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate tennis coaching tips based on analysis"""
        if "error" in analysis_result:
            return ["Please ensure proper camera positioning and lighting for analysis."]
        
        return self.coaching_system.generate_tips(analysis_result)
    
    def get_exercise_library(self) -> List[Dict[str, Any]]:
        """Return tennis-specific exercises and drills"""
        return [
            {
                "id": "tennis_serve_practice",
                "name": "Serve Technique Practice",
                "description": "Practice proper serve technique with ball toss and racket swing",
                "duration": "15 minutes",
                "equipment": ["tennis racket", "tennis balls"],
                "difficulty": "intermediate",
                "instructions": [
                    "Start with proper serving stance",
                    "Practice ball toss to consistent height",
                    "Focus on racket head speed through contact",
                    "Follow through across body"
                ]
            },
            {
                "id": "forehand_topspin_drill",
                "name": "Forehand Topspin Development",
                "description": "Develop consistent topspin forehand technique",
                "duration": "20 minutes",
                "equipment": ["tennis racket", "tennis balls", "practice wall"],
                "difficulty": "beginner",
                "instructions": [
                    "Stand sideways to target",
                    "Low to high swing path",
                    "Brush up on back of ball",
                    "Follow through over opposite shoulder"
                ]
            },
            {
                "id": "backhand_slice_technique",
                "name": "Backhand Slice Technique",
                "description": "Master the backhand slice for variety and control",
                "duration": "15 minutes",
                "equipment": ["tennis racket", "tennis balls"],
                "difficulty": "intermediate",
                "instructions": [
                    "Prepare early with shoulder turn",
                    "High to low swing path",
                    "Contact ball slightly in front",
                    "Short, controlled follow through"
                ]
            },
            {
                "id": "volley_reaction_drill",
                "name": "Net Volley Reaction Training",
                "description": "Improve volley reaction time and technique",
                "duration": "10 minutes",
                "equipment": ["tennis racket", "tennis balls"],
                "difficulty": "advanced",
                "instructions": [
                    "Position at net with ready stance",
                    "Short backswing preparation",
                    "Firm wrist through contact",
                    "Step into the volley"
                ]
            }
        ]
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Return API routes for tennis analysis"""
        return [
            {
                "path": "/tennis/analyze",
                "method": "POST",
                "handler": "analyze_stroke",
                "description": "Analyze tennis stroke from video/image data"
            },
            {
                "path": "/tennis/session/start",
                "method": "POST", 
                "handler": "start_session",
                "description": "Start new tennis training session"
            },
            {
                "path": "/tennis/session/end",
                "method": "POST",
                "handler": "end_session", 
                "description": "End current tennis session and get summary"
            },
            {
                "path": "/tennis/stats",
                "method": "GET",
                "handler": "get_statistics",
                "description": "Get tennis performance statistics"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Return UI components for tennis coaching"""
        return [
            {
                "component": "TennisStrokeAnalyzer",
                "type": "analysis_display",
                "props": {
                    "show_stroke_type": True,
                    "show_metrics": True,
                    "show_3d_model": True
                }
            },
            {
                "component": "TennisCourtView", 
                "type": "court_overlay",
                "props": {
                    "show_position": True,
                    "show_ball_trajectory": True,
                    "court_type": "singles"
                }
            },
            {
                "component": "TennisMetricsDashboard",
                "type": "metrics_panel", 
                "props": {
                    "metrics": ["power", "accuracy", "timing", "consistency"],
                    "chart_type": "radar"
                }
            }
        ]
    
    def start_session(self) -> str:
        """Start a new tennis training session"""
        session_id = f"tennis_{int(time.time())}"
        self.current_session = TennisSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            stroke_breakdown={},
            average_scores={},
            improvements=[],
            recommendations=[]
        )
        return session_id
    
    def end_session(self) -> Dict[str, Any]:
        """End current session and return summary"""
        if not self.current_session:
            return {"error": "No active session"}
        
        self.current_session.end_time = datetime.now().isoformat()
        session_summary = asdict(self.current_session)
        
        # Generate final recommendations
        session_summary["final_recommendations"] = self.coaching_system.generate_session_summary(
            self.current_session
        )
        
        self.current_session = None
        return session_summary
    
    def _extract_tennis_keypoints(self, pose_data: Dict[str, Any]) -> TennisKeypoints:
        """Extract tennis-relevant keypoints from pose data"""
        landmarks = pose_data.get("landmarks", {})
        
        return TennisKeypoints(
            left_shoulder=landmarks.get("left_shoulder", (0, 0)),
            right_shoulder=landmarks.get("right_shoulder", (0, 0)),
            left_elbow=landmarks.get("left_elbow", (0, 0)),
            right_elbow=landmarks.get("right_elbow", (0, 0)),
            left_wrist=landmarks.get("left_wrist", (0, 0)),
            right_wrist=landmarks.get("right_wrist", (0, 0)),
            left_hip=landmarks.get("left_hip", (0, 0)),
            right_hip=landmarks.get("right_hip", (0, 0)),
            left_knee=landmarks.get("left_knee", (0, 0)),
            right_knee=landmarks.get("right_knee", (0, 0)),
            left_ankle=landmarks.get("left_ankle", (0, 0)),
            right_ankle=landmarks.get("right_ankle", (0, 0))
        )
    
    def _calculate_stroke_metrics(self, keypoints: TennisKeypoints, 
                                stroke_info: Any, technique_analysis: Dict) -> StrokeMetrics:
        """Calculate comprehensive stroke metrics"""
        # Mock calculations - in real implementation, use biomechanical analysis
        racket_speed = technique_analysis.get("racket_speed", 85.0)
        ball_contact_angle = technique_analysis.get("contact_angle", 15.0)
        body_rotation = technique_analysis.get("body_rotation", 45.0)
        weight_transfer = technique_analysis.get("weight_transfer", 75.0)
        
        # Calculate scores based on stroke type
        timing_score = min(100, max(0, 85 + np.random.normal(0, 10)))
        power_score = min(100, max(0, racket_speed * 1.2))
        accuracy_score = min(100, max(0, 90 - abs(ball_contact_angle - 10) * 2))
        overall_score = (timing_score + power_score + accuracy_score) / 3
        
        return StrokeMetrics(
            stroke_type=stroke_info.stroke_type,
            stroke_phase=stroke_info.stroke_phase,
            racket_speed=racket_speed,
            ball_contact_angle=ball_contact_angle,
            body_rotation=body_rotation,
            weight_transfer=weight_transfer,
            timing_score=timing_score,
            power_score=power_score,
            accuracy_score=accuracy_score,
            overall_score=overall_score,
            timestamp=datetime.now().isoformat()
        )
    
    def _update_session(self, metrics: StrokeMetrics):
        """Update current session with new metrics"""
        if not self.current_session:
            return
        
        self.current_session.strokes_analyzed += 1
        stroke_type = metrics.stroke_type.value
        
        # Update stroke breakdown
        if not self.current_session.stroke_breakdown:
            self.current_session.stroke_breakdown = {}
        self.current_session.stroke_breakdown[stroke_type] = \
            self.current_session.stroke_breakdown.get(stroke_type, 0) + 1
        
        # Update average scores
        if not self.current_session.average_scores:
            self.current_session.average_scores = {}
        
        current_avg = self.current_session.average_scores.get("overall", 0)
        count = self.current_session.strokes_analyzed
        new_avg = ((current_avg * (count - 1)) + metrics.overall_score) / count
        self.current_session.average_scores["overall"] = round(new_avg, 1)

class TennisStrokeDetector:
    """Detects tennis stroke types and phases"""
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self):
        """Initialize stroke detection models"""
        # In real implementation, load trained models
        self.initialized = True
    
    def detect_stroke(self, keypoints: TennisKeypoints) -> Any:
        """Detect stroke type and phase from keypoints"""
        # Mock stroke detection - in real implementation, use ML models
        from collections import namedtuple
        StrokeInfo = namedtuple('StrokeInfo', ['stroke_type', 'stroke_phase'])
        
        # Simple heuristic based on wrist position
        right_wrist_y = keypoints.right_wrist[1] if keypoints.right_wrist else 0
        right_shoulder_y = keypoints.right_shoulder[1] if keypoints.right_shoulder else 0
        
        if right_wrist_y < right_shoulder_y:
            stroke_type = TennisStroke.SERVE
        else:
            stroke_type = TennisStroke.FOREHAND
        
        # Simple phase detection
        stroke_phase = StrokePhase.FORWARD_SWING
        
        return StrokeInfo(stroke_type, stroke_phase)

class TennisTechniqueAnalyzer:
    """Analyzes tennis technique and biomechanics"""
    
    def __init__(self):
        self.models_loaded = False
    
    def load_models(self):
        """Load technique analysis models"""
        # In real implementation, load trained models
        self.models_loaded = True
    
    def analyze_technique(self, keypoints: TennisKeypoints, stroke_info: Any) -> Dict[str, Any]:
        """Analyze technique for specific stroke"""
        # Mock technique analysis
        return {
            "racket_speed": 85.0 + np.random.normal(0, 15),
            "contact_angle": 15.0 + np.random.normal(0, 5),
            "body_rotation": 45.0 + np.random.normal(0, 10),
            "weight_transfer": 75.0 + np.random.normal(0, 15),
            "grip_position": "eastern_forehand",
            "stance_type": "open_stance",
            "preparation_time": 1.2,
            "contact_point": "optimal"
        }

class TennisCoachingSystem:
    """Generates tennis coaching tips and feedback"""
    
    def __init__(self):
        self.coaching_database = {}
    
    def initialize(self):
        """Initialize coaching knowledge base"""
        self.coaching_database = {
            TennisStroke.SERVE: {
                "power_tips": [
                    "Use your legs to drive up through the serve",
                    "Snap your wrist at contact for added racket head speed",
                    "Keep your elbow high during the trophy position"
                ],
                "accuracy_tips": [
                    "Consistent ball toss is key to accurate serving",
                    "Keep your head up and watch the ball until contact",
                    "Follow through in the direction of your target"
                ],
                "timing_tips": [
                    "Start your swing as the ball reaches its peak",
                    "Coordinate your leg drive with arm swing",
                    "Practice your rhythm with shadow swings"
                ]
            },
            TennisStroke.FOREHAND: {
                "power_tips": [
                    "Rotate your shoulders and hips together",
                    "Accelerate through contact, don't slow down",
                    "Use your non-hitting hand for balance and timing"
                ],
                "accuracy_tips": [
                    "Keep your eye on the ball through contact",
                    "Make contact in front of your body",
                    "Follow through over your opposite shoulder"
                ],
                "timing_tips": [
                    "Start your preparation early",
                    "Step into the shot with your front foot",
                    "Time your swing to meet the ball at its optimal height"
                ]
            }
        }
    
    def generate_tips(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate coaching tips based on analysis"""
        tips = []
        
        if "metrics" not in analysis_result:
            return ["Focus on proper form and technique"]
        
        metrics = analysis_result["metrics"]
        stroke_type = TennisStroke(analysis_result["stroke_type"])
        
        # Get stroke-specific tips
        stroke_tips = self.coaching_database.get(stroke_type, {})
        
        # Power feedback
        if metrics["power_score"] < 70:
            tips.extend(stroke_tips.get("power_tips", [])[:2])
        
        # Accuracy feedback  
        if metrics["accuracy_score"] < 80:
            tips.extend(stroke_tips.get("accuracy_tips", [])[:2])
        
        # Timing feedback
        if metrics["timing_score"] < 75:
            tips.extend(stroke_tips.get("timing_tips", [])[:1])
        
        # General encouragement
        if metrics["overall_score"] > 85:
            tips.append("Excellent technique! Keep up the consistent form.")
        elif metrics["overall_score"] > 70:
            tips.append("Good stroke! Focus on the small details for improvement.")
        else:
            tips.append("Keep practicing! Focus on fundamentals and consistency.")
        
        return tips[:5]  # Limit to 5 tips
    
    def generate_session_summary(self, session: TennisSession) -> List[str]:
        """Generate session summary recommendations"""
        recommendations = []
        
        if session.strokes_analyzed < 10:
            recommendations.append("Try to analyze more strokes for better insights")
        
        if session.average_scores and session.average_scores.get("overall", 0) > 80:
            recommendations.append("Great session! Your technique is looking consistent")
        else:
            recommendations.append("Focus on fundamentals in your next practice session")
        
        # Stroke-specific recommendations based on breakdown
        if session.stroke_breakdown:
            most_practiced = max(session.stroke_breakdown.items(), key=lambda x: x[1])
            recommendations.append(f"You practiced {most_practiced[0]} the most - great focus!")
        
        return recommendations

# Plugin entry point
def create_plugin(manifest: PluginManifest) -> TennisProPlugin:
    """Create and return tennis plugin instance"""
    return TennisProPlugin(manifest)

if __name__ == "__main__":
    # Test the tennis plugin
    print("🎾 Testing Tennis Pro Plugin...")
    
    # Create mock manifest
    manifest = PluginManifest(
        id="tennis_pro",
        name="Tennis Pro Stroke Analyzer",
        version="1.0.0",
        description="Professional tennis analysis",
        author="AI Fitness Coach Team",
        plugin_type="sport_analysis"
    )
    
    # Initialize plugin
    plugin = TennisProPlugin(manifest)
    success = plugin.initialize()
    
    if success:
        print("✅ Tennis plugin initialized successfully!")
        
        # Test stroke analysis
        mock_pose_data = {
            "landmarks": {
                "left_shoulder": (100, 150),
                "right_shoulder": (200, 150),
                "left_wrist": (80, 200),
                "right_wrist": (250, 180),
                "left_hip": (120, 300),
                "right_hip": (180, 300)
            }
        }
        
        result = plugin.analyze_movement(mock_pose_data)
        print(f"   Analysis result: {result['stroke_type']}")
        print(f"   Overall score: {result['metrics']['overall_score']:.1f}")
        
        tips = plugin.get_coaching_tips(result)
        print(f"   Coaching tips: {len(tips)} tips generated")
        
        exercises = plugin.get_exercise_library()
        print(f"   Exercise library: {len(exercises)} exercises available")
        
    else:
        print("❌ Failed to initialize tennis plugin")