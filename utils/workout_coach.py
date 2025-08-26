"""
Integrated Workout Coach for AI Fitness Coach

Combines pose estimation, rep counting, voice feedback, and visual overlays
into a complete real-time fitness coaching experience.
"""

import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

# Import project modules (with fallback for testing)
try:
    from models.pose_estimator import create_pose_estimator, PoseEstimation
    from utils.rep_counter import create_rep_counter, ExerciseType, RepPhase
    from utils.voice_output import VoiceOutputService, CoachingTone
    from utils.visual_aide import create_visual_aide, FeedbackLevel
    from utils.logger import FitnessLogger, WorkoutSession, Exercise, ExerciseSet, WorkoutType, ExerciseCategory
except ImportError:
    print("Warning: Some imports failed - running in limited mode")
    # Create dummy classes for type hints
    PoseEstimation = Any

@dataclass
class WorkoutConfig:
    """Configuration for a workout session"""
    exercise_type: str = "push_ups"
    target_reps: int = 10
    target_sets: int = 3
    rest_time_seconds: int = 60
    enable_voice: bool = True
    enable_visual: bool = True
    show_pose_skeleton: bool = True
    voice_frequency: str = "every_rep"  # "every_rep", "every_5", "milestones_only"

class WorkoutCoach:
    """
    Integrated workout coaching system that provides real-time feedback
    during exercise sessions.
    """
    
    def __init__(self, config: WorkoutConfig):
        self.config = config
        self.is_active = False
        self.current_set = 1
        
        # Initialize components
        self.pose_estimator = create_pose_estimator("placeholder")  # Will try MediaPipe first
        self.rep_counter = create_rep_counter(config.exercise_type)
        
        if config.enable_voice:
            self.voice_service = VoiceOutputService()
            self.voice_queue = queue.Queue()
            self.voice_thread = None
        
        if config.enable_visual:
            self.visual_aide = create_visual_aide()
        
        # Workout tracking
        self.workout_start_time = None
        self.set_start_time = None
        self.rest_start_time = None
        self.is_resting = False
        
        # Feedback tracking
        self.last_rep_count = 0
        self.last_voice_feedback = 0
        self.form_feedback_history = []
        
    def start_workout(self) -> Dict[str, Any]:
        """Start a new workout session"""
        
        self.is_active = True
        self.workout_start_time = datetime.now()
        self.set_start_time = datetime.now()
        self.current_set = 1
        self.is_resting = False
        
        # Start voice thread if enabled
        if self.config.enable_voice and self.voice_thread is None:
            self.voice_thread = threading.Thread(target=self._voice_worker, daemon=True)
            self.voice_thread.start()
        
        # Reset rep counter
        self.rep_counter.reset_session()
        
        # Welcome message
        if self.config.enable_voice:
            self._queue_voice_feedback(
                f"Starting {self.config.exercise_type.replace('_', ' ')} workout. "
                f"Let's do {self.config.target_sets} sets of {self.config.target_reps} reps!",
                CoachingTone.MOTIVATIONAL
            )
        
        print(f"🏋️ Workout started: {self.config.exercise_type}")
        print(f"   Target: {self.config.target_sets} sets x {self.config.target_reps} reps")
        
        return {
            "status": "started",
            "exercise": self.config.exercise_type,
            "target_sets": self.config.target_sets,
            "target_reps": self.config.target_reps,
            "start_time": self.workout_start_time.isoformat()
        }
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process a video frame and return annotated frame with coaching data
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (annotated_frame, coaching_data)
        """
        
        if not self.is_active:
            return frame, {"status": "inactive"}
        
        # Estimate pose
        pose = self.pose_estimator.estimate_pose(frame)
        
        if pose is None:
            return frame, {"status": "no_pose_detected"}
        
        # Process rep counting (if not resting)
        rep_data = {}
        if not self.is_resting:
            rep_data = self.rep_counter.process_pose(pose)
            
            # Check for new reps
            current_reps = rep_data.get("total_reps", 0)
            if current_reps > self.last_rep_count:
                self._handle_new_rep(current_reps, rep_data)
                self.last_rep_count = current_reps
            
            # Check for set completion
            if current_reps >= self.config.target_reps and not self.is_resting:
                self._complete_set()
        
        # Handle rest periods
        if self.is_resting:
            self._handle_rest_period()
        
        # Generate coaching feedback
        coaching_data = self._generate_coaching_data(pose, rep_data)
        
        # Create visual overlay
        if self.config.enable_visual:
            frame = self._create_visual_overlay(frame, pose, rep_data, coaching_data)
        
        return frame, coaching_data
    
    def _handle_new_rep(self, rep_count: int, rep_data: Dict[str, Any]):
        """Handle completion of a new repetition"""
        
        print(f"✅ Rep {rep_count} completed in set {self.current_set}")
        
        # Voice feedback based on configuration
        if self.config.enable_voice:
            if self.config.voice_frequency == "every_rep":
                if rep_count == self.config.target_reps:
                    self._queue_voice_feedback("Perfect! Set complete!", CoachingTone.CELEBRATION)
                elif rep_count == self.config.target_reps - 1:
                    self._queue_voice_feedback("One more! You've got this!", CoachingTone.MOTIVATIONAL)
                elif rep_count % 5 == 0:
                    self._queue_voice_feedback(f"{rep_count} reps! Keep going!", CoachingTone.ENCOURAGING)
                else:
                    # Provide rep count every few reps
                    if rep_count % 3 == 0:
                        remaining = self.config.target_reps - rep_count
                        self._queue_voice_feedback(f"{remaining} more!", CoachingTone.ENCOURAGING)
            
            elif self.config.voice_frequency == "every_5" and rep_count % 5 == 0:
                remaining = self.config.target_reps - rep_count
                if remaining > 0:
                    self._queue_voice_feedback(f"{rep_count} done, {remaining} to go!", CoachingTone.ENCOURAGING)
        
        # Form feedback
        form_feedback = rep_data.get("form_feedback", [])
        if form_feedback and self.config.enable_voice:
            # Queue form correction (but don't overwhelm)
            if len(self.form_feedback_history) == 0 or form_feedback[0] not in self.form_feedback_history[-3:]:
                self._queue_voice_feedback(form_feedback[0], CoachingTone.CORRECTIVE)
                self.form_feedback_history.append(form_feedback[0])
    
    def _complete_set(self):
        """Handle completion of a set"""
        
        print(f"🎉 Set {self.current_set} completed!")
        
        if self.current_set < self.config.target_sets:
            # Start rest period
            self.is_resting = True
            self.rest_start_time = datetime.now()
            self.current_set += 1
            
            if self.config.enable_voice:
                self._queue_voice_feedback(
                    f"Excellent! Set {self.current_set - 1} complete. "
                    f"Rest for {self.config.rest_time_seconds} seconds.",
                    CoachingTone.CELEBRATION
                )
            
            # Reset rep counter for next set
            self.rep_counter.reset_session()
            self.last_rep_count = 0
            
        else:
            # Workout complete
            self._complete_workout()
    
    def _handle_rest_period(self):
        """Handle rest period between sets"""
        
        if not self.rest_start_time:
            return
        
        elapsed_rest = (datetime.now() - self.rest_start_time).total_seconds()
        remaining_rest = max(0, self.config.rest_time_seconds - elapsed_rest)
        
        # Voice countdown at specific intervals
        if self.config.enable_voice and remaining_rest > 0:
            if remaining_rest <= 10 and int(remaining_rest) % 5 == 0:
                self._queue_voice_feedback(f"{int(remaining_rest)} seconds", CoachingTone.CALM)
            elif remaining_rest <= 5:
                self._queue_voice_feedback("Almost ready", CoachingTone.ENCOURAGING)
        
        # End rest period
        if remaining_rest <= 0:
            self.is_resting = False
            self.rest_start_time = None
            self.set_start_time = datetime.now()
            
            if self.config.enable_voice:
                self._queue_voice_feedback(
                    f"Let's go! Set {self.current_set} of {self.config.target_sets}",
                    CoachingTone.MOTIVATIONAL
                )
    
    def _complete_workout(self):
        """Handle workout completion"""
        
        self.is_active = False
        workout_duration = (datetime.now() - self.workout_start_time).total_seconds()
        
        print(f"🏆 Workout complete! Duration: {workout_duration:.1f} seconds")
        
        if self.config.enable_voice:
            self._queue_voice_feedback(
                "Outstanding work! Workout complete. You crushed it today!",
                CoachingTone.CELEBRATION
            )
        
        # Generate workout summary
        summary = self.rep_counter.get_session_summary()
        summary.update({
            "total_sets_completed": self.current_set,
            "workout_duration": workout_duration,
            "workout_complete": True
        })
        
        return summary
    
    def _generate_coaching_data(self, pose: PoseEstimation, rep_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive coaching data for the current frame"""
        
        current_time = datetime.now()
        
        # Calculate times
        if self.is_resting and self.rest_start_time:
            rest_elapsed = (current_time - self.rest_start_time).total_seconds()
            rest_remaining = max(0, self.config.rest_time_seconds - rest_elapsed)
        else:
            rest_elapsed = 0
            rest_remaining = 0
        
        if self.set_start_time:
            set_duration = (current_time - self.set_start_time).total_seconds()
        else:
            set_duration = 0
        
        if self.workout_start_time:
            workout_duration = (current_time - self.workout_start_time).total_seconds()
        else:
            workout_duration = 0
        
        return {
            "pose_confidence": pose.confidence if pose else 0.0,
            "current_set": self.current_set,
            "target_sets": self.config.target_sets,
            "current_reps": rep_data.get("total_reps", 0),
            "target_reps": self.config.target_reps,
            "current_phase": rep_data.get("current_phase", "unknown"),
            "is_resting": self.is_resting,
            "rest_remaining": rest_remaining,
            "set_duration": set_duration,
            "workout_duration": workout_duration,
            "form_feedback": rep_data.get("form_feedback", []),
            "rep_confidence": rep_data.get("confidence", 0.0),
            "primary_angle": rep_data.get("primary_angle", 0.0),
            "exercise_type": self.config.exercise_type
        }
    
    def _create_visual_overlay(self, frame: np.ndarray, pose: PoseEstimation, 
                             rep_data: Dict[str, Any], coaching_data: Dict[str, Any]) -> np.ndarray:
        """Create complete visual overlay on the frame"""
        
        if not self.config.enable_visual:
            return frame
        
        # Determine current phase
        try:
            from utils.rep_counter import RepPhase
            phase_str = rep_data.get("current_phase", "unknown")
            current_phase = RepPhase(phase_str) if phase_str != "unknown" else None
        except:
            current_phase = None
        
        # Create overlay parameters
        overlay_params = {
            "pose": pose,
            "rep_count": coaching_data["current_reps"],
            "target_reps": coaching_data["target_reps"],
            "current_phase": current_phase,
            "confidence": coaching_data["rep_confidence"],
            "form_feedback": coaching_data["form_feedback"]
        }
        
        # Add rest period info
        if self.is_resting:
            rest_text = f"REST: {int(coaching_data['rest_remaining'])}s"
            cv2.putText(frame, rest_text, (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 
                       1.0, (0, 255, 255), 2)
        
        # Add set info
        set_text = f"Set {coaching_data['current_set']}/{coaching_data['target_sets']}"
        cv2.putText(frame, set_text, (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.8, (255, 255, 255), 2)
        
        # Create full overlay
        frame = self.visual_aide.create_workout_overlay(frame, **overlay_params)
        
        return frame
    
    def _queue_voice_feedback(self, text: str, tone: CoachingTone):
        """Queue voice feedback for playback"""
        
        if self.config.enable_voice and hasattr(self, 'voice_queue'):
            self.voice_queue.put((text, tone))
    
    def _voice_worker(self):
        """Background worker for voice feedback"""
        
        while self.is_active or not self.voice_queue.empty():
            try:
                text, tone = self.voice_queue.get(timeout=1.0)
                self.voice_service.speak_coaching_cue(text, tone, play_immediately=True)
                self.voice_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Voice feedback error: {e}")
    
    def stop_workout(self) -> Dict[str, Any]:
        """Stop the current workout session"""
        
        if not self.is_active:
            return {"status": "already_stopped"}
        
        self.is_active = False
        
        if self.config.enable_voice:
            self._queue_voice_feedback("Workout stopped", CoachingTone.CALM)
        
        # Wait for voice queue to finish
        if hasattr(self, 'voice_queue'):
            self.voice_queue.join()
        
        # Generate session summary
        summary = self.rep_counter.get_session_summary()
        summary.update({
            "workout_stopped": True,
            "sets_completed": self.current_set - (1 if self.is_resting else 0),
            "final_reps": self.last_rep_count
        })
        
        print("🛑 Workout stopped")
        return summary
    
    def calibrate_exercise(self, calibration_poses: List[PoseEstimation], 
                          position_labels: List[bool]) -> Dict[str, Any]:
        """Calibrate the rep counter with user-specific range of motion"""
        
        result = self.rep_counter.calibrate(calibration_poses, position_labels)
        
        if result.get("status") == "calibrated" and self.config.enable_voice:
            self._queue_voice_feedback("Calibration complete! You're ready to start.", CoachingTone.SUCCESS)
        
        return result

# Utility functions
def create_workout_coach(exercise_type: str = "push_ups", target_reps: int = 10, 
                        target_sets: int = 3, enable_voice: bool = True) -> WorkoutCoach:
    """Create a workout coach with specified parameters"""
    
    config = WorkoutConfig(
        exercise_type=exercise_type,
        target_reps=target_reps,
        target_sets=target_sets,
        enable_voice=enable_voice,
        enable_visual=True
    )
    
    return WorkoutCoach(config)

def test_workout_coach():
    """Test the integrated workout coach system"""
    
    print("🏋️ Testing Integrated Workout Coach...")
    
    # Create workout coach
    coach = create_workout_coach("push_ups", target_reps=5, target_sets=2, enable_voice=False)
    
    # Start workout
    start_result = coach.start_workout()
    print(f"✅ Workout started: {start_result}")
    
    # Simulate some frames
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    for i in range(15):
        annotated_frame, coaching_data = coach.process_frame(test_frame)
        
        if coaching_data.get("status") != "no_pose_detected":
            print(f"Frame {i+1}: Reps={coaching_data['current_reps']}, "
                  f"Phase={coaching_data['current_phase']}, "
                  f"Set={coaching_data['current_set']}")
        
        # Simulate processing delay
        time.sleep(0.1)
    
    # Stop workout
    summary = coach.stop_workout()
    print(f"📊 Final summary: {summary}")
    
    print("✅ Workout coach test completed!")
    return True

if __name__ == "__main__":
    test_workout_coach()