"""
Rep Counter for AI Fitness Coach

Analyzes pose estimation data to automatically count exercise repetitions
with exercise-specific logic and form feedback.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

from models.pose_estimator import PoseEstimation, PoseKeypoint

class ExerciseType(Enum):
    """Supported exercise types for rep counting"""
    PUSH_UPS = "push_ups"
    SQUATS = "squats"
    BICEP_CURLS = "bicep_curls"
    SHOULDER_PRESS = "shoulder_press"
    LUNGES = "lunges"
    JUMPING_JACKS = "jumping_jacks"
    BURPEES = "burpees"
    PULL_UPS = "pull_ups"
    BENCH_PRESS = "bench_press"
    DEADLIFTS = "deadlifts"

class RepPhase(Enum):
    """Phases of a repetition"""
    BOTTOM = "bottom"
    TRANSITION_UP = "transition_up"
    TOP = "top"
    TRANSITION_DOWN = "transition_down"
    UNKNOWN = "unknown"

@dataclass
class RepData:
    """Data for a single repetition"""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    range_of_motion: Optional[float] = None
    form_score: Optional[float] = None
    phase_timings: Dict[RepPhase, float] = field(default_factory=dict)
    form_issues: List[str] = field(default_factory=list)

@dataclass
class RepCountSession:
    """Complete rep counting session data"""
    exercise_type: ExerciseType
    start_time: datetime
    total_reps: int = 0
    current_phase: RepPhase = RepPhase.UNKNOWN
    reps_data: List[RepData] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    form_feedback: List[str] = field(default_factory=list)

class RepCounter:
    """
    Exercise-specific repetition counter with form analysis
    """
    
    def __init__(self, exercise_type: ExerciseType):
        self.exercise_type = exercise_type
        self.session = RepCountSession(
            exercise_type=exercise_type,
            start_time=datetime.now()
        )
        
        # Initialize exercise-specific parameters
        self.init_exercise_config()
        
        # State tracking
        self.pose_history = []
        self.angle_history = []
        self.current_rep_start = None
        self.last_phase = RepPhase.UNKNOWN
        
        # Calibration data
        self.calibration_data = {}
        self.is_calibrated = False
    
    def init_exercise_config(self):
        """Initialize exercise-specific configuration"""
        
        # Exercise-specific configurations
        configs = {
            ExerciseType.PUSH_UPS: {
                "primary_angle": "left_arm",  # Main angle to track
                "secondary_angle": "right_arm",
                "bottom_threshold": 90,  # Degrees
                "top_threshold": 160,
                "min_range": 60,  # Minimum range of motion
                "form_checks": ["body_alignment", "arm_symmetry"]
            },
            ExerciseType.SQUATS: {
                "primary_angle": "left_leg",
                "secondary_angle": "right_leg", 
                "bottom_threshold": 90,
                "top_threshold": 170,
                "min_range": 70,
                "form_checks": ["knee_tracking", "torso_upright"]
            },
            ExerciseType.BICEP_CURLS: {
                "primary_angle": "left_arm",
                "secondary_angle": "right_arm",
                "bottom_threshold": 170,
                "top_threshold": 45,
                "min_range": 100,
                "form_checks": ["elbow_stability", "shoulder_stability"]
            },
            ExerciseType.SHOULDER_PRESS: {
                "primary_angle": "left_arm",
                "secondary_angle": "right_arm",
                "bottom_threshold": 90,
                "top_threshold": 170,
                "min_range": 70,
                "form_checks": ["core_stability", "arm_symmetry"]
            },
            ExerciseType.LUNGES: {
                "primary_angle": "left_leg",
                "secondary_angle": "right_leg",
                "bottom_threshold": 90,
                "top_threshold": 170,
                "min_range": 70,
                "form_checks": ["knee_tracking", "torso_upright", "step_length"]
            }
        }
        
        self.config = configs.get(self.exercise_type, {
            "primary_angle": "left_arm",
            "secondary_angle": "right_arm",
            "bottom_threshold": 90,
            "top_threshold": 160,
            "min_range": 60,
            "form_checks": []
        })
    
    def calibrate(self, pose_samples: List[PoseEstimation], top_positions: List[bool]) -> Dict[str, Any]:
        """
        Calibrate rep counter with user-specific range of motion
        
        Args:
            pose_samples: List of pose estimations from calibration
            top_positions: Boolean list indicating which samples are "top" positions
            
        Returns:
            Calibration results
        """
        
        if len(pose_samples) < 4:
            return {"error": "Need at least 4 pose samples for calibration"}
        
        top_angles = []
        bottom_angles = []
        
        for i, pose in enumerate(pose_samples):
            angles = self._calculate_pose_angles(pose)
            primary_angle = angles.get(self.config["primary_angle"], 0)
            
            if top_positions[i]:
                top_angles.append(primary_angle)
            else:
                bottom_angles.append(primary_angle)
        
        if not top_angles or not bottom_angles:
            return {"error": "Need both top and bottom position samples"}
        
        # Calculate user-specific thresholds
        avg_top = np.mean(top_angles)
        avg_bottom = np.mean(bottom_angles)
        
        # Add some tolerance
        tolerance = 10  # degrees
        
        if avg_top > avg_bottom:  # Normal case (e.g., squats, push-ups)
            self.calibration_data = {
                "top_threshold": avg_top - tolerance,
                "bottom_threshold": avg_bottom + tolerance,
                "range_of_motion": avg_top - avg_bottom
            }
        else:  # Inverted case (e.g., bicep curls)
            self.calibration_data = {
                "top_threshold": avg_top + tolerance,
                "bottom_threshold": avg_bottom - tolerance,
                "range_of_motion": avg_bottom - avg_top
            }
        
        self.is_calibrated = True
        
        return {
            "status": "calibrated",
            "top_threshold": self.calibration_data["top_threshold"],
            "bottom_threshold": self.calibration_data["bottom_threshold"],
            "range_of_motion": self.calibration_data["range_of_motion"],
            "samples_used": len(pose_samples)
        }
    
    def process_pose(self, pose: PoseEstimation) -> Dict[str, Any]:
        """
        Process a single pose frame for rep counting
        
        Args:
            pose: PoseEstimation object
            
        Returns:
            Rep counting results for this frame
        """
        
        if not pose or not pose.keypoints:
            return {"error": "Invalid pose data"}
        
        # Calculate current angles
        angles = self._calculate_pose_angles(pose)
        primary_angle = angles.get(self.config["primary_angle"], 0)
        secondary_angle = angles.get(self.config["secondary_angle"], 0)
        
        # Store history
        self.pose_history.append(pose)
        self.angle_history.append(primary_angle)
        
        # Keep only recent history
        if len(self.pose_history) > 60:  # ~2 seconds at 30fps
            self.pose_history.pop(0)
            self.angle_history.pop(0)
        
        # Determine current phase
        current_phase = self._determine_phase(primary_angle)
        
        # Check for rep completion
        rep_completed = False
        if self._is_rep_completed(current_phase):
            rep_completed = True
            self._complete_rep(pose)
        
        # Analyze form
        form_feedback = self._analyze_form(pose, angles)
        
        # Calculate confidence
        confidence = self._calculate_confidence(pose, angles)
        self.session.confidence_scores.append(confidence)
        
        result = {
            "current_phase": current_phase.value,
            "primary_angle": primary_angle,
            "secondary_angle": secondary_angle,
            "rep_completed": rep_completed,
            "total_reps": self.session.total_reps,
            "confidence": confidence,
            "form_feedback": form_feedback,
            "is_calibrated": self.is_calibrated
        }
        
        # Update state
        self.last_phase = current_phase
        self.session.current_phase = current_phase
        
        return result
    
    def _calculate_pose_angles(self, pose: PoseEstimation) -> Dict[str, float]:
        """Calculate key angles from pose estimation"""
        
        # Create keypoint lookup
        kp_dict = {kp.name: kp for kp in pose.keypoints}
        angles = {}
        
        try:
            # Left arm angle (shoulder-elbow-wrist)
            if all(name in kp_dict for name in ["left_shoulder", "left_elbow", "left_wrist"]):
                angles["left_arm"] = self._calculate_angle(
                    kp_dict["left_shoulder"], kp_dict["left_elbow"], kp_dict["left_wrist"]
                )
            
            # Right arm angle
            if all(name in kp_dict for name in ["right_shoulder", "right_elbow", "right_wrist"]):
                angles["right_arm"] = self._calculate_angle(
                    kp_dict["right_shoulder"], kp_dict["right_elbow"], kp_dict["right_wrist"]
                )
            
            # Left leg angle (hip-knee-ankle)
            if all(name in kp_dict for name in ["left_hip", "left_knee", "left_ankle"]):
                angles["left_leg"] = self._calculate_angle(
                    kp_dict["left_hip"], kp_dict["left_knee"], kp_dict["left_ankle"]
                )
            
            # Right leg angle
            if all(name in kp_dict for name in ["right_hip", "right_knee", "right_ankle"]):
                angles["right_leg"] = self._calculate_angle(
                    kp_dict["right_hip"], kp_dict["right_knee"], kp_dict["right_ankle"]
                )
                
        except Exception as e:
            print(f"Error calculating angles: {e}")
        
        return angles
    
    def _calculate_angle(self, p1: PoseKeypoint, p2: PoseKeypoint, p3: PoseKeypoint) -> float:
        """Calculate angle between three points (p2 is the vertex)"""
        
        # Create vectors
        v1 = (p1.x - p2.x, p1.y - p2.y)
        v2 = (p3.x - p2.x, p3.y - p2.y)
        
        # Calculate angle
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        magnitude1 = np.sqrt(v1[0]**2 + v1[1]**2)
        magnitude2 = np.sqrt(v2[0]**2 + v2[1]**2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        cos_angle = dot_product / (magnitude1 * magnitude2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def _determine_phase(self, angle: float) -> RepPhase:
        """Determine current rep phase based on angle"""
        
        # Use calibrated thresholds if available
        if self.is_calibrated:
            top_thresh = self.calibration_data["top_threshold"]
            bottom_thresh = self.calibration_data["bottom_threshold"]
        else:
            top_thresh = self.config["top_threshold"]
            bottom_thresh = self.config["bottom_threshold"]
        
        # For exercises where top angle > bottom angle (e.g., squats, push-ups)
        if top_thresh > bottom_thresh:
            if angle >= top_thresh:
                return RepPhase.TOP
            elif angle <= bottom_thresh:
                return RepPhase.BOTTOM
            else:
                # Determine transition direction based on recent history
                if len(self.angle_history) >= 3:
                    recent_trend = np.mean(np.diff(self.angle_history[-3:]))
                    if recent_trend > 0:
                        return RepPhase.TRANSITION_UP
                    else:
                        return RepPhase.TRANSITION_DOWN
                return RepPhase.UNKNOWN
        else:
            # For exercises where top angle < bottom angle (e.g., bicep curls)
            if angle <= top_thresh:
                return RepPhase.TOP
            elif angle >= bottom_thresh:
                return RepPhase.BOTTOM
            else:
                if len(self.angle_history) >= 3:
                    recent_trend = np.mean(np.diff(self.angle_history[-3:]))
                    if recent_trend < 0:
                        return RepPhase.TRANSITION_UP
                    else:
                        return RepPhase.TRANSITION_DOWN
                return RepPhase.UNKNOWN
    
    def _is_rep_completed(self, current_phase: RepPhase) -> bool:
        """Check if a complete repetition has been performed"""
        
        # Simple state machine: Look for bottom -> top -> bottom cycle
        if (self.last_phase == RepPhase.TOP and 
            current_phase in [RepPhase.BOTTOM, RepPhase.TRANSITION_DOWN]):
            
            # Additional validation: check if we've seen a reasonable range of motion
            if len(self.angle_history) >= 10:
                recent_angles = self.angle_history[-10:]
                angle_range = max(recent_angles) - min(recent_angles)
                min_range = self.calibration_data.get("range_of_motion", self.config["min_range"]) * 0.6
                
                if angle_range >= min_range:
                    return True
        
        return False
    
    def _complete_rep(self, pose: PoseEstimation):
        """Process a completed repetition"""
        
        self.session.total_reps += 1
        
        # Calculate rep metrics
        if self.current_rep_start:
            duration = (datetime.now() - self.current_rep_start).total_seconds()
        else:
            duration = None
        
        # Calculate range of motion from recent history
        if len(self.angle_history) >= 10:
            recent_angles = self.angle_history[-10:]
            range_of_motion = max(recent_angles) - min(recent_angles)
        else:
            range_of_motion = None
        
        # Create rep data
        rep_data = RepData(
            start_time=self.current_rep_start or datetime.now(),
            end_time=datetime.now(),
            duration=duration,
            range_of_motion=range_of_motion,
            form_score=self._calculate_form_score(pose)
        )
        
        self.session.reps_data.append(rep_data)
        self.current_rep_start = datetime.now()
        
        print(f"✅ Rep {self.session.total_reps} completed! ROM: {range_of_motion:.1f}° Duration: {duration:.1f}s")
    
    def _analyze_form(self, pose: PoseEstimation, angles: Dict[str, float]) -> List[str]:
        """Analyze exercise form and provide feedback"""
        
        feedback = []
        
        # Check for exercise-specific form issues
        if self.exercise_type == ExerciseType.PUSH_UPS:
            feedback.extend(self._check_pushup_form(pose, angles))
        elif self.exercise_type == ExerciseType.SQUATS:
            feedback.extend(self._check_squat_form(pose, angles))
        elif self.exercise_type == ExerciseType.BICEP_CURLS:
            feedback.extend(self._check_curl_form(pose, angles))
        
        return feedback
    
    def _check_pushup_form(self, pose: PoseEstimation, angles: Dict[str, float]) -> List[str]:
        """Check push-up specific form"""
        feedback = []
        
        # Check arm symmetry
        left_arm = angles.get("left_arm", 0)
        right_arm = angles.get("right_arm", 0)
        
        if abs(left_arm - right_arm) > 20:
            feedback.append("Keep arms symmetrical")
        
        # Add more push-up specific checks here
        return feedback
    
    def _check_squat_form(self, pose: PoseEstimation, angles: Dict[str, float]) -> List[str]:
        """Check squat specific form"""
        feedback = []
        
        # Check leg symmetry
        left_leg = angles.get("left_leg", 0)
        right_leg = angles.get("right_leg", 0)
        
        if abs(left_leg - right_leg) > 15:
            feedback.append("Keep legs symmetrical")
        
        # Add more squat specific checks here
        return feedback
    
    def _check_curl_form(self, pose: PoseEstimation, angles: Dict[str, float]) -> List[str]:
        """Check bicep curl specific form"""
        feedback = []
        
        # Check for excessive shoulder movement
        # (This would require tracking shoulder position over time)
        
        return feedback
    
    def _calculate_confidence(self, pose: PoseEstimation, angles: Dict[str, float]) -> float:
        """Calculate confidence in the rep counting for this frame"""
        
        confidence_factors = []
        
        # Pose estimation confidence
        if pose.confidence:
            confidence_factors.append(pose.confidence)
        
        # Key point visibility
        key_points = self._get_key_points_for_exercise()
        visible_points = 0
        total_points = len(key_points)
        
        for kp in pose.keypoints:
            if kp.name in key_points and kp.confidence > 0.5:
                visible_points += 1
        
        if total_points > 0:
            visibility_score = visible_points / total_points
            confidence_factors.append(visibility_score)
        
        # Angle consistency (smoothness of movement)
        if len(self.angle_history) >= 3:
            recent_angles = self.angle_history[-3:]
            angle_variance = np.var(recent_angles)
            smoothness_score = max(0, 1 - (angle_variance / 1000))  # Normalize
            confidence_factors.append(smoothness_score)
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    def _get_key_points_for_exercise(self) -> List[str]:
        """Get key pose points needed for specific exercise"""
        
        exercise_keypoints = {
            ExerciseType.PUSH_UPS: ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
            ExerciseType.SQUATS: ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"],
            ExerciseType.BICEP_CURLS: ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
            ExerciseType.SHOULDER_PRESS: ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
            ExerciseType.LUNGES: ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]
        }
        
        return exercise_keypoints.get(self.exercise_type, ["left_shoulder", "right_shoulder", "left_hip", "right_hip"])
    
    def _calculate_form_score(self, pose: PoseEstimation) -> float:
        """Calculate overall form score for the current rep"""
        
        # This would implement more sophisticated form analysis
        # For now, return a basic score based on pose confidence
        return pose.confidence if pose.confidence else 0.5
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current rep counting session"""
        
        total_duration = (datetime.now() - self.session.start_time).total_seconds()
        avg_confidence = np.mean(self.session.confidence_scores) if self.session.confidence_scores else 0
        
        # Calculate rep metrics
        rep_durations = [rep.duration for rep in self.session.reps_data if rep.duration]
        avg_rep_duration = np.mean(rep_durations) if rep_durations else 0
        
        rep_ranges = [rep.range_of_motion for rep in self.session.reps_data if rep.range_of_motion]
        avg_range_of_motion = np.mean(rep_ranges) if rep_ranges else 0
        
        form_scores = [rep.form_score for rep in self.session.reps_data if rep.form_score]
        avg_form_score = np.mean(form_scores) if form_scores else 0
        
        return {
            "exercise_type": self.exercise_type.value,
            "total_reps": self.session.total_reps,
            "session_duration": total_duration,
            "average_confidence": avg_confidence,
            "average_rep_duration": avg_rep_duration,
            "average_range_of_motion": avg_range_of_motion,
            "average_form_score": avg_form_score,
            "is_calibrated": self.is_calibrated,
            "form_feedback_count": len(set(self.session.form_feedback))
        }
    
    def reset_session(self):
        """Reset the rep counting session"""
        self.session = RepCountSession(
            exercise_type=self.exercise_type,
            start_time=datetime.now()
        )
        self.pose_history.clear()
        self.angle_history.clear()
        self.current_rep_start = None
        self.last_phase = RepPhase.UNKNOWN

