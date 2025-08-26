"""
Unit Tests for Workout Logging System

Tests workout session logging, progress tracking, and fitness data management.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, mock_open
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.workout_logger import (
    FitnessLogger, WorkoutSession, Exercise, ExerciseSet,
    ExerciseCategory, ExerciseType
)
from tests.test_config import TestConfig, TestHelpers

class TestExerciseSet:
    """Test ExerciseSet data class"""
    
    def test_exercise_set_creation(self):
        """Test creating exercise sets"""
        exercise_set = ExerciseSet(
            reps=15,
            weight=20.0,
            duration=None,
            perceived_exertion=7,
            rest_time=60
        )
        
        assert exercise_set.reps == 15
        assert exercise_set.weight == 20.0
        assert exercise_set.perceived_exertion == 7
        assert exercise_set.rest_time == 60
    
    def test_exercise_set_basic_functionality(self):
        """Test basic exercise set functionality"""
        exercise_set = ExerciseSet(reps=10, weight=25.0)
        
        assert exercise_set.reps == 10
        assert exercise_set.weight == 25.0
        assert exercise_set.duration is None

class TestExercise:
    """Test Exercise data class"""
    
    def test_exercise_creation(self):
        """Test creating exercises"""
        sets = [
            ExerciseSet(reps=10, weight=50.0, rpe=6),
            ExerciseSet(reps=8, weight=55.0, rpe=7),
            ExerciseSet(reps=6, weight=60.0, rpe=8)
        ]
        
        exercise = Exercise(
            name="Bench Press",
            category=ExerciseCategory.UPPER_BODY,
            sets=sets,
            equipment="barbell",
            form_notes="Keep shoulders retracted"
        )
        
        assert exercise.name == "Bench Press"
        assert exercise.category == ExerciseCategory.UPPER_BODY
        assert len(exercise.sets) == 3
        assert exercise.equipment == "barbell"
    
    def test_exercise_volume_calculation(self):
        """Test exercise volume calculation"""
        sets = [
            ExerciseSet(reps=10, weight=50.0),
            ExerciseSet(reps=10, weight=50.0),
            ExerciseSet(reps=10, weight=50.0)
        ]
        
        exercise = Exercise(
            name="Squats",
            category=ExerciseCategory.LOWER_BODY,
            sets=sets
        )
        
        total_volume = exercise.get_total_volume()
        assert total_volume == 1500.0  # 3 sets * 10 reps * 50kg

class TestWorkoutSession:
    """Test WorkoutSession functionality"""
    
    def test_workout_session_creation(self, mock_workout_session):
        """Test creating workout sessions"""
        
        sets = [ExerciseSet(reps=15, rpe=7)]
        exercises = [Exercise(
            name="Push-ups",
            category=ExerciseCategory.UPPER_BODY,
            sets=sets
        )]
        
        session = WorkoutSession(
            date=mock_workout_session["date"],
            workout_type=WorkoutType.STRENGTH,
            exercises=exercises,
            duration_minutes=45,
            workout_rating=8
        )
        
        assert session.workout_type == WorkoutType.STRENGTH
        assert len(session.exercises) == 1
        assert session.duration_minutes == 45
        assert session.workout_rating == 8
    
    def test_workout_session_summary(self):
        """Test workout session summary generation"""
        
        sets = [
            ExerciseSet(reps=10, weight=50.0),
            ExerciseSet(reps=8, weight=55.0)
        ]
        
        exercises = [
            Exercise(name="Squats", category=ExerciseCategory.LOWER_BODY, sets=sets),
            Exercise(name="Push-ups", category=ExerciseCategory.UPPER_BODY, 
                    sets=[ExerciseSet(reps=20)])
        ]
        
        session = WorkoutSession(
            date=datetime.now().isoformat(),
            workout_type=WorkoutType.STRENGTH,
            exercises=exercises,
            duration_minutes=60
        )
        
        summary = session.get_summary()
        
        assert "total_exercises" in summary
        assert "total_sets" in summary
        assert "total_volume" in summary
        assert summary["total_exercises"] == 2
        assert summary["total_sets"] == 3

class TestFitnessLogger:
    """Test FitnessLogger main functionality"""
    
    @pytest.fixture
    def logger(self):
        """Create fitness logger with mocked file operations"""
        with patch('utils.logger.os.makedirs'), \
             patch('utils.logger.os.path.exists', return_value=True):
            return FitnessLogger()
    
    def test_logger_initialization(self, logger):
        """Test logger initializes correctly"""
        assert logger is not None
        assert hasattr(logger, 'data_dir')
        assert hasattr(logger, 'workout_history')
        assert hasattr(logger, 'personal_records')
    
    @patch('builtins.open', mock_open())
    @patch('json.dump')
    def test_log_workout(self, mock_json_dump, logger):
        """Test logging workout sessions"""
        
        sets = [ExerciseSet(reps=10, weight=80.0, rpe=7)]
        exercises = [Exercise(
            name="Deadlift",
            category=ExerciseCategory.LOWER_BODY,
            sets=sets
        )]
        
        session = WorkoutSession(
            date=datetime.now().isoformat(),
            workout_type=WorkoutType.STRENGTH,
            exercises=exercises,
            duration_minutes=45,
            workout_rating=8
        )
        
        result = logger.log_workout(session)
        
        assert result["status"] == "success"
        assert "workout_id" in result
        assert "summary" in result
        mock_json_dump.assert_called()
    
    def test_get_workout_history(self, logger):
        """Test retrieving workout history"""
        
        # Mock workout data
        mock_workouts = [
            {
                "date": (datetime.now() - timedelta(days=1)).isoformat(),
                "workout_type": "strength",
                "duration_minutes": 45,
                "workout_rating": 8
            },
            {
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "workout_type": "cardio",
                "duration_minutes": 30,
                "workout_rating": 7
            }
        ]
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_workouts), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            history = logger.get_workout_history(days=7)
            
            assert len(history) == 2
            assert history[0]["workout_type"] == "strength"
    
    def test_personal_records_tracking(self, logger):
        """Test personal records tracking"""
        
        # Create workout with new PR
        sets = [ExerciseSet(reps=1, weight=100.0, rpe=10)]  # Max effort
        exercises = [Exercise(
            name="Bench Press",
            category=ExerciseCategory.UPPER_BODY,
            sets=sets
        )]
        
        session = WorkoutSession(
            date=datetime.now().isoformat(),
            workout_type=WorkoutType.STRENGTH,
            exercises=exercises,
            duration_minutes=60
        )
        
        with patch('builtins.open', mock_open()), \
             patch('json.dump'), \
             patch('json.load', return_value={}):  # No existing PRs
            
            result = logger.log_workout(session)
            
            # Should detect new PR
            assert "personal_records" in result
    
    def test_get_exercise_progress(self, logger):
        """Test exercise progress tracking"""
        
        # Mock exercise history
        mock_history = [
            {
                "date": (datetime.now() - timedelta(days=7)).isoformat(),
                "exercises": [{
                    "name": "Squats",
                    "sets": [{"reps": 10, "weight": 60.0}]
                }]
            },
            {
                "date": (datetime.now() - timedelta(days=1)).isoformat(),
                "exercises": [{
                    "name": "Squats",
                    "sets": [{"reps": 10, "weight": 65.0}]
                }]
            }
        ]
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_history), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            progress = logger.get_exercise_progress("Squats")
            
            assert "exercise_name" in progress
            assert "progress_data" in progress
            assert "trend" in progress
    
    def test_weekly_summary(self, logger):
        """Test weekly workout summary"""
        
        # Mock week of workouts
        mock_workouts = []
        for i in range(5):  # 5 workouts this week
            mock_workouts.append({
                "date": (datetime.now() - timedelta(days=i)).isoformat(),
                "workout_type": "strength" if i % 2 == 0 else "cardio",
                "duration_minutes": 45,
                "exercises": [{
                    "name": "Test Exercise",
                    "sets": [{"reps": 10, "weight": 50.0}]
                }]
            })
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_workouts), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            summary = logger.get_weekly_summary()
            
            assert "total_workouts" in summary
            assert "total_time" in summary
            assert "workout_types" in summary
            assert summary["total_workouts"] == 5
            assert summary["total_time"] == 225  # 5 * 45 minutes
    
    def test_export_data(self, logger):
        """Test data export functionality"""
        
        mock_data = {
            "workouts": [],
            "personal_records": {},
            "export_date": datetime.now().isoformat()
        }
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=[]), \
             patch('utils.logger.os.path.exists', return_value=True), \
             patch('zipfile.ZipFile') as mock_zip:
            
            export_path = logger.export_data("json")
            
            assert export_path.endswith('.zip')
            mock_zip.assert_called()
    
    def test_workout_streaks(self, logger):
        """Test workout streak calculation"""
        
        # Mock consecutive workout days
        mock_workouts = []
        for i in range(7):  # 7 consecutive days
            mock_workouts.append({
                "date": (datetime.now() - timedelta(days=i)).isoformat(),
                "workout_type": "strength",
                "duration_minutes": 30
            })
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_workouts), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            streaks = logger.get_workout_streaks()
            
            assert "current_streak" in streaks
            assert "longest_streak" in streaks
            assert streaks["current_streak"] >= 7

class TestWorkoutAnalytics:
    """Test workout analytics and insights"""
    
    def test_volume_progression(self):
        """Test volume progression calculation"""
        logger = FitnessLogger()
        
        # Mock progressive overload data
        mock_history = []
        base_weight = 50.0
        
        for week in range(4):
            for day in range(3):  # 3 workouts per week
                date = datetime.now() - timedelta(weeks=week, days=day)
                mock_history.append({
                    "date": date.isoformat(),
                    "exercises": [{
                        "name": "Bench Press",
                        "sets": [
                            {"reps": 10, "weight": base_weight + (week * 2.5)},
                            {"reps": 10, "weight": base_weight + (week * 2.5)},
                            {"reps": 10, "weight": base_weight + (week * 2.5)}
                        ]
                    }]
                })
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_history), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            progression = logger.analyze_volume_progression("Bench Press", weeks=4)
            
            assert "weekly_volumes" in progression
            assert "progression_rate" in progression
            assert len(progression["weekly_volumes"]) == 4
    
    def test_strength_gains(self):
        """Test strength gain analysis"""
        logger = FitnessLogger()
        
        # Mock strength progression
        mock_prs = {
            "Squat": [
                {"date": "2024-08-01", "weight": 100.0, "reps": 1},
                {"date": "2024-08-15", "weight": 105.0, "reps": 1},
                {"date": "2024-08-26", "weight": 110.0, "reps": 1}
            ]
        }
        
        with patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_prs), \
             patch('utils.logger.os.path.exists', return_value=True):
            
            gains = logger.analyze_strength_gains("Squat")
            
            assert "total_gain" in gains
            assert "percentage_gain" in gains
            assert gains["total_gain"] == 10.0  # 110 - 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])