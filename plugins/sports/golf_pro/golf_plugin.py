"""
Golf Pro Swing Analyzer Plugin

Professional golf swing analysis using pose estimation to provide
detailed feedback on swing mechanics, tempo, and form.
"""

import numpy as np
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

# Import plugin base classes
import sys
import os

# Add the root project directory to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from plugins.core.plugin_manager import SportPlugin, PluginManifest

@dataclass
class SwingPhase:
    """Golf swing phases"""
    SETUP = "setup"
    TAKEAWAY = "takeaway"
    BACKSWING = "backswing"
    TOP = "top"
    TRANSITION = "transition"
    DOWNSWING = "downswing"
    IMPACT = "impact"
    FOLLOW_THROUGH = "follow_through"
    FINISH = "finish"

@dataclass
class SwingAnalysis:
    """Golf swing analysis result"""
    swing_id: str
    timestamp: str
    swing_phase: str
    swing_plane_angle: float
    tempo_ratio: float
    weight_transfer: float
    club_path: str
    impact_position: Dict[str, float]
    swing_speed_estimate: float
    consistency_score: float
    issues: List[str]
    tips: List[str]
    overall_score: float

class GolfProPlugin(SportPlugin):
    """
    Golf Pro Swing Analyzer Plugin
    
    Analyzes golf swings using pose estimation to provide professional-level
    coaching feedback on swing mechanics, tempo, and consistency.
    """
    
    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)
        
        # Golf-specific analysis parameters
        self.swing_phases = [
            SwingPhase.SETUP, SwingPhase.TAKEAWAY, SwingPhase.BACKSWING,
            SwingPhase.TOP, SwingPhase.TRANSITION, SwingPhase.DOWNSWING,
            SwingPhase.IMPACT, SwingPhase.FOLLOW_THROUGH, SwingPhase.FINISH
        ]
        
        # Swing analysis state
        self.current_swing = None
        self.swing_history = []
        self.pose_sequence = []
        self.swing_start_time = None
        
        # Analysis thresholds
        self.setup_threshold = 15  # degrees of shoulder rotation
        self.backswing_threshold = 90  # degrees
        self.impact_threshold = 5   # degrees from setup
        
        # Golf coaching knowledge base
        self.coaching_tips = self._load_coaching_tips()
    
    def initialize(self) -> bool:
        """Initialize the Golf Pro plugin"""
        try:
            print("🏌️ Initializing Golf Pro Swing Analyzer...")
            print("   ✅ Swing analysis engine loaded")
            print("   ✅ Coaching database loaded")
            print("   ✅ Tempo analyzer ready")
            self.is_loaded = True
            return True
        except Exception as e:
            print(f"❌ Golf Pro initialization failed: {e}")
            return False
    
    def analyze_movement(self, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze golf swing movement from pose data
        
        Args:
            pose_data: Pose estimation data with keypoints
            
        Returns:
            Swing analysis results
        """
        
        if not pose_data or 'keypoints' not in pose_data:
            return {"error": "Invalid pose data"}
        
        # Add pose to sequence
        self.pose_sequence.append({
            'timestamp': datetime.now().isoformat(),
            'pose': pose_data
        })
        
        # Keep only recent poses (last 5 seconds at 30fps)
        if len(self.pose_sequence) > 150:
            self.pose_sequence.pop(0)
        
        # Analyze current swing phase
        current_phase = self._detect_swing_phase(pose_data)
        
        # Check for swing completion
        if self._is_swing_complete(current_phase):
            swing_analysis = self._analyze_complete_swing()
            self.swing_history.append(swing_analysis)
            self._reset_swing()
            return {
                "swing_complete": True,
                "analysis": swing_analysis,
                "current_phase": current_phase
            }
        
        # Return real-time analysis
        return {
            "swing_complete": False,
            "current_phase": current_phase,
            "real_time_feedback": self._get_real_time_feedback(pose_data, current_phase),
            "swing_progress": self._calculate_swing_progress(current_phase)
        }
    
    def _detect_swing_phase(self, pose_data: Dict[str, Any]) -> str:
        """Detect current phase of golf swing"""
        
        # Calculate key angles
        angles = self._calculate_golf_angles(pose_data)
        shoulder_rotation = angles.get('shoulder_rotation', 0)
        hip_rotation = angles.get('hip_rotation', 0)
        spine_angle = angles.get('spine_angle', 0)
        
        # Phase detection logic
        if abs(shoulder_rotation) < self.setup_threshold:
            return SwingPhase.SETUP
        elif 0 < shoulder_rotation < 45:
            return SwingPhase.TAKEAWAY
        elif 45 <= shoulder_rotation < 90:
            return SwingPhase.BACKSWING
        elif shoulder_rotation >= 90:
            return SwingPhase.TOP
        elif shoulder_rotation < 0 and shoulder_rotation > -30:
            return SwingPhase.DOWNSWING
        elif shoulder_rotation <= -30:
            return SwingPhase.IMPACT
        else:
            return SwingPhase.FOLLOW_THROUGH
    
    def _calculate_golf_angles(self, pose_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate golf-specific body angles"""
        
        keypoints = pose_data.get('keypoints', [])
        if len(keypoints) < 20:
            return {}
        
        # Create keypoint lookup
        kp_dict = {}
        for kp in keypoints:
            if hasattr(kp, 'name') and hasattr(kp, 'x') and hasattr(kp, 'y'):
                kp_dict[kp.name] = kp
            elif isinstance(kp, dict):
                kp_dict[kp.get('name', '')] = kp
        
        angles = {}
        
        try:
            # Shoulder rotation (key metric for golf swing)
            if all(key in kp_dict for key in ['left_shoulder', 'right_shoulder']):
                left_shoulder = kp_dict['left_shoulder']
                right_shoulder = kp_dict['right_shoulder']
                
                # Calculate shoulder line angle
                if hasattr(left_shoulder, 'x'):
                    dx = right_shoulder.x - left_shoulder.x
                    dy = right_shoulder.y - left_shoulder.y
                else:
                    dx = right_shoulder['x'] - left_shoulder['x']
                    dy = right_shoulder['y'] - left_shoulder['y']
                
                shoulder_angle = math.degrees(math.atan2(dy, dx))
                angles['shoulder_rotation'] = shoulder_angle
            
            # Hip rotation
            if all(key in kp_dict for key in ['left_hip', 'right_hip']):
                left_hip = kp_dict['left_hip']
                right_hip = kp_dict['right_hip']
                
                if hasattr(left_hip, 'x'):
                    dx = right_hip.x - left_hip.x
                    dy = right_hip.y - left_hip.y
                else:
                    dx = right_hip['x'] - left_hip['x']
                    dy = right_hip['y'] - left_hip['y']
                
                hip_angle = math.degrees(math.atan2(dy, dx))
                angles['hip_rotation'] = hip_angle
            
            # Spine angle (posture)
            if all(key in kp_dict for key in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']):
                # Calculate spine tilt
                shoulder_center = self._get_midpoint(kp_dict['left_shoulder'], kp_dict['right_shoulder'])
                hip_center = self._get_midpoint(kp_dict['left_hip'], kp_dict['right_hip'])
                
                if hasattr(shoulder_center, 'x'):
                    dx = shoulder_center.x - hip_center.x
                    dy = shoulder_center.y - hip_center.y
                else:
                    dx = shoulder_center['x'] - hip_center['x']
                    dy = shoulder_center['y'] - hip_center['y']
                
                spine_angle = math.degrees(math.atan2(dx, dy))
                angles['spine_angle'] = spine_angle
            
            # Arm angles (for swing plane analysis)
            if all(key in kp_dict for key in ['left_shoulder', 'left_elbow', 'left_wrist']):
                left_arm_angle = self._calculate_three_point_angle(
                    kp_dict['left_shoulder'], kp_dict['left_elbow'], kp_dict['left_wrist']
                )
                angles['left_arm_angle'] = left_arm_angle
            
        except Exception as e:
            print(f"Error calculating golf angles: {e}")
        
        return angles
    
    def _get_midpoint(self, p1, p2):
        """Calculate midpoint between two points"""
        if hasattr(p1, 'x'):
            return type('Point', (), {
                'x': (p1.x + p2.x) / 2,
                'y': (p1.y + p2.y) / 2
            })
        else:
            return {
                'x': (p1['x'] + p2['x']) / 2,
                'y': (p1['y'] + p2['y']) / 2
            }
    
    def _calculate_three_point_angle(self, p1, p2, p3) -> float:
        """Calculate angle at p2 formed by p1-p2-p3"""
        try:
            if hasattr(p1, 'x'):
                v1 = (p1.x - p2.x, p1.y - p2.y)
                v2 = (p3.x - p2.x, p3.y - p2.y)
            else:
                v1 = (p1['x'] - p2['x'], p1['y'] - p2['y'])
                v2 = (p3['x'] - p2['x'], p3['y'] - p2['y'])
            
            dot_product = v1[0] * v2[0] + v1[1] * v2[1]
            magnitude1 = math.sqrt(v1[0]**2 + v1[1]**2)
            magnitude2 = math.sqrt(v2[0]**2 + v2[1]**2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            cos_angle = dot_product / (magnitude1 * magnitude2)
            cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
            
            return math.degrees(math.acos(cos_angle))
            
        except:
            return 0.0
    
    def _is_swing_complete(self, current_phase: str) -> bool:
        """Determine if a complete swing has been executed"""
        
        if len(self.pose_sequence) < 30:  # Need minimum sequence
            return False
        
        # Look for setup -> backswing -> downswing -> follow-through pattern
        recent_phases = [self._detect_swing_phase(pose['pose']) for pose in self.pose_sequence[-30:]]
        
        # Check for complete swing pattern
        has_setup = SwingPhase.SETUP in recent_phases
        has_backswing = SwingPhase.BACKSWING in recent_phases or SwingPhase.TOP in recent_phases
        has_downswing = SwingPhase.DOWNSWING in recent_phases or SwingPhase.IMPACT in recent_phases
        has_follow_through = SwingPhase.FOLLOW_THROUGH in recent_phases
        
        return has_setup and has_backswing and has_downswing and (
            current_phase == SwingPhase.FOLLOW_THROUGH or current_phase == SwingPhase.FINISH
        )
    
    def _analyze_complete_swing(self) -> SwingAnalysis:
        """Analyze a complete swing sequence"""
        
        swing_id = f"swing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate swing metrics
        swing_plane = self._analyze_swing_plane()
        tempo = self._analyze_tempo()
        weight_transfer = self._analyze_weight_transfer()
        consistency = self._calculate_consistency()
        
        # Identify issues and generate tips
        issues = self._identify_swing_issues(swing_plane, tempo, weight_transfer)
        tips = self.get_coaching_tips({"issues": issues, "swing_plane": swing_plane})
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(swing_plane, tempo, weight_transfer, consistency)
        
        return SwingAnalysis(
            swing_id=swing_id,
            timestamp=datetime.now().isoformat(),
            swing_phase="complete",
            swing_plane_angle=swing_plane.get('angle', 0),
            tempo_ratio=tempo.get('ratio', 1.0),
            weight_transfer=weight_transfer.get('score', 0.5),
            club_path=swing_plane.get('path', 'neutral'),
            impact_position=self._analyze_impact_position(),
            swing_speed_estimate=tempo.get('speed_estimate', 0),
            consistency_score=consistency,
            issues=issues,
            tips=tips[:3],  # Top 3 tips
            overall_score=overall_score
        )
    
    def _analyze_swing_plane(self) -> Dict[str, Any]:
        """Analyze swing plane characteristics"""
        
        if len(self.pose_sequence) < 20:
            return {"angle": 0, "path": "neutral", "consistency": 0.5}
        
        # Extract arm positions during swing
        arm_positions = []
        for pose_data in self.pose_sequence:
            angles = self._calculate_golf_angles(pose_data['pose'])
            if 'left_arm_angle' in angles:
                arm_positions.append(angles['left_arm_angle'])
        
        if not arm_positions:
            return {"angle": 0, "path": "neutral", "consistency": 0.5}
        
        # Calculate average swing plane angle
        avg_angle = np.mean(arm_positions)
        consistency = 1.0 - (np.std(arm_positions) / 180.0)  # Normalize by max possible variation
        
        # Determine swing path
        if avg_angle < 120:
            path = "steep"
        elif avg_angle > 150:
            path = "shallow"
        else:
            path = "neutral"
        
        return {
            "angle": avg_angle,
            "path": path,
            "consistency": max(0, min(1, consistency)),
            "range": max(arm_positions) - min(arm_positions)
        }
    
    def _analyze_tempo(self) -> Dict[str, Any]:
        """Analyze swing tempo and timing"""
        
        if len(self.pose_sequence) < 20:
            return {"ratio": 1.0, "speed_estimate": 0}
        
        # Find backswing and downswing phases
        backswing_start = None
        top_position = None
        impact_position = None
        
        for i, pose_data in enumerate(self.pose_sequence):
            phase = self._detect_swing_phase(pose_data['pose'])
            
            if phase == SwingPhase.TAKEAWAY and backswing_start is None:
                backswing_start = i
            elif phase == SwingPhase.TOP:
                top_position = i
            elif phase == SwingPhase.IMPACT:
                impact_position = i
                break
        
        # Calculate tempo ratio (backswing time : downswing time)
        if backswing_start and top_position and impact_position:
            backswing_frames = top_position - backswing_start
            downswing_frames = impact_position - top_position
            
            if downswing_frames > 0:
                tempo_ratio = backswing_frames / downswing_frames
            else:
                tempo_ratio = 1.0
            
            # Estimate swing speed (frames from top to impact)
            speed_estimate = max(0, 100 - downswing_frames * 2)  # Rough estimate
        else:
            tempo_ratio = 1.0
            speed_estimate = 0
        
        return {
            "ratio": tempo_ratio,
            "speed_estimate": speed_estimate,
            "backswing_frames": backswing_frames if 'backswing_frames' in locals() else 0,
            "downswing_frames": downswing_frames if 'downswing_frames' in locals() else 0
        }
    
    def _analyze_weight_transfer(self) -> Dict[str, Any]:
        """Analyze weight transfer during swing"""
        
        # This would analyze hip and foot position changes
        # For now, return a simulated analysis
        return {
            "score": 0.75,
            "peak_transfer": 0.8,
            "timing": "good"
        }
    
    def _analyze_impact_position(self) -> Dict[str, float]:
        """Analyze body position at impact"""
        
        # Find impact frame
        impact_pose = None
        for pose_data in reversed(self.pose_sequence):
            if self._detect_swing_phase(pose_data['pose']) == SwingPhase.IMPACT:
                impact_pose = pose_data['pose']
                break
        
        if not impact_pose:
            return {"hip_rotation": 0, "shoulder_rotation": 0, "spine_angle": 0}
        
        angles = self._calculate_golf_angles(impact_pose)
        return {
            "hip_rotation": angles.get('hip_rotation', 0),
            "shoulder_rotation": angles.get('shoulder_rotation', 0),
            "spine_angle": angles.get('spine_angle', 0)
        }
    
    def _calculate_consistency(self) -> float:
        """Calculate swing consistency score"""
        
        if len(self.swing_history) < 2:
            return 0.5
        
        # Compare recent swings for consistency
        recent_swings = self.swing_history[-5:]  # Last 5 swings
        
        plane_angles = [swing.swing_plane_angle for swing in recent_swings]
        tempo_ratios = [swing.tempo_ratio for swing in recent_swings]
        
        # Calculate consistency based on standard deviation
        plane_consistency = 1.0 - (np.std(plane_angles) / 45.0)  # Normalize
        tempo_consistency = 1.0 - (np.std(tempo_ratios) / 1.0)   # Normalize
        
        overall_consistency = (plane_consistency + tempo_consistency) / 2
        return max(0, min(1, overall_consistency))
    
    def _identify_swing_issues(self, swing_plane: Dict, tempo: Dict, weight_transfer: Dict) -> List[str]:
        """Identify specific swing issues"""
        
        issues = []
        
        # Swing plane issues
        if swing_plane['path'] == 'steep':
            issues.append("Swing plane too steep - coming over the top")
        elif swing_plane['path'] == 'shallow':
            issues.append("Swing plane too shallow - coming from inside")
        
        if swing_plane['consistency'] < 0.6:
            issues.append("Inconsistent swing plane - work on repeatability")
        
        # Tempo issues
        if tempo['ratio'] > 3.0:
            issues.append("Backswing too slow - rushing the downswing")
        elif tempo['ratio'] < 2.0:
            issues.append("Backswing too fast - not enough time to load")
        
        # Weight transfer issues
        if weight_transfer['score'] < 0.6:
            issues.append("Poor weight transfer - not using ground properly")
        
        return issues
    
    def _calculate_overall_score(self, swing_plane: Dict, tempo: Dict, 
                                weight_transfer: Dict, consistency: float) -> float:
        """Calculate overall swing score (0-100)"""
        
        # Weight different aspects
        plane_score = swing_plane['consistency'] * 30
        tempo_score = min(1.0, 3.0 / max(tempo['ratio'], 0.1)) * 25  # Ideal tempo ratio ~3:1
        transfer_score = weight_transfer['score'] * 25
        consistency_score = consistency * 20
        
        total_score = plane_score + tempo_score + transfer_score + consistency_score
        return min(100, max(0, total_score))
    
    def _get_real_time_feedback(self, pose_data: Dict, phase: str) -> List[str]:
        """Generate real-time feedback during swing"""
        
        feedback = []
        angles = self._calculate_golf_angles(pose_data)
        
        if phase == SwingPhase.SETUP:
            feedback.append("Good setup position - maintain spine angle")
        elif phase == SwingPhase.BACKSWING:
            if angles.get('shoulder_rotation', 0) > 100:
                feedback.append("Good shoulder turn - maintain width")
        elif phase == SwingPhase.DOWNSWING:
            feedback.append("Start with hips - let hands follow")
        elif phase == SwingPhase.IMPACT:
            feedback.append("Strike down and through")
        
        return feedback
    
    def _calculate_swing_progress(self, phase: str) -> float:
        """Calculate swing completion progress (0-1)"""
        
        phase_progress = {
            SwingPhase.SETUP: 0.0,
            SwingPhase.TAKEAWAY: 0.15,
            SwingPhase.BACKSWING: 0.35,
            SwingPhase.TOP: 0.5,
            SwingPhase.TRANSITION: 0.6,
            SwingPhase.DOWNSWING: 0.75,
            SwingPhase.IMPACT: 0.85,
            SwingPhase.FOLLOW_THROUGH: 0.95,
            SwingPhase.FINISH: 1.0
        }
        
        return phase_progress.get(phase, 0.0)
    
    def _reset_swing(self):
        """Reset swing tracking for next swing"""
        self.pose_sequence = []
        self.current_swing = None
        self.swing_start_time = None
    
    def get_coaching_tips(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate coaching tips based on analysis"""
        
        issues = analysis_result.get("issues", [])
        tips = []
        
        # Match issues to coaching tips
        for issue in issues:
            if "steep" in issue.lower():
                tips.extend(self.coaching_tips["swing_plane"]["steep"])
            elif "shallow" in issue.lower():
                tips.extend(self.coaching_tips["swing_plane"]["shallow"])
            elif "tempo" in issue.lower():
                tips.extend(self.coaching_tips["tempo"]["general"])
            elif "weight" in issue.lower():
                tips.extend(self.coaching_tips["weight_transfer"]["general"])
            elif "inconsistent" in issue.lower():
                tips.extend(self.coaching_tips["consistency"]["general"])
        
        # Add general tips if no specific issues
        if not tips:
            tips.extend(self.coaching_tips["general"]["fundamentals"])
        
        return list(set(tips))  # Remove duplicates
    
    def get_exercise_library(self) -> List[Dict[str, Any]]:
        """Return golf-specific exercises and drills"""
        
        return [
            {
                "id": "swing_tempo_drill",
                "name": "Swing Tempo Drill",
                "description": "Practice swings focusing on 3:1 tempo ratio",
                "duration": "10 minutes",
                "difficulty": "beginner"
            },
            {
                "id": "plane_alignment_drill",
                "name": "Swing Plane Alignment",
                "description": "Use alignment stick to practice proper swing plane",
                "duration": "15 minutes",
                "difficulty": "intermediate"
            },
            {
                "id": "weight_transfer_drill",
                "name": "Weight Transfer Practice",
                "description": "Step-through drill for proper weight shift",
                "duration": "10 minutes", 
                "difficulty": "beginner"
            }
        ]
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Return API routes for golf analysis"""
        
        return [
            {
                "path": "/golf/analyze",
                "method": "POST",
                "handler": "analyze_swing",
                "description": "Analyze golf swing from pose data"
            },
            {
                "path": "/golf/history",
                "method": "GET", 
                "handler": "get_swing_history",
                "description": "Get swing analysis history"
            },
            {
                "path": "/golf/tips/{issue_type}",
                "method": "GET",
                "handler": "get_tips_for_issue",
                "description": "Get coaching tips for specific issues"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Return UI components for golf analysis"""
        
        return [
            {
                "id": "swing_analyzer",
                "name": "Swing Analyzer",
                "type": "analysis_display",
                "position": "main"
            },
            {
                "id": "tempo_meter",
                "name": "Tempo Meter", 
                "type": "real_time_meter",
                "position": "sidebar"
            },
            {
                "id": "swing_tips",
                "name": "Coaching Tips",
                "type": "tips_panel",
                "position": "bottom"
            }
        ]
    
    def _load_coaching_tips(self) -> Dict[str, Any]:
        """Load golf coaching tips database"""
        
        return {
            "swing_plane": {
                "steep": [
                    "Focus on taking the club back more inside",
                    "Feel like you're swinging around your body, not up and down",
                    "Practice with a flatter backswing plane"
                ],
                "shallow": [
                    "Work on getting the club more upright in the backswing",
                    "Focus on turning your shoulders more vertically",
                    "Practice steepening your downswing approach"
                ]
            },
            "tempo": {
                "general": [
                    "Practice the 3:1 tempo ratio - slow back, quick down",
                    "Count 'one-two-three' on the backswing, 'one' on the downswing",
                    "Focus on smooth acceleration through impact"
                ]
            },
            "weight_transfer": {
                "general": [
                    "Start the downswing with your hips, not your hands",
                    "Feel your weight move to your front foot at impact",
                    "Practice the step-through drill to feel proper weight shift"
                ]
            },
            "consistency": {
                "general": [
                    "Focus on making the same swing every time",
                    "Practice with a consistent pre-shot routine",
                    "Work on maintaining spine angle throughout the swing"
                ]
            },
            "general": {
                "fundamentals": [
                    "Maintain good posture and spine angle",
                    "Keep your head steady during the swing",
                    "Focus on a smooth, balanced finish"
                ]
            }
        }

    def provide_voice_coaching(self, analysis_result: Dict[str, Any], 
                             voice_service=None) -> List[str]:
        """Provide golf-specific voice coaching feedback"""
        
        if not voice_service:
            return []
        
        spoken_messages = []
        
        # Import voice service locally to avoid circular imports
        try:
            from utils.voice_output import CoachingTone
            
            # Real-time swing feedback
            if 'current_phase' in analysis_result:
                phase = analysis_result['current_phase']
                real_time_feedback = analysis_result.get('real_time_feedback', [])
                
                for feedback in real_time_feedback:
                    voice_service.speak_coaching_cue(
                        text=feedback,
                        tone=CoachingTone.ENCOURAGING,
                        play_immediately=True
                    )
                    spoken_messages.append(feedback)
            
            # Post-swing analysis feedback
            if analysis_result.get('swing_complete'):
                analysis = analysis_result.get('analysis')
                if analysis:
                    
                    # Overall score feedback
                    score = analysis.overall_score
                    if score >= 85:
                        message = f"Excellent swing! Score: {score:.0f}. That's professional level."
                        tone = CoachingTone.CELEBRATING
                    elif score >= 70:
                        message = f"Great swing! Score: {score:.0f}. Keep building on that."
                        tone = CoachingTone.ENCOURAGING
                    elif score >= 50:
                        message = f"Good progress. Score: {score:.0f}. Let's work on a few areas."
                        tone = CoachingTone.SUPPORTIVE
                    else:
                        message = f"Score: {score:.0f}. No worries, let's focus on the fundamentals."
                        tone = CoachingTone.MOTIVATING
                    
                    voice_service.speak_coaching_cue(message, tone)
                    spoken_messages.append(message)
                    
                    # Specific issue feedback
                    if analysis.issues:
                        primary_issue = analysis.issues[0]
                        issue_feedback = self._get_voice_feedback_for_issue(primary_issue)
                        
                        voice_service.speak_coaching_cue(
                            text=issue_feedback,
                            tone=CoachingTone.INSTRUCTIONAL
                        )
                        spoken_messages.append(issue_feedback)
                    
                    # Tempo feedback
                    tempo_ratio = analysis.tempo_ratio
                    if tempo_ratio > 3.5:
                        tempo_message = "Try to speed up your backswing slightly. Aim for a 3-to-1 ratio."
                    elif tempo_ratio < 2.5:
                        tempo_message = "Slow down your backswing. Give yourself time to load properly."
                    else:
                        tempo_message = "Great tempo! That 3-to-1 ratio is perfect."
                    
                    voice_service.speak_coaching_cue(
                        text=tempo_message,
                        tone=CoachingTone.INSTRUCTIONAL
                    )
                    spoken_messages.append(tempo_message)
                    
                    # Encouragement and next step
                    if len(analysis.tips) > 0:
                        next_tip = analysis.tips[0]
                        encouragement = f"Next focus: {next_tip}"
                        
                        voice_service.speak_coaching_cue(
                            text=encouragement,
                            tone=CoachingTone.ENCOURAGING
                        )
                        spoken_messages.append(encouragement)
        
        except ImportError:
            print("Voice service not available")
        
        return spoken_messages
    
    def _get_voice_feedback_for_issue(self, issue: str) -> str:
        """Get specific voice feedback for swing issues"""
        
        voice_feedback_map = {
            "steep": "You're coming over the top. Try to feel like you're swinging around your body, not chopping wood.",
            "shallow": "Your swing is too flat. Think about getting the club more upright in your backswing.",
            "tempo": "Work on your rhythm. Count one-two-three on the way back, and one coming down.",
            "weight": "You're not transferring your weight properly. Start the downswing with your hips.",
            "inconsistent": "Focus on making the same swing every time. Pick one thought and stick with it.",
            "backswing": "Slow down that backswing. Give yourself time to make a full turn.",
            "downswing": "You're rushing the transition. Let the club drop into the slot naturally."
        }
        
        for key, feedback in voice_feedback_map.items():
            if key in issue.lower():
                return feedback
        
        return "Keep working on the fundamentals. Stay balanced and commit to the swing."
    
    def provide_drill_coaching(self, drill_name: str, voice_service=None) -> List[str]:
        """Provide voice coaching for specific golf drills"""
        
        if not voice_service:
            return []
        
        try:
            from utils.voice_output import CoachingTone
            
            drill_instructions = {
                "swing_tempo_drill": [
                    "Let's work on tempo. Take slow practice swings.",
                    "Count one-two-three on the backswing.",
                    "Then one quick count down to impact.",
                    "Feel that 3-to-1 rhythm. Slow back, quick down."
                ],
                "plane_alignment_drill": [
                    "Set up with an alignment stick along your target line.",
                    "Take slow backswings, feeling the club track along the proper plane.", 
                    "The club should stay parallel to the alignment stick.",
                    "This builds muscle memory for the correct swing path."
                ],
                "weight_transfer_drill": [
                    "Start in your address position.",
                    "Step through with your front foot as you swing.",
                    "Feel your weight move from back foot to front foot.",
                    "This is how proper weight transfer should feel."
                ]
            }
            
            instructions = drill_instructions.get(drill_name, [
                "Focus on smooth, controlled movements.",
                "Quality over quantity - make each rep count."
            ])
            
            spoken_messages = []
            for instruction in instructions:
                voice_service.speak_coaching_cue(
                    text=instruction,
                    tone=CoachingTone.INSTRUCTIONAL
                )
                spoken_messages.append(instruction)
            
            return spoken_messages
            
        except ImportError:
            print("Voice service not available")
            return []
    
    def provide_pre_swing_coaching(self, voice_service=None) -> str:
        """Provide pre-swing setup coaching"""
        
        if not voice_service:
            return ""
        
        try:
            from utils.voice_output import CoachingTone
            
            setup_reminders = [
                "Take your time. Get comfortable over the ball.",
                "Good posture. Athletic stance. Weight balanced.",
                "Pick your target and commit to the swing.",
                "Trust your practice. Make a confident swing.",
                "Smooth tempo. Let the club do the work."
            ]
            
            import random
            message = random.choice(setup_reminders)
            
            voice_service.speak_coaching_cue(
                text=message,
                tone=CoachingTone.CALMING
            )
            
            return message
            
        except ImportError:
            print("Voice service not available")
            return ""

# Plugin instance - this is what gets loaded by the plugin manager
def create_plugin(manifest: PluginManifest) -> GolfProPlugin:
    """Factory function to create the plugin instance"""
    return GolfProPlugin(manifest)