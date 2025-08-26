"""
Visual Aide Utilities for AI Fitness Coach

Provides visual feedback overlays, pose visualization, and real-time
form correction displays for the fitness coaching interface.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import math

# Import project modules (with fallback for testing)
try:
    from models.pose_estimator import PoseEstimation, PoseKeypoint
    from utils.rep_counter import RepCountSession, RepPhase, ExerciseType
except ImportError:
    # Fallback for testing
    class PoseEstimation:
        def __init__(self):
            self.keypoints = []
            self.confidence = 0.0
    
    class PoseKeypoint:
        def __init__(self, x=0, y=0, confidence=0.0, name=""):
            self.x = x
            self.y = y
            self.confidence = confidence
            self.name = name
    
    class RepPhase(Enum):
        BOTTOM = "bottom"
        TOP = "top"
        TRANSITION_UP = "transition_up"
        TRANSITION_DOWN = "transition_down"

class OverlayType(Enum):
    """Types of visual overlays"""
    POSE_SKELETON = "pose_skeleton"
    REP_COUNTER = "rep_counter"
    FORM_FEEDBACK = "form_feedback"
    RANGE_OF_MOTION = "range_of_motion"
    CONFIDENCE_METER = "confidence_meter"
    PHASE_INDICATOR = "phase_indicator"
    PROGRESS_BAR = "progress_bar"

class FeedbackLevel(Enum):
    """Levels of feedback severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

@dataclass
class VisualFeedback:
    """Visual feedback message"""
    message: str
    level: FeedbackLevel
    position: Tuple[int, int]
    duration: float = 3.0  # seconds
    timestamp: float = 0.0

class ColorScheme:
    """Color scheme for visual elements"""
    
    # Main colors (BGR format for OpenCV)
    PRIMARY = (255, 140, 0)      # Orange
    SUCCESS = (0, 255, 0)        # Green
    WARNING = (0, 255, 255)      # Yellow
    ERROR = (0, 0, 255)          # Red
    INFO = (255, 255, 255)       # White
    
    # Pose colors
    POSE_JOINT = (0, 255, 255)   # Yellow
    POSE_BONE = (255, 255, 255)  # White
    POSE_CONFIDENT = (0, 255, 0) # Green
    POSE_UNCERTAIN = (0, 165, 255) # Orange
    
    # UI colors
    BACKGROUND = (40, 40, 40)    # Dark gray
    TEXT = (255, 255, 255)       # White
    ACCENT = (255, 140, 0)       # Orange

class VisualAide:
    """
    Main visual aide class for fitness coaching overlays
    """
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.feedback_messages = []
        self.colors = ColorScheme()
        
        # Font settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.font_thickness = 2
        
        # UI element positions
        self.ui_positions = {
            "rep_counter": (20, 50),
            "phase_indicator": (20, 100),
            "confidence_meter": (frame_width - 200, 50),
            "form_feedback": (20, frame_height - 100),
            "progress_bar": (50, frame_height - 50)
        }
    
    def draw_pose_overlay(self, frame: np.ndarray, pose: PoseEstimation, show_skeleton: bool = True) -> np.ndarray:
        """
        Draw pose estimation overlay on frame
        
        Args:
            frame: Input video frame
            pose: PoseEstimation object
            show_skeleton: Whether to draw skeleton connections
            
        Returns:
            Frame with pose overlay
        """
        
        if not pose or not pose.keypoints:
            return frame
        
        # Draw keypoints
        for keypoint in pose.keypoints:
            if keypoint.confidence > 0.5:
                center = (int(keypoint.x), int(keypoint.y))
                
                # Color based on confidence
                if keypoint.confidence > 0.8:
                    color = self.colors.POSE_CONFIDENT
                else:
                    color = self.colors.POSE_UNCERTAIN
                
                # Draw keypoint
                cv2.circle(frame, center, 6, color, -1)
                cv2.circle(frame, center, 6, (0, 0, 0), 2)  # Black border
                
                # Add keypoint label for debugging
                if keypoint.name:
                    label_pos = (center[0] + 10, center[1] - 10)
                    cv2.putText(frame, keypoint.name[:4], label_pos, 
                              self.font, 0.4, color, 1)
        
        # Draw skeleton connections
        if show_skeleton:
            frame = self._draw_pose_skeleton(frame, pose)
        
        return frame
    
    def _draw_pose_skeleton(self, frame: np.ndarray, pose: PoseEstimation) -> np.ndarray:
        """Draw skeleton connections between pose keypoints"""
        
        # Define pose connections
        connections = [
            # Head
            ("nose", "left_eye"), ("nose", "right_eye"),
            ("left_eye", "left_ear"), ("right_eye", "right_ear"),
            
            # Arms
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            
            # Torso
            ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            
            # Legs
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
        ]
        
        # Create keypoint lookup
        kp_dict = {kp.name: kp for kp in pose.keypoints if kp.confidence > 0.5}
        
        # Draw connections
        for start_name, end_name in connections:
            if start_name in kp_dict and end_name in kp_dict:
                start_kp = kp_dict[start_name]
                end_kp = kp_dict[end_name]
                
                start_point = (int(start_kp.x), int(start_kp.y))
                end_point = (int(end_kp.x), int(end_kp.y))
                
                # Line thickness based on confidence
                avg_confidence = (start_kp.confidence + end_kp.confidence) / 2
                thickness = int(3 * avg_confidence)
                
                cv2.line(frame, start_point, end_point, self.colors.POSE_BONE, thickness)
        
        return frame
    
    def draw_rep_counter(self, frame: np.ndarray, rep_count: int, target_reps: Optional[int] = None) -> np.ndarray:
        """Draw rep counter display"""
        
        pos = self.ui_positions["rep_counter"]
        
        # Draw background
        bg_rect = (pos[0] - 10, pos[1] - 35, 120, 50)
        cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                     (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                     self.colors.BACKGROUND, -1)
        cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                     (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                     self.colors.ACCENT, 2)
        
        # Draw rep count
        if target_reps:
            text = f"Reps: {rep_count}/{target_reps}"
        else:
            text = f"Reps: {rep_count}"
        
        cv2.putText(frame, text, pos, self.font, self.font_scale, 
                   self.colors.TEXT, self.font_thickness)
        
        return frame
    
    def draw_phase_indicator(self, frame: np.ndarray, current_phase: RepPhase) -> np.ndarray:
        """Draw current exercise phase indicator"""
        
        pos = self.ui_positions["phase_indicator"]
        
        # Phase colors
        phase_colors = {
            RepPhase.BOTTOM: self.colors.ERROR,
            RepPhase.TOP: self.colors.SUCCESS,
            RepPhase.TRANSITION_UP: self.colors.WARNING,
            RepPhase.TRANSITION_DOWN: self.colors.WARNING,
        }
        
        # Get phase display name
        phase_names = {
            RepPhase.BOTTOM: "BOTTOM",
            RepPhase.TOP: "TOP",
            RepPhase.TRANSITION_UP: "UP",
            RepPhase.TRANSITION_DOWN: "DOWN",
        }
        
        phase_name = phase_names.get(current_phase, "UNKNOWN")
        phase_color = phase_colors.get(current_phase, self.colors.INFO)
        
        # Draw background
        text_size = cv2.getTextSize(phase_name, self.font, self.font_scale, self.font_thickness)[0]
        bg_rect = (pos[0] - 10, pos[1] - text_size[1] - 10, text_size[0] + 20, text_size[1] + 20)
        
        cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                     (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                     self.colors.BACKGROUND, -1)
        cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                     (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                     phase_color, 2)
        
        # Draw phase text
        cv2.putText(frame, phase_name, pos, self.font, self.font_scale, 
                   phase_color, self.font_thickness)
        
        return frame
    
    def draw_confidence_meter(self, frame: np.ndarray, confidence: float) -> np.ndarray:
        """Draw confidence meter"""
        
        pos = self.ui_positions["confidence_meter"]
        meter_width = 150
        meter_height = 20
        
        # Draw meter background
        cv2.rectangle(frame, pos, (pos[0] + meter_width, pos[1] + meter_height), 
                     self.colors.BACKGROUND, -1)
        cv2.rectangle(frame, pos, (pos[0] + meter_width, pos[1] + meter_height), 
                     self.colors.TEXT, 2)
        
        # Draw confidence fill
        fill_width = int(meter_width * confidence)
        if confidence > 0.8:
            fill_color = self.colors.SUCCESS
        elif confidence > 0.5:
            fill_color = self.colors.WARNING
        else:
            fill_color = self.colors.ERROR
        
        if fill_width > 0:
            cv2.rectangle(frame, (pos[0] + 2, pos[1] + 2), 
                         (pos[0] + fill_width - 2, pos[1] + meter_height - 2), 
                         fill_color, -1)
        
        # Draw confidence text
        conf_text = f"Confidence: {confidence:.1%}"
        text_pos = (pos[0], pos[1] - 10)
        cv2.putText(frame, conf_text, text_pos, self.font, 0.5, 
                   self.colors.TEXT, 1)
        
        return frame
    
    def draw_form_feedback(self, frame: np.ndarray, feedback_messages: List[str]) -> np.ndarray:
        """Draw form feedback messages"""
        
        if not feedback_messages:
            return frame
        
        base_pos = self.ui_positions["form_feedback"]
        
        for i, message in enumerate(feedback_messages[-3:]):  # Show last 3 messages
            pos = (base_pos[0], base_pos[1] + i * 25)
            
            # Draw message background
            text_size = cv2.getTextSize(message, self.font, 0.6, 1)[0]
            bg_rect = (pos[0] - 5, pos[1] - text_size[1] - 5, text_size[0] + 10, text_size[1] + 10)
            
            cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                         (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                         self.colors.WARNING, -1)
            
            # Draw message text
            cv2.putText(frame, message, pos, self.font, 0.6, 
                       self.colors.BACKGROUND, 1)
        
        return frame
    
    def draw_range_of_motion_arc(self, frame: np.ndarray, center: Tuple[int, int], 
                                current_angle: float, min_angle: float, max_angle: float) -> np.ndarray:
        """Draw range of motion arc visualization"""
        
        radius = 50
        
        # Draw full range arc (gray)
        cv2.ellipse(frame, center, (radius, radius), 0, 
                   min_angle, max_angle, self.colors.BACKGROUND, 3)
        
        # Draw current position
        angle_rad = math.radians(current_angle)
        end_point = (
            int(center[0] + radius * math.cos(angle_rad)),
            int(center[1] + radius * math.sin(angle_rad))
        )
        cv2.line(frame, center, end_point, self.colors.ACCENT, 3)
        
        # Draw min/max markers
        min_rad = math.radians(min_angle)
        max_rad = math.radians(max_angle)
        
        min_point = (
            int(center[0] + radius * math.cos(min_rad)),
            int(center[1] + radius * math.sin(min_rad))
        )
        max_point = (
            int(center[0] + radius * math.cos(max_rad)),
            int(center[1] + radius * math.sin(max_rad))
        )
        
        cv2.circle(frame, min_point, 5, self.colors.ERROR, -1)
        cv2.circle(frame, max_point, 5, self.colors.SUCCESS, -1)
        
        return frame
    
    def draw_progress_bar(self, frame: np.ndarray, current: int, target: int) -> np.ndarray:
        """Draw workout progress bar"""
        
        if target <= 0:
            return frame
        
        pos = self.ui_positions["progress_bar"]
        bar_width = self.frame_width - 100
        bar_height = 15
        
        # Calculate progress
        progress = min(current / target, 1.0)
        
        # Draw background
        cv2.rectangle(frame, pos, (pos[0] + bar_width, pos[1] + bar_height), 
                     self.colors.BACKGROUND, -1)
        cv2.rectangle(frame, pos, (pos[0] + bar_width, pos[1] + bar_height), 
                     self.colors.TEXT, 2)
        
        # Draw progress fill
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            cv2.rectangle(frame, (pos[0] + 2, pos[1] + 2), 
                         (pos[0] + fill_width - 2, pos[1] + bar_height - 2), 
                         self.colors.SUCCESS, -1)
        
        # Draw progress text
        progress_text = f"Progress: {current}/{target} ({progress:.1%})"
        text_pos = (pos[0], pos[1] - 10)
        cv2.putText(frame, progress_text, text_pos, self.font, 0.6, 
                   self.colors.TEXT, 1)
        
        return frame
    
    def add_feedback_message(self, message: str, level: FeedbackLevel = FeedbackLevel.INFO,
                           position: Optional[Tuple[int, int]] = None):
        """Add a timed feedback message"""
        
        if position is None:
            position = (20, self.frame_height - 150 - len(self.feedback_messages) * 30)
        
        feedback = VisualFeedback(
            message=message,
            level=level,
            position=position,
            timestamp=cv2.getTickCount() / cv2.getTickFrequency()
        )
        
        self.feedback_messages.append(feedback)
    
    def draw_feedback_messages(self, frame: np.ndarray) -> np.ndarray:
        """Draw all active feedback messages"""
        
        current_time = cv2.getTickCount() / cv2.getTickFrequency()
        
        # Remove expired messages
        self.feedback_messages = [
            msg for msg in self.feedback_messages 
            if current_time - msg.timestamp < msg.duration
        ]
        
        # Draw remaining messages
        for feedback in self.feedback_messages:
            # Color based on level
            colors = {
                FeedbackLevel.INFO: self.colors.INFO,
                FeedbackLevel.WARNING: self.colors.WARNING,
                FeedbackLevel.ERROR: self.colors.ERROR,
                FeedbackLevel.SUCCESS: self.colors.SUCCESS
            }
            
            color = colors.get(feedback.level, self.colors.INFO)
            
            # Draw background
            text_size = cv2.getTextSize(feedback.message, self.font, 0.6, 1)[0]
            bg_rect = (feedback.position[0] - 5, feedback.position[1] - text_size[1] - 5, 
                      text_size[0] + 10, text_size[1] + 10)
            
            cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                         (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                         self.colors.BACKGROUND, -1)
            cv2.rectangle(frame, (bg_rect[0], bg_rect[1]), 
                         (bg_rect[0] + bg_rect[2], bg_rect[1] + bg_rect[3]), 
                         color, 2)
            
            # Draw message
            cv2.putText(frame, feedback.message, feedback.position, 
                       self.font, 0.6, color, 1)
        
        return frame
    
    def create_workout_overlay(self, frame: np.ndarray, **kwargs) -> np.ndarray:
        """Create complete workout overlay with all elements"""
        
        # Extract parameters
        pose = kwargs.get('pose')
        rep_count = kwargs.get('rep_count', 0)
        target_reps = kwargs.get('target_reps')
        current_phase = kwargs.get('current_phase')
        confidence = kwargs.get('confidence', 0.0)
        form_feedback = kwargs.get('form_feedback', [])
        current_angle = kwargs.get('current_angle')
        angle_range = kwargs.get('angle_range')
        
        # Draw pose overlay
        if pose:
            frame = self.draw_pose_overlay(frame, pose)
        
        # Draw UI elements
        if rep_count is not None:
            frame = self.draw_rep_counter(frame, rep_count, target_reps)
        
        if current_phase:
            frame = self.draw_phase_indicator(frame, current_phase)
        
        if confidence is not None:
            frame = self.draw_confidence_meter(frame, confidence)
        
        if form_feedback:
            frame = self.draw_form_feedback(frame, form_feedback)
        
        if target_reps and rep_count is not None:
            frame = self.draw_progress_bar(frame, rep_count, target_reps)
        
        # Draw feedback messages
        frame = self.draw_feedback_messages(frame)
        
        return frame

# Utility functions
def create_visual_aide(width: int = 640, height: int = 480) -> VisualAide:
    """Create a visual aide instance"""
    return VisualAide(width, height)

def test_visual_aide():
    """Test visual aide with mock data"""
    
    print("🎨 Testing Visual Aide...")
    
    # Create visual aide
    aide = create_visual_aide(640, 480)
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add some test overlays
    frame = aide.draw_rep_counter(frame, 5, 10)
    frame = aide.draw_phase_indicator(frame, RepPhase.BOTTOM)
    frame = aide.draw_confidence_meter(frame, 0.85)
    frame = aide.draw_form_feedback(frame, ["Keep your back straight", "Lower more slowly"])
    frame = aide.draw_progress_bar(frame, 5, 10)
    
    # Add feedback message
    aide.add_feedback_message("Great form!", FeedbackLevel.SUCCESS)
    frame = aide.draw_feedback_messages(frame)
    
    # Save test image
    cv2.imwrite("visual_aide_test.jpg", frame)
    print("✅ Visual aide test image saved as visual_aide_test.jpg")
    
    return True

if __name__ == "__main__":
    test_visual_aide()