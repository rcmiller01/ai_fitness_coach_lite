"""
Workout and Progress Logger for AI Fitness Coach

Provides comprehensive logging for workouts, progress tracking, and
fitness data management with JSON-based local storage.
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

class WorkoutType(Enum):
    """Types of workouts"""
    STRENGTH = "strength"
    CARDIO = "cardio"
    FLEXIBILITY = "flexibility"
    HIIT = "hiit"
    BODYWEIGHT = "bodyweight"
    SPORTS = "sports"

class ExerciseCategory(Enum):
    """Exercise categories for organization"""
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    LEGS = "legs"
    CORE = "core"
    FULL_BODY = "full_body"
    CARDIO = "cardio"

@dataclass
class ExerciseSet:
    """Individual set data"""
    reps: int
    weight: float = 0.0  # in pounds or kg
    duration: Optional[int] = None  # in seconds for time-based exercises
    rpe: Optional[int] = None  # Rate of Perceived Exertion (1-10)
    rest_time: Optional[int] = None  # rest after this set in seconds
    notes: Optional[str] = None

@dataclass
class Exercise:
    """Individual exercise data"""
    name: str
    category: ExerciseCategory
    sets: List[ExerciseSet]
    equipment: Optional[str] = None
    form_notes: Optional[str] = None
    
@dataclass
class WorkoutSession:
    """Complete workout session"""
    date: str  # ISO format
    workout_type: WorkoutType
    exercises: List[Exercise]
    duration_minutes: int
    total_volume: float = 0.0  # total weight moved
    calories_burned: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    workout_rating: Optional[int] = None  # 1-10 subjective rating
    notes: Optional[str] = None
    location: Optional[str] = None  # gym, home, outdoor

class FitnessLogger:
    """
    Comprehensive fitness logging system with progress tracking
    """
    
    def __init__(self, user_id: str = "default_user", logs_dir: str = "logs"):
        self.user_id = user_id
        self.logs_dir = logs_dir
        self.daily_logs_path = os.path.join(logs_dir, "daily_workouts")
        self.progress_path = os.path.join(logs_dir, "progress_tracking")
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.daily_logs_path, exist_ok=True)
        os.makedirs(self.progress_path, exist_ok=True)
        
    def log_workout(self, workout: WorkoutSession) -> Dict[str, Any]:
        """
        Log a complete workout session
        
        Args:
            workout: WorkoutSession object to log
            
        Returns:
            Result dictionary with status and file path
        """
        # Calculate total volume
        workout.total_volume = self._calculate_total_volume(workout)
        
        # Generate filename
        workout_date = datetime.fromisoformat(workout.date).date()
        filename = f"{workout_date}_{workout.workout_type.value}.json"
        filepath = os.path.join(self.daily_logs_path, filename)
        
        # Convert to dictionary for JSON serialization
        workout_data = {
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "workout": asdict(workout)
        }
        
        # Save workout
        with open(filepath, 'w') as f:
            json.dump(workout_data, f, indent=2, default=str)
            
        # Update progress tracking
        self._update_progress_tracking(workout)
        
        return {
            "status": "logged",
            "file_path": filepath,
            "total_volume": workout.total_volume,
            "exercise_count": len(workout.exercises)
        }
    
    def _calculate_total_volume(self, workout: WorkoutSession) -> float:
        """Calculate total volume (weight x reps) for the workout"""
        total_volume = 0.0
        for exercise in workout.exercises:
            for set_data in exercise.sets:
                if set_data.weight and set_data.reps:
                    total_volume += set_data.weight * set_data.reps
        return total_volume
    
    def _update_progress_tracking(self, workout: WorkoutSession):
        """Update progress tracking with workout data"""
        progress_file = os.path.join(self.progress_path, "exercise_progress.json")
        
        # Load existing progress
        progress_data = {}
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
        
        # Update exercise records
        for exercise in workout.exercises:
            exercise_name = exercise.name.lower()
            if exercise_name not in progress_data:
                progress_data[exercise_name] = {
                    "category": exercise.category.value,
                    "best_sets": [],
                    "volume_history": [],
                    "frequency_count": 0
                }
            
            # Track best sets (by weight, reps, or volume)
            exercise_data = progress_data[exercise_name]
            exercise_data["frequency_count"] += 1
            
            for set_data in exercise.sets:
                if set_data.weight and set_data.reps:
                    volume = set_data.weight * set_data.reps
                    exercise_data["volume_history"].append({
                        "date": workout.date,
                        "weight": set_data.weight,
                        "reps": set_data.reps,
                        "volume": volume,
                        "rpe": set_data.rpe
                    })
                    
                    # Update best sets
                    self._update_personal_records(exercise_data, set_data, workout.date)
        
        # Save updated progress
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2, default=str)
    
    def _update_personal_records(self, exercise_data: Dict, set_data: ExerciseSet, workout_date: str):
        """Update personal records for an exercise"""
        new_record = {
            "date": workout_date,
            "weight": set_data.weight,
            "reps": set_data.reps,
            "volume": set_data.weight * set_data.reps if set_data.weight and set_data.reps else 0
        }
        
        best_sets = exercise_data.get("best_sets", [])
        
        # Check for new records
        records_updated = False
        record_types = ["weight", "reps", "volume"]
        
        for record_type in record_types:
            current_best = max(best_sets, key=lambda x: x.get(record_type, 0), default={})
            if new_record[record_type] > current_best.get(record_type, 0):
                new_record[f"pr_{record_type}"] = True
                records_updated = True
        
        if records_updated:
            best_sets.append(new_record)
            # Keep only recent best sets (last 10)
            exercise_data["best_sets"] = sorted(best_sets, key=lambda x: x["volume"], reverse=True)[:10]
    
    def get_workout_history(self, days: int = 30) -> List[Dict]:
        """
        Retrieve workout history for specified number of days
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of workout sessions
        """
        workouts = []
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        for filename in os.listdir(self.daily_logs_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.daily_logs_path, filename)
                with open(filepath, 'r') as f:
                    workout_data = json.load(f)
                    workout_date = datetime.fromisoformat(workout_data["workout"]["date"]).date()
                    if workout_date >= cutoff_date:
                        workouts.append(workout_data)
        
        return sorted(workouts, key=lambda x: x["workout"]["date"], reverse=True)
    
    def get_exercise_progress(self, exercise_name: str) -> Dict[str, Any]:
        """
        Get progress data for a specific exercise
        
        Args:
            exercise_name: Name of the exercise
            
        Returns:
            Progress data including records and history
        """
        progress_file = os.path.join(self.progress_path, "exercise_progress.json")
        
        if not os.path.exists(progress_file):
            return {"error": "No progress data found"}
        
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
        
        exercise_key = exercise_name.lower()
        return progress_data.get(exercise_key, {"error": f"No data found for {exercise_name}"})
    
    def get_weekly_summary(self, week_offset: int = 0) -> Dict[str, Any]:
        """
        Get weekly workout summary
        
        Args:
            week_offset: Weeks back from current (0 = this week)
            
        Returns:
            Weekly summary statistics
        """
        from datetime import timedelta
        
        # Calculate week start/end
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)
        
        workouts = []
        for filename in os.listdir(self.daily_logs_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.daily_logs_path, filename)
                with open(filepath, 'r') as f:
                    workout_data = json.load(f)
                    workout_date = datetime.fromisoformat(workout_data["workout"]["date"]).date()
                    if week_start <= workout_date <= week_end:
                        workouts.append(workout_data["workout"])
        
        # Calculate summary stats
        total_workouts = len(workouts)
        total_duration = sum(w["duration_minutes"] for w in workouts)
        total_volume = sum(w.get("total_volume", 0) for w in workouts)
        avg_rating = sum(w.get("workout_rating", 0) for w in workouts if w.get("workout_rating")) / max(1, len([w for w in workouts if w.get("workout_rating")]))
        
        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_workouts": total_workouts,
            "total_duration_minutes": total_duration,
            "total_volume": total_volume,
            "average_rating": round(avg_rating, 1) if avg_rating else None,
            "workout_types": list(set(w["workout_type"] for w in workouts))
        }
    
    def export_data(self, format_type: str = "json") -> str:
        """
        Export all fitness data
        
        Args:
            format_type: Export format ("json" or "csv")
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type.lower() == "json":
            export_path = os.path.join("exports", f"fitness_data_{timestamp}.json")
            
            # Collect all data
            all_data = {
                "user_id": self.user_id,
                "export_timestamp": datetime.now().isoformat(),
                "workouts": self.get_workout_history(days=365),  # Last year
                "progress": {}
            }
            
            # Add progress data
            progress_file = os.path.join(self.progress_path, "exercise_progress.json")
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    all_data["progress"] = json.load(f)
            
            os.makedirs("exports", exist_ok=True)
            with open(export_path, 'w') as f:
                json.dump(all_data, f, indent=2, default=str)
                
        elif format_type.lower() == "csv":
            import csv
            export_path = os.path.join("exports", f"workout_summary_{timestamp}.csv")
            
            workouts = self.get_workout_history(days=365)
            os.makedirs("exports", exist_ok=True)
            
            with open(export_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Type", "Duration", "Exercises", "Total Volume", "Rating"])
                
                for workout_data in workouts:
                    workout = workout_data["workout"]
                    writer.writerow([
                        workout["date"],
                        workout["workout_type"],
                        workout["duration_minutes"],
                        len(workout["exercises"]),
                        workout.get("total_volume", 0),
                        workout.get("workout_rating", "")
                    ])
        
        return export_path

# Convenience functions for quick logging
def quick_log_exercise(
    exercise_name: str,
    sets_data: List[tuple],  # [(weight, reps), (weight, reps), ...]
    workout_type: WorkoutType = WorkoutType.STRENGTH,
    category: ExerciseCategory = ExerciseCategory.FULL_BODY
) -> str:
    """
    Quick function to log a single exercise
    
    Args:
        exercise_name: Name of exercise
        sets_data: List of (weight, reps) tuples
        workout_type: Type of workout
        category: Exercise category
        
    Returns:
        Log file path
    """
    logger = FitnessLogger()
    
    # Convert tuples to ExerciseSet objects
    sets = [ExerciseSet(reps=reps, weight=weight) for weight, reps in sets_data]
    
    # Create exercise
    exercise = Exercise(
        name=exercise_name,
        category=category,
        sets=sets
    )
    
    # Create workout session
    workout = WorkoutSession(
        date=datetime.now().isoformat(),
        workout_type=workout_type,
        exercises=[exercise],
        duration_minutes=30  # default
    )
    
    result = logger.log_workout(workout)
    return result["file_path"]

# Example usage
if __name__ == "__main__":
    # Example workout logging
    logger = FitnessLogger()
    
    # Create sample workout
    bench_press = Exercise(
        name="Bench Press",
        category=ExerciseCategory.CHEST,
        sets=[
            ExerciseSet(reps=10, weight=135, rpe=7),
            ExerciseSet(reps=8, weight=145, rpe=8),
            ExerciseSet(reps=6, weight=155, rpe=9)
        ],
        equipment="Barbell"
    )
    
    workout = WorkoutSession(
        date=datetime.now().isoformat(),
        workout_type=WorkoutType.STRENGTH,
        exercises=[bench_press],
        duration_minutes=45,
        workout_rating=8,
        location="Gym"
    )
    
    result = logger.log_workout(workout)
    print(f"Workout logged: {result}")
    
    # Get progress
    progress = logger.get_exercise_progress("bench press")
    print(f"Bench press progress: {progress}")
    
    # Get weekly summary
    summary = logger.get_weekly_summary()
    print(f"This week's summary: {summary}")