# Utility functions
def create_rep_counter(exercise_name: str) -> RepCounter:
    """Create a rep counter for the specified exercise"""
    
    exercise_map = {
        "push_ups": ExerciseType.PUSH_UPS,
        "squats": ExerciseType.SQUATS,
        "bicep_curls": ExerciseType.BICEP_CURLS,
        "shoulder_press": ExerciseType.SHOULDER_PRESS,
        "lunges": ExerciseType.LUNGES,
        "jumping_jacks": ExerciseType.JUMPING_JACKS,
        "burpees": ExerciseType.BURPEES,
        "pull_ups": ExerciseType.PULL_UPS,
        "bench_press": ExerciseType.BENCH_PRESS,
        "deadlifts": ExerciseType.DEADLIFTS
    }
    
    exercise_type = exercise_map.get(exercise_name.lower(), ExerciseType.PUSH_UPS)
    return RepCounter(exercise_type)

# Example usage and testing
if __name__ == "__main__":
    # Test rep counter with mock data
    from models.pose_estimator import create_pose_estimator
    
    print("🏋️ Testing Rep Counter...")
    
    # Create rep counter
    counter = create_rep_counter("push_ups")
    
    # Create pose estimator for mock data
    estimator = create_pose_estimator("placeholder")
    
    # Simulate some poses
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    print("Simulating push-up reps...")
    for i in range(20):
        pose = estimator.estimate_pose(test_frame)
        if pose:
            result = counter.process_pose(pose)
            if result["rep_completed"]:
                print(f"Rep {result['total_reps']} - Confidence: {result['confidence']:.2f}")
    
    # Get session summary
    summary = counter.get_session_summary()
    print(f"\n📊 Session Summary:")
    print(f"   Exercise: {summary['exercise_type']}")
    print(f"   Total Reps: {summary['total_reps']}")
    print(f"   Average Confidence: {summary['average_confidence']:.2f}")
    print(f"   Session Duration: {summary['session_duration']:.1f}s")
    
    print("✅ Rep counter test completed!")