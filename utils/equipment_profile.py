"""
Equipment Profile Configuration for AI Fitness Coach

Defines available equipment and exercise substitution mappings
for equipment-aware workout planning.
"""

EQUIPMENT_CATEGORIES = {
    "free_weights": {
        "barbell": ["olympic_barbell", "standard_barbell", "curl_bar"],
        "dumbbells": ["adjustable_dumbbells", "fixed_dumbbells", "powerblocks"],
        "kettlebells": ["competition_kettlebells", "cast_iron_kettlebells"],
        "weight_plates": ["olympic_plates", "standard_plates", "bumper_plates"]
    },
    "machines": {
        "cardio": ["treadmill", "elliptical", "stationary_bike", "rowing_machine"],
        "strength": ["lat_pulldown", "leg_press", "chest_press", "leg_curl", "leg_extension"],
        "functional": ["cable_machine", "smith_machine", "power_rack", "squat_rack"]
    },
    "bodyweight": {
        "supports": ["pull_up_bar", "dip_station", "parallette_bars"],
        "accessories": ["resistance_bands", "suspension_trainer", "medicine_ball"]
    },
    "home_gym": {
        "minimal": ["yoga_mat", "resistance_bands", "jump_rope"],
        "basic": ["dumbbells", "resistance_bands", "yoga_mat", "pull_up_bar"],
        "intermediate": ["adjustable_dumbbells", "barbell", "bench", "pull_up_bar"],
        "advanced": ["power_rack", "barbell", "dumbbells", "bench", "cable_system"]
    }
}

EXERCISE_EQUIPMENT_MAP = {
    # Chest Exercises
    "bench_press": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "dumbbell_bench_press",
            "machines": "chest_press_machine",
            "bodyweight": "push_ups",
            "resistance_bands": "resistance_band_chest_press"
        }
    },
    "incline_bench_press": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "incline_dumbbell_press",
            "machines": "incline_chest_press",
            "bodyweight": "incline_push_ups",
            "resistance_bands": "incline_band_press"
        }
    },
    "dips": {
        "primary_equipment": "dip_station",
        "alternatives": {
            "chairs": "chair_dips",
            "bodyweight": "tricep_dips",
            "resistance_bands": "tricep_band_extensions"
        }
    },
    
    # Back Exercises
    "deadlift": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "dumbbell_deadlift",
            "kettlebells": "kettlebell_deadlift",
            "resistance_bands": "band_deadlift",
            "bodyweight": "single_leg_rdl"
        }
    },
    "pull_ups": {
        "primary_equipment": "pull_up_bar",
        "alternatives": {
            "machines": "lat_pulldown",
            "resistance_bands": "band_assisted_pullups",
            "bodyweight": "inverted_rows"
        }
    },
    "bent_over_row": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "dumbbell_rows",
            "machines": "seated_cable_row",
            "resistance_bands": "band_rows",
            "bodyweight": "inverted_rows"
        }
    },
    
    # Leg Exercises
    "squat": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "dumbbell_squats",
            "bodyweight": "bodyweight_squats",
            "kettlebells": "goblet_squats",
            "machines": "leg_press"
        }
    },
    "lunges": {
        "primary_equipment": "bodyweight",
        "alternatives": {
            "dumbbells": "dumbbell_lunges",
            "barbell": "barbell_lunges",
            "kettlebells": "kettlebell_lunges",
            "resistance_bands": "band_lunges"
        }
    },
    "leg_press": {
        "primary_equipment": "leg_press_machine",
        "alternatives": {
            "bodyweight": "squats",
            "dumbbells": "dumbbell_squats",
            "resistance_bands": "band_squats"
        }
    },
    
    # Shoulder Exercises
    "overhead_press": {
        "primary_equipment": "barbell",
        "alternatives": {
            "dumbbells": "dumbbell_shoulder_press",
            "machines": "shoulder_press_machine",
            "kettlebells": "kettlebell_press",
            "resistance_bands": "band_shoulder_press"
        }
    },
    "lateral_raises": {
        "primary_equipment": "dumbbells",
        "alternatives": {
            "resistance_bands": "band_lateral_raises",
            "cables": "cable_lateral_raises",
            "bodyweight": "arm_circles"
        }
    },
    
    # Arm Exercises
    "bicep_curls": {
        "primary_equipment": "dumbbells",
        "alternatives": {
            "barbell": "barbell_curls",
            "resistance_bands": "band_curls",
            "cables": "cable_curls",
            "bodyweight": "chin_ups"
        }
    },
    "tricep_extensions": {
        "primary_equipment": "dumbbells",
        "alternatives": {
            "resistance_bands": "band_tricep_extensions",
            "cables": "cable_tricep_extensions",
            "bodyweight": "close_grip_push_ups"
        }
    },
    
    # Core Exercises
    "planks": {
        "primary_equipment": "bodyweight",
        "alternatives": {
            "medicine_ball": "medicine_ball_plank",
            "resistance_bands": "band_pallof_press"
        }
    },
    "russian_twists": {
        "primary_equipment": "bodyweight",
        "alternatives": {
            "medicine_ball": "medicine_ball_twists",
            "dumbbells": "dumbbell_twists"
        }
    }
}

WORKOUT_TEMPLATES = {
    "strength_gym": {
        "equipment_required": ["barbell", "dumbbells", "bench"],
        "exercises": [
            "bench_press", "squat", "deadlift", "bent_over_row",
            "overhead_press", "pull_ups", "dips"
        ]
    },
    "strength_home_basic": {
        "equipment_required": ["dumbbells", "resistance_bands"],
        "exercises": [
            "dumbbell_bench_press", "dumbbell_squats", "dumbbell_deadlift",
            "dumbbell_rows", "dumbbell_shoulder_press", "band_assisted_pullups"
        ]
    },
    "bodyweight_anywhere": {
        "equipment_required": [],
        "exercises": [
            "push_ups", "bodyweight_squats", "lunges", "planks",
            "burpees", "mountain_climbers", "jumping_jacks"
        ]
    },
    "hiit_minimal": {
        "equipment_required": ["jump_rope"],
        "exercises": [
            "jump_rope", "high_knees", "burpees", "squat_jumps",
            "push_ups", "mountain_climbers", "plank_jacks"
        ]
    }
}

EQUIPMENT_PROFILES = {
    "gym_member": {
        "available_equipment": [
            "barbell", "dumbbells", "bench", "pull_up_bar", "dip_station",
            "leg_press_machine", "lat_pulldown", "cable_machine", "treadmill"
        ],
        "preferred_templates": ["strength_gym", "hiit_gym"]
    },
    "home_gym_advanced": {
        "available_equipment": [
            "adjustable_dumbbells", "barbell", "bench", "pull_up_bar",
            "resistance_bands", "kettlebells"
        ],
        "preferred_templates": ["strength_home_advanced", "hiit_home"]
    },
    "home_gym_basic": {
        "available_equipment": [
            "dumbbells", "resistance_bands", "yoga_mat", "jump_rope"
        ],
        "preferred_templates": ["strength_home_basic", "hiit_minimal"]
    },
    "minimal_equipment": {
        "available_equipment": [
            "resistance_bands", "yoga_mat"
        ],
        "preferred_templates": ["bodyweight_anywhere", "resistance_band_focus"]
    },
    "bodyweight_only": {
        "available_equipment": [],
        "preferred_templates": ["bodyweight_anywhere", "calisthenics"]
    }
}

def get_exercise_substitution(exercise: str, available_equipment: list) -> str:
    """
    Find appropriate exercise substitution based on available equipment
    
    Args:
        exercise: Original exercise name
        available_equipment: List of available equipment
        
    Returns:
        Best substitute exercise name
    """
    exercise_map = EXERCISE_EQUIPMENT_MAP.get(exercise.lower())
    if not exercise_map:
        return exercise  # Return original if no mapping found
    
    # Check if primary equipment is available
    primary_equipment = exercise_map["primary_equipment"]
    if primary_equipment in available_equipment:
        return exercise
    
    # Find best alternative
    alternatives = exercise_map.get("alternatives", {})
    for equipment, substitute in alternatives.items():
        if equipment in available_equipment:
            return substitute
    
    # Default to bodyweight alternative if available
    return alternatives.get("bodyweight", exercise)

def filter_workout_by_equipment(workout_template: str, available_equipment: list) -> dict:
    """
    Filter and adapt workout template based on available equipment
    
    Args:
        workout_template: Template name
        available_equipment: List of available equipment
        
    Returns:
        Adapted workout with equipment substitutions
    """
    template = WORKOUT_TEMPLATES.get(workout_template)
    if not template:
        return {"error": f"Template {workout_template} not found"}
    
    adapted_exercises = []
    for exercise in template["exercises"]:
        substitute = get_exercise_substitution(exercise, available_equipment)
        adapted_exercises.append(substitute)
    
    return {
        "template": workout_template,
        "original_exercises": template["exercises"],
        "adapted_exercises": adapted_exercises,
        "equipment_used": available_equipment,
        "substitutions_made": sum(1 for orig, adapt in zip(template["exercises"], adapted_exercises) if orig != adapt)
    }

def recommend_equipment_profile(available_equipment: list) -> str:
    """
    Recommend equipment profile based on available equipment
    
    Args:
        available_equipment: List of available equipment
        
    Returns:
        Recommended profile name
    """
    equipment_set = set(available_equipment)
    
    # Score each profile based on equipment overlap
    best_profile = "bodyweight_only"
    best_score = 0
    
    for profile_name, profile_data in EQUIPMENT_PROFILES.items():
        profile_equipment = set(profile_data["available_equipment"])
        overlap = len(equipment_set.intersection(profile_equipment))
        coverage = overlap / len(profile_equipment) if profile_equipment else 1
        
        if coverage > best_score:
            best_score = coverage
            best_profile = profile_name
    
    return best_profile