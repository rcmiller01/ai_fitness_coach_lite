"""
Workout Planner for AI Fitness Coach

Generates personalized workout plans based on user goals, available equipment,
time constraints, and health considerations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import random

from utils.equipment_profile import (
    get_exercise_substitution, 
    filter_workout_by_equipment,
    WORKOUT_TEMPLATES,
    EQUIPMENT_PROFILES
)
from core.health_parser import HealthDataParser

class WorkoutGoal(Enum):
    """Workout goals for plan generation"""
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    ENDURANCE = "endurance"
    FAT_LOSS = "fat_loss"
    GENERAL_FITNESS = "general_fitness"
    ATHLETIC_PERFORMANCE = "athletic_performance"

class FitnessLevel(Enum):
    """User fitness levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class WorkoutPlanner:
    """
    Intelligent workout planning system with equipment awareness
    and health condition considerations.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.health_parser = HealthDataParser(user_id)
        
        # Rep ranges by goal
        self.rep_ranges = {
            WorkoutGoal.STRENGTH: (1, 6),
            WorkoutGoal.HYPERTROPHY: (6, 12),
            WorkoutGoal.ENDURANCE: (12, 20),
            WorkoutGoal.FAT_LOSS: (8, 15),
            WorkoutGoal.GENERAL_FITNESS: (8, 12),
            WorkoutGoal.ATHLETIC_PERFORMANCE: (3, 8)
        }
        
        # Set counts by fitness level
        self.set_counts = {
            FitnessLevel.BEGINNER: (2, 3),
            FitnessLevel.INTERMEDIATE: (3, 4),
            FitnessLevel.ADVANCED: (4, 6)
        }
    
    def generate_workout_plan(
        self,
        goal: WorkoutGoal,
        duration_minutes: int,
        available_equipment: List[str],
        fitness_level: FitnessLevel = FitnessLevel.INTERMEDIATE,
        target_muscle_groups: Optional[List[str]] = None,
        health_considerations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete workout plan based on parameters
        
        Args:
            goal: Primary workout goal
            duration_minutes: Available workout time
            available_equipment: List of available equipment
            fitness_level: User's current fitness level
            target_muscle_groups: Specific muscle groups to target
            health_considerations: Health conditions to consider
            
        Returns:
            Complete workout plan with exercises, sets, reps, and timing
        """
        
        # Get health readiness assessment
        readiness = self.health_parser.get_readiness_assessment()
        
        # Select appropriate template based on equipment
        template = self._select_workout_template(available_equipment, goal, duration_minutes)
        
        # Filter and adapt exercises
        adapted_workout = filter_workout_by_equipment(template, available_equipment)
        
        # Generate specific exercise details
        exercise_plan = self._generate_exercise_details(
            adapted_workout["adapted_exercises"],
            goal,
            fitness_level,
            duration_minutes,
            target_muscle_groups
        )
        
        # Apply health considerations
        if health_considerations or readiness.get("recommendations"):
            exercise_plan = self._apply_health_modifications(exercise_plan, health_considerations, readiness)
        
        # Calculate timing and rest periods
        timing_plan = self._calculate_workout_timing(exercise_plan, duration_minutes)
        
        return {
            "workout_id": f"workout_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "goal": goal.value,
            "duration_minutes": duration_minutes,
            "fitness_level": fitness_level.value,
            "readiness_score": readiness.get("readiness_score", 0.7),
            "template_used": template,
            "equipment_needed": available_equipment,
            "exercises": exercise_plan,
            "timing": timing_plan,
            "health_modifications": health_considerations or [],
            "estimated_calories": self._estimate_calories(exercise_plan, duration_minutes),
            "notes": self._generate_workout_notes(goal, readiness)
        }
    
    def _select_workout_template(self, equipment: List[str], goal: WorkoutGoal, duration: int) -> str:
        """Select most appropriate workout template"""
        
        # Equipment-based template selection
        if not equipment:
            return "bodyweight_anywhere"
        elif "barbell" in equipment and "dumbbells" in equipment:
            return "strength_gym"
        elif "dumbbells" in equipment:
            return "strength_home_basic"
        else:
            return "bodyweight_anywhere"
    
    def _generate_exercise_details(
        self,
        exercises: List[str],
        goal: WorkoutGoal,
        fitness_level: FitnessLevel,
        duration: int,
        target_groups: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Generate detailed exercise prescriptions"""
        
        rep_range = self.rep_ranges[goal]
        set_range = self.set_counts[fitness_level]
        
        exercise_details = []
        
        for exercise in exercises:
            # Filter by target muscle groups if specified
            if target_groups and not self._exercise_targets_groups(exercise, target_groups):
                continue
                
            sets = random.randint(set_range[0], set_range[1])
            reps = random.randint(rep_range[0], rep_range[1])
            
            exercise_detail = {
                "name": exercise,
                "category": self._get_exercise_category(exercise),
                "sets": sets,
                "reps": reps,
                "rest_seconds": self._calculate_rest_time(goal, sets),
                "intensity": self._get_intensity_guidance(goal, fitness_level),
                "form_cues": self._get_form_cues(exercise),
                "progression": self._get_progression_notes(exercise, fitness_level)
            }
            
            exercise_details.append(exercise_detail)
        
        return exercise_details
    
    def _apply_health_modifications(
        self,
        exercise_plan: List[Dict],
        health_conditions: Optional[List[str]],
        readiness: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply health-based modifications to workout plan"""
        
        modified_plan = exercise_plan.copy()
        
        # Reduce intensity if low readiness
        if readiness.get("readiness_score", 0.7) < 0.5:
            for exercise in modified_plan:
                exercise["sets"] = max(1, exercise["sets"] - 1)
                exercise["intensity"] = "light"
                exercise["notes"] = "Reduced intensity due to low readiness score"
        
        # Apply condition-specific modifications
        if health_conditions:
            for condition in health_conditions:
                if condition == "joint_issues":
                    modified_plan = self._modify_for_joint_issues(modified_plan)
                elif condition == "hypertension":
                    modified_plan = self._modify_for_hypertension(modified_plan)
                elif condition == "diabetes":
                    modified_plan = self._modify_for_diabetes(modified_plan)
        
        return modified_plan
    
    def _modify_for_joint_issues(self, plan: List[Dict]) -> List[Dict]:
        """Modify workout for joint health considerations"""
        for exercise in plan:
            exercise["rest_seconds"] += 30  # Extra rest
            exercise["form_cues"].append("Focus on controlled movement, avoid impact")
            if "jump" in exercise["name"].lower():
                exercise["alternative"] = exercise["name"].replace("jump", "step")
        return plan
    
    def _modify_for_hypertension(self, plan: List[Dict]) -> List[Dict]:
        """Modify workout for blood pressure considerations"""
        for exercise in plan:
            exercise["rest_seconds"] = max(exercise["rest_seconds"], 90)  # Longer rest
            exercise["form_cues"].append("Breathe steadily, avoid breath holding")
        return plan
    
    def _modify_for_diabetes(self, plan: List[Dict]) -> List[Dict]:
        """Modify workout for diabetes management"""
        for exercise in plan:
            exercise["notes"] = "Monitor blood glucose before and after exercise"
        return plan
    
    def _calculate_workout_timing(self, exercises: List[Dict], total_minutes: int) -> Dict[str, Any]:
        """Calculate workout timing and pacing"""
        
        warm_up_time = 5
        cool_down_time = 5
        exercise_time = total_minutes - warm_up_time - cool_down_time
        
        total_exercise_time = sum(
            (exercise["sets"] * 30) + (exercise["rest_seconds"] * (exercise["sets"] - 1))
            for exercise in exercises
        ) / 60  # Convert to minutes
        
        if total_exercise_time > exercise_time:
            # Scale down rest times if workout is too long
            scale_factor = exercise_time / total_exercise_time
            for exercise in exercises:
                exercise["rest_seconds"] = int(exercise["rest_seconds"] * scale_factor)
        
        return {
            "warm_up_minutes": warm_up_time,
            "exercise_minutes": exercise_time,
            "cool_down_minutes": cool_down_time,
            "estimated_total": total_minutes,
            "pace": "moderate" if total_exercise_time <= exercise_time else "fast"
        }
    
    def _estimate_calories(self, exercises: List[Dict], duration: int) -> int:
        """Estimate calories burned during workout"""
        # Simple estimation: 8-12 calories per minute based on intensity
        base_rate = 10  # calories per minute
        
        # Adjust based on exercise types
        strength_exercises = sum(1 for ex in exercises if "weight" in ex["name"] or "press" in ex["name"])
        cardio_exercises = sum(1 for ex in exercises if "jump" in ex["name"] or "run" in ex["name"])
        
        intensity_multiplier = 1.0
        if cardio_exercises > strength_exercises:
            intensity_multiplier = 1.3
        elif strength_exercises > cardio_exercises:
            intensity_multiplier = 0.9
        
        return int(duration * base_rate * intensity_multiplier)
    
    def _generate_workout_notes(self, goal: WorkoutGoal, readiness: Dict) -> List[str]:
        """Generate helpful workout notes and tips"""
        notes = []
        
        if goal == WorkoutGoal.STRENGTH:
            notes.append("Focus on progressive overload - increase weight when you can complete all reps with good form")
        elif goal == WorkoutGoal.HYPERTROPHY:
            notes.append("Emphasize time under tension and mind-muscle connection")
        elif goal == WorkoutGoal.FAT_LOSS:
            notes.append("Keep rest periods short to maintain elevated heart rate")
        
        if readiness.get("readiness_score", 0.7) < 0.6:
            notes.append("Consider this a recovery day - listen to your body")
        
        notes.append("Stay hydrated throughout the workout")
        notes.append("Stop if you experience pain or discomfort")
        
        return notes
    
    # Helper methods (placeholders for now)
    def _exercise_targets_groups(self, exercise: str, target_groups: List[str]) -> bool:
        """Check if exercise targets specified muscle groups"""
        # This would be implemented with a comprehensive exercise database
        return True
    
    def _get_exercise_category(self, exercise: str) -> str:
        """Get exercise category (chest, back, legs, etc.)"""
        # Placeholder implementation
        if "press" in exercise.lower() or "push" in exercise.lower():
            return "chest"
        elif "pull" in exercise.lower() or "row" in exercise.lower():
            return "back"
        elif "squat" in exercise.lower() or "lunge" in exercise.lower():
            return "legs"
        else:
            return "full_body"
    
    def _calculate_rest_time(self, goal: WorkoutGoal, sets: int) -> int:
        """Calculate appropriate rest time between sets"""
        base_rest = {
            WorkoutGoal.STRENGTH: 180,
            WorkoutGoal.HYPERTROPHY: 90,
            WorkoutGoal.ENDURANCE: 45,
            WorkoutGoal.FAT_LOSS: 60,
            WorkoutGoal.GENERAL_FITNESS: 75,
            WorkoutGoal.ATHLETIC_PERFORMANCE: 120
        }
        return base_rest.get(goal, 90)
    
    def _get_intensity_guidance(self, goal: WorkoutGoal, fitness_level: FitnessLevel) -> str:
        """Get intensity guidance for the workout"""
        if goal == WorkoutGoal.STRENGTH:
            return "high" if fitness_level == FitnessLevel.ADVANCED else "moderate-high"
        elif goal == WorkoutGoal.ENDURANCE:
            return "moderate"
        else:
            return "moderate-high"
    
    def _get_form_cues(self, exercise: str) -> List[str]:
        """Get form cues for specific exercises"""
        # Placeholder - would be expanded with comprehensive form guidance
        general_cues = [
            "Maintain proper posture throughout",
            "Control the movement on both concentric and eccentric phases",
            "Breathe properly - exhale on exertion"
        ]
        return general_cues
    
    def _get_progression_notes(self, exercise: str, fitness_level: FitnessLevel) -> str:
        """Get progression guidance for the exercise"""
        if fitness_level == FitnessLevel.BEGINNER:
            return "Focus on mastering form before adding weight"
        elif fitness_level == FitnessLevel.INTERMEDIATE:
            return "Increase weight by 2.5-5lbs when you can complete all sets with perfect form"
        else:
            return "Consider advanced variations or periodization techniques"

# Quick workout generation function
def quick_generate_workout(
    duration_minutes: int = 30,
    equipment: List[str] = None,
    goal: str = "general_fitness"
) -> Dict[str, Any]:
    """Quick workout generation for testing"""
    planner = WorkoutPlanner()
    
    if equipment is None:
        equipment = ["dumbbells", "resistance_bands"]
    
    return planner.generate_workout_plan(
        goal=WorkoutGoal(goal),
        duration_minutes=duration_minutes,
        available_equipment=equipment,
        fitness_level=FitnessLevel.INTERMEDIATE
    )

if __name__ == "__main__":
    # Example workout generation
    planner = WorkoutPlanner()
    
    sample_workout = planner.generate_workout_plan(
        goal=WorkoutGoal.STRENGTH,
        duration_minutes=45,
        available_equipment=["barbell", "dumbbells", "bench"],
        fitness_level=FitnessLevel.INTERMEDIATE,
        target_muscle_groups=["chest", "back", "legs"]
    )
    
    print("Generated Workout Plan:")
    print(f"Goal: {sample_workout['goal']}")
    print(f"Duration: {sample_workout['duration_minutes']} minutes")
    print(f"Exercises: {len(sample_workout['exercises'])}")
    for exercise in sample_workout['exercises']:
        print(f"  - {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps")