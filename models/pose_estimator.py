"""
Pose Estimation Framework for AI Fitness Coach

Provides a flexible framework for pose estimation that can work with
different backends (MediaPipe/BlazePose, OpenPose, or placeholder).
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import json
import os

class PoseBackend(Enum):
    """Available pose estimation backends"""
    MEDIAPIPE = "mediapipe"
    OPENCV_DNN = "opencv_dnn"
    PLACEHOLDER = "placeholder"

@dataclass
class PoseKeypoint:
    """Individual pose keypoint"""
    x: float
    y: float
    z: Optional[float] = None
    confidence: float = 0.0
    name: str = ""

@dataclass
class PoseEstimation:
    """Complete pose estimation result"""
    keypoints: List[PoseKeypoint]
    confidence: float
    timestamp: str
    frame_width: int
    frame_height: int

class PoseEstimator:
    """
    Main pose estimation class with multiple backend support
    """
    
    def __init__(self, backend: PoseBackend = PoseBackend.PLACEHOLDER):
        self.backend = backend
        self.model = None
        self.is_initialized = False
        
        # Standard pose keypoint names (MediaPipe/BlazePose format)
        self.keypoint_names = [
            "nose", "left_eye_inner", "left_eye", "left_eye_outer",
            "right_eye_inner", "right_eye", "right_eye_outer",
            "left_ear", "right_ear", "mouth_left", "mouth_right",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_pinky", "right_pinky",
            "left_index", "right_index", "left_thumb", "right_thumb",
            "left_hip", "right_hip", "left_knee", "right_knee",
            "left_ankle", "right_ankle", "left_heel", "right_heel",
            "left_foot_index", "right_foot_index"
        ]
        
        self.initialize_backend()
    
    def initialize_backend(self):
        """Initialize the selected pose estimation backend"""
        
        if self.backend == PoseBackend.MEDIAPIPE:
            try:
                import mediapipe as mp
                self.mp_pose = mp.solutions.pose
                self.mp_drawing = mp.solutions.drawing_utils
                self.model = self.mp_pose.Pose(
                    static_image_mode=False,
                    model_complexity=1,
                    enable_segmentation=False,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.is_initialized = True
                print("✅ MediaPipe pose estimation initialized")
                
            except ImportError:
                print("⚠️  MediaPipe not available, falling back to placeholder")
                self.backend = PoseBackend.PLACEHOLDER
                self.initialize_placeholder()
                
        elif self.backend == PoseBackend.OPENCV_DNN:
            try:
                # Placeholder for OpenCV DNN pose estimation
                # This would load a pre-trained pose estimation model
                self.initialize_opencv_pose()
                
            except Exception as e:
                print(f"⚠️  OpenCV DNN pose failed: {e}, falling back to placeholder")
                self.backend = PoseBackend.PLACEHOLDER
                self.initialize_placeholder()
                
        else:
            self.initialize_placeholder()
    
    def initialize_opencv_pose(self):
        """Initialize OpenCV DNN-based pose estimation"""
        # This is a placeholder for OpenCV DNN implementation
        # In practice, you'd load a pre-trained model like OpenPose
        print("⚠️  OpenCV DNN pose estimation not yet implemented")
        self.backend = PoseBackend.PLACEHOLDER
        self.initialize_placeholder()
    
    def initialize_placeholder(self):
        """Initialize placeholder pose estimation for testing"""
        self.backend = PoseBackend.PLACEHOLDER
        self.is_initialized = True
        print("ℹ️  Using placeholder pose estimation for testing")
    
    def estimate_pose(self, frame: np.ndarray) -> Optional[PoseEstimation]:
        """
        Estimate pose from a video frame
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            PoseEstimation object or None if no pose detected
        """
        
        if not self.is_initialized:
            return None
        
        height, width = frame.shape[:2]
        
        if self.backend == PoseBackend.MEDIAPIPE:
            return self._estimate_mediapipe(frame, width, height)
        elif self.backend == PoseBackend.OPENCV_DNN:
            return self._estimate_opencv_dnn(frame, width, height)
        else:
            return self._estimate_placeholder(frame, width, height)
    
    def _estimate_mediapipe(self, frame: np.ndarray, width: int, height: int) -> Optional[PoseEstimation]:
        """MediaPipe pose estimation"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.model.process(rgb_frame)
            
            if results.pose_landmarks:
                keypoints = []
                for i, landmark in enumerate(results.pose_landmarks.landmark):
                    keypoint = PoseKeypoint(
                        x=landmark.x * width,
                        y=landmark.y * height,
                        z=landmark.z,
                        confidence=landmark.visibility,
                        name=self.keypoint_names[i] if i < len(self.keypoint_names) else f"point_{i}"
                    )
                    keypoints.append(keypoint)
                
                # Calculate overall confidence
                avg_confidence = np.mean([kp.confidence for kp in keypoints])
                
                return PoseEstimation(
                    keypoints=keypoints,
                    confidence=avg_confidence,
                    timestamp=str(np.datetime64('now')),
                    frame_width=width,
                    frame_height=height
                )
                
        except Exception as e:
            print(f"MediaPipe pose estimation error: {e}")
            
        return None
    
    def _estimate_opencv_dnn(self, frame: np.ndarray, width: int, height: int) -> Optional[PoseEstimation]:
        """OpenCV DNN pose estimation (placeholder)"""
        # This would implement OpenCV DNN-based pose estimation
        return None
    
    def _estimate_placeholder(self, frame: np.ndarray, width: int, height: int) -> Optional[PoseEstimation]:
        """Placeholder pose estimation for testing"""
        # Generate fake pose data for testing
        keypoints = []
        
        # Create some reasonable mock keypoints
        mock_positions = [
            (width * 0.5, height * 0.1),   # nose
            (width * 0.45, height * 0.08), # left_eye_inner
            (width * 0.47, height * 0.08), # left_eye
            (width * 0.49, height * 0.08), # left_eye_outer
            (width * 0.55, height * 0.08), # right_eye_inner
            (width * 0.53, height * 0.08), # right_eye
            (width * 0.51, height * 0.08), # right_eye_outer
            (width * 0.42, height * 0.12), # left_ear
            (width * 0.58, height * 0.12), # right_ear
            (width * 0.48, height * 0.15), # mouth_left
            (width * 0.52, height * 0.15), # mouth_right
            (width * 0.35, height * 0.25), # left_shoulder
            (width * 0.65, height * 0.25), # right_shoulder
            (width * 0.25, height * 0.35), # left_elbow
            (width * 0.75, height * 0.35), # right_elbow
            (width * 0.20, height * 0.45), # left_wrist
            (width * 0.80, height * 0.45), # right_wrist
        ]
        
        for i, (x, y) in enumerate(mock_positions):
            if i < len(self.keypoint_names):
                keypoint = PoseKeypoint(
                    x=x + np.random.normal(0, 5),  # Add some noise
                    y=y + np.random.normal(0, 5),
                    z=0.0,
                    confidence=0.8 + np.random.normal(0, 0.1),
                    name=self.keypoint_names[i]
                )
                keypoints.append(keypoint)
        
        return PoseEstimation(
            keypoints=keypoints,
            confidence=0.85,
            timestamp=str(np.datetime64('now')),
            frame_width=width,
            frame_height=height
        )
    
    def draw_pose(self, frame: np.ndarray, pose: PoseEstimation) -> np.ndarray:
        """
        Draw pose keypoints and connections on frame
        
        Args:
            frame: Input frame
            pose: PoseEstimation object
            
        Returns:
            Frame with pose overlay
        """
        
        if not pose or not pose.keypoints:
            return frame
        
        # Draw keypoints
        for keypoint in pose.keypoints:
            if keypoint.confidence > 0.5:  # Only draw confident keypoints
                center = (int(keypoint.x), int(keypoint.y))
                
                # Color based on confidence
                confidence_color = int(255 * keypoint.confidence)
                color = (0, confidence_color, 255 - confidence_color)
                
                cv2.circle(frame, center, 5, color, -1)
                
                # Add keypoint name (for debugging)
                if keypoint.name:
                    cv2.putText(frame, keypoint.name[:4], 
                              (center[0] + 10, center[1]), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        
        # Draw pose connections (simplified skeleton)
        self._draw_pose_connections(frame, pose)
        
        # Add confidence score
        cv2.putText(frame, f"Confidence: {pose.confidence:.2f}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame
    
    def _draw_pose_connections(self, frame: np.ndarray, pose: PoseEstimation):
        """Draw connections between pose keypoints"""
        
        # Define pose connections (simplified)
        connections = [
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"),
            ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"),
            ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            ("left_hip", "left_knee"),
            ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"),
            ("right_knee", "right_ankle"),
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
                
                cv2.line(frame, start_point, end_point, (255, 255, 255), 2)
    
    def get_pose_angles(self, pose: PoseEstimation) -> Dict[str, float]:
        """
        Calculate key body angles from pose
        
        Args:
            pose: PoseEstimation object
            
        Returns:
            Dictionary of body angles in degrees
        """
        
        if not pose or len(pose.keypoints) < 10:
            return {}
        
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
            
            # Torso angle (shoulder to hip line vs vertical)
            if all(name in kp_dict for name in ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]):
                shoulder_center = self._midpoint(kp_dict["left_shoulder"], kp_dict["right_shoulder"])
                hip_center = self._midpoint(kp_dict["left_hip"], kp_dict["right_hip"])
                
                # Calculate torso lean
                torso_vector = (hip_center.x - shoulder_center.x, hip_center.y - shoulder_center.y)
                vertical_vector = (0, 1)
                angles["torso_lean"] = self._vector_angle(torso_vector, vertical_vector)
                
        except Exception as e:
            print(f"Error calculating angles: {e}")
        
        return angles
    
    def _calculate_angle(self, p1: PoseKeypoint, p2: PoseKeypoint, p3: PoseKeypoint) -> float:
        """Calculate angle between three points (p2 is the vertex)"""
        
        # Create vectors
        v1 = (p1.x - p2.x, p1.y - p2.y)
        v2 = (p3.x - p2.x, p3.y - p2.y)
        
        return self._vector_angle(v1, v2)
    
    def _vector_angle(self, v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
        """Calculate angle between two vectors in degrees"""
        
        # Calculate dot product and magnitudes
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        magnitude1 = np.sqrt(v1[0]**2 + v1[1]**2)
        magnitude2 = np.sqrt(v2[0]**2 + v2[1]**2)
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate angle
        cos_angle = dot_product / (magnitude1 * magnitude2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Handle floating point errors
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def _midpoint(self, p1: PoseKeypoint, p2: PoseKeypoint) -> PoseKeypoint:
        """Calculate midpoint between two keypoints"""
        return PoseKeypoint(
            x=(p1.x + p2.x) / 2,
            y=(p1.y + p2.y) / 2,
            z=(p1.z + p2.z) / 2 if p1.z and p2.z else 0,
            confidence=(p1.confidence + p2.confidence) / 2
        )

# Utility functions
def create_pose_estimator(preferred_backend: str = "mediapipe") -> PoseEstimator:
    """Create pose estimator with fallback support"""
    
    backend_map = {
        "mediapipe": PoseBackend.MEDIAPIPE,
        "opencv": PoseBackend.OPENCV_DNN,
        "placeholder": PoseBackend.PLACEHOLDER
    }
    
    backend = backend_map.get(preferred_backend, PoseBackend.PLACEHOLDER)
    return PoseEstimator(backend)

def test_pose_estimation():
    """Test pose estimation with webcam or sample image"""
    
    estimator = create_pose_estimator("mediapipe")
    
    # Try to open webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("⚠️  No webcam available, creating test frame")
        # Create a test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(test_frame, "Test Frame - No Webcam", 
                   (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        pose = estimator.estimate_pose(test_frame)
        if pose:
            result_frame = estimator.draw_pose(test_frame, pose)
            print(f"✅ Pose estimated with {len(pose.keypoints)} keypoints")
            print(f"   Confidence: {pose.confidence:.2f}")
            
            # Save test result
            cv2.imwrite("pose_test_result.jpg", result_frame)
            print("   Test result saved as pose_test_result.jpg")
        
        return True
    
    print("🎥 Webcam opened - press 'q' to quit, 's' to save frame")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Estimate pose
        pose = estimator.estimate_pose(frame)
        
        if pose:
            # Draw pose on frame
            result_frame = estimator.draw_pose(frame, pose)
            
            # Calculate and display angles
            angles = estimator.get_pose_angles(pose)
            y_offset = 60
            for angle_name, angle_value in angles.items():
                cv2.putText(result_frame, f"{angle_name}: {angle_value:.1f}°", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y_offset += 20
            
            cv2.imshow("Pose Estimation", result_frame)
        else:
            cv2.imshow("Pose Estimation", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s') and pose:
            filename = f"pose_frame_{frame_count:04d}.jpg"
            cv2.imwrite(filename, estimator.draw_pose(frame, pose))
            print(f"Saved {filename}")
            frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Pose estimation test completed")
    return True

if __name__ == "__main__":
    # Test pose estimation
    test_pose_estimation()