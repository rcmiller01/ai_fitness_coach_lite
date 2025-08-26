"""
Diet Engine for AI Fitness Coach

Generates personalized nutrition plans based on user goals, health data,
and dietary preferences with macro and calorie tracking.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from enum import Enum
import json

from core.health_parser import HealthDataParser

class DietGoal(Enum):
    """Nutrition goals for meal planning"""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    PERFORMANCE = "performance"
    GENERAL_HEALTH = "general_health"

class ActivityLevel(Enum):
    """Physical activity levels for calorie calculation"""
    SEDENTARY = "sedentary"          # Little/no exercise
    LIGHTLY_ACTIVE = "lightly_active"  # Light exercise 1-3 days/week
    MODERATELY_ACTIVE = "moderately_active"  # Moderate exercise 3-5 days/week
    VERY_ACTIVE = "very_active"      # Hard exercise 6-7 days/week
    EXTREMELY_ACTIVE = "extremely_active"  # Very hard exercise, physical job

class DietaryRestriction(Enum):
    """Common dietary restrictions and preferences"""
    NONE = "none"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    KETOGENIC = "ketogenic"
    PALEO = "paleo"
    MEDITERRANEAN = "mediterranean"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    LOW_CARB = "low_carb"
    HIGH_PROTEIN = "high_protein"

class DietEngine:
    """
    Intelligent nutrition planning system with health integration
    and personalized macro calculations.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.health_parser = HealthDataParser(user_id)
        
        # Activity level multipliers for TDEE calculation
        self.activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }
        
        # Macro ratios by goal (protein%, carb%, fat%)
        self.macro_ratios = {
            DietGoal.WEIGHT_LOSS: (0.35, 0.30, 0.35),
            DietGoal.WEIGHT_GAIN: (0.25, 0.45, 0.30),
            DietGoal.MUSCLE_GAIN: (0.30, 0.40, 0.30),
            DietGoal.MAINTENANCE: (0.25, 0.45, 0.30),
            DietGoal.PERFORMANCE: (0.20, 0.55, 0.25),
            DietGoal.GENERAL_HEALTH: (0.25, 0.45, 0.30)
        }
    
    def calculate_calorie_needs(
        self,
        age: int,
        sex: str,
        weight_kg: float,
        height_cm: float,
        activity_level: ActivityLevel,
        goal: DietGoal
    ) -> Dict[str, Any]:
        """
        Calculate daily calorie needs using Mifflin-St Jeor equation
        
        Args:
            age: Age in years
            sex: M/F
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            activity_level: Physical activity level
            goal: Nutrition goal
            
        Returns:
            Calorie breakdown with BMR, TDEE, and target calories
        """
        
        # Calculate BMR (Basal Metabolic Rate)
        if sex.upper() == 'M':
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        else:  # Female
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
        
        # Calculate TDEE (Total Daily Energy Expenditure)
        activity_multiplier = self.activity_multipliers[activity_level]
        tdee = bmr * activity_multiplier
        
        # Adjust calories based on goal
        goal_adjustments = {
            DietGoal.WEIGHT_LOSS: -500,      # 1 lb/week loss
            DietGoal.WEIGHT_GAIN: +500,      # 1 lb/week gain
            DietGoal.MUSCLE_GAIN: +300,      # Lean bulk
            DietGoal.MAINTENANCE: 0,
            DietGoal.PERFORMANCE: +200,      # Slight surplus for performance
            DietGoal.GENERAL_HEALTH: 0
        }
        
        target_calories = tdee + goal_adjustments.get(goal, 0)
        
        return {
            "bmr": round(bmr),
            "tdee": round(tdee),
            "target_calories": round(target_calories),
            "calorie_adjustment": goal_adjustments.get(goal, 0),
            "goal": goal.value,
            "activity_level": activity_level.value
        }
    
    def calculate_macros(
        self,
        target_calories: int,
        goal: DietGoal,
        dietary_restrictions: List[DietaryRestriction] = None
    ) -> Dict[str, Any]:
        """
        Calculate macro breakdown based on calories and goals
        
        Args:
            target_calories: Daily calorie target
            goal: Nutrition goal
            dietary_restrictions: List of dietary restrictions
            
        Returns:
            Macro breakdown in grams and percentages
        """
        
        if dietary_restrictions is None:
            dietary_restrictions = []
        
        # Get base macro ratios
        protein_ratio, carb_ratio, fat_ratio = self.macro_ratios[goal]
        
        # Adjust ratios based on dietary restrictions
        if DietaryRestriction.KETOGENIC in dietary_restrictions:
            protein_ratio, carb_ratio, fat_ratio = 0.25, 0.05, 0.70
        elif DietaryRestriction.LOW_CARB in dietary_restrictions:
            protein_ratio, carb_ratio, fat_ratio = 0.35, 0.20, 0.45
        elif DietaryRestriction.HIGH_PROTEIN in dietary_restrictions:
            protein_ratio, carb_ratio, fat_ratio = 0.40, 0.30, 0.30
        
        # Calculate macro grams (4 cal/g protein, 4 cal/g carb, 9 cal/g fat)
        protein_calories = target_calories * protein_ratio
        carb_calories = target_calories * carb_ratio
        fat_calories = target_calories * fat_ratio
        
        protein_grams = protein_calories / 4
        carb_grams = carb_calories / 4
        fat_grams = fat_calories / 9
        
        return {
            "target_calories": target_calories,
            "protein": {
                "grams": round(protein_grams),
                "calories": round(protein_calories),
                "percentage": round(protein_ratio * 100)
            },
            "carbohydrates": {
                "grams": round(carb_grams),
                "calories": round(carb_calories),
                "percentage": round(carb_ratio * 100)
            },
            "fat": {
                "grams": round(fat_grams),
                "calories": round(fat_calories),
                "percentage": round(fat_ratio * 100)
            },
            "dietary_restrictions": [dr.value for dr in dietary_restrictions]
        }
    
    def generate_meal_plan(
        self,
        target_calories: int,
        macro_breakdown: Dict[str, Any],
        dietary_restrictions: List[DietaryRestriction] = None,
        meals_per_day: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a basic meal plan structure
        
        Args:
            target_calories: Daily calorie target
            macro_breakdown: Macro breakdown from calculate_macros
            dietary_restrictions: List of dietary restrictions
            meals_per_day: Number of meals per day (3-6)
            
        Returns:
            Structured meal plan with calorie and macro distribution
        """
        
        if dietary_restrictions is None:
            dietary_restrictions = []
        
        # Distribute calories across meals
        if meals_per_day == 3:
            # Breakfast: 25%, Lunch: 35%, Dinner: 40%
            meal_ratios = [0.25, 0.35, 0.40]
            meal_names = ["Breakfast", "Lunch", "Dinner"]
        elif meals_per_day == 4:
            # Add snack: Breakfast: 25%, Lunch: 30%, Snack: 15%, Dinner: 30%
            meal_ratios = [0.25, 0.30, 0.15, 0.30]
            meal_names = ["Breakfast", "Lunch", "Snack", "Dinner"]
        elif meals_per_day == 5:
            # More balanced: 20% each meal
            meal_ratios = [0.20, 0.20, 0.20, 0.20, 0.20]
            meal_names = ["Breakfast", "Morning Snack", "Lunch", "Afternoon Snack", "Dinner"]
        else:
            # Default to 3 meals
            meal_ratios = [0.25, 0.35, 0.40]
            meal_names = ["Breakfast", "Lunch", "Dinner"]
        
        meals = []
        for i, (name, ratio) in enumerate(zip(meal_names, meal_ratios)):
            meal_calories = target_calories * ratio
            meal_protein = macro_breakdown["protein"]["grams"] * ratio
            meal_carbs = macro_breakdown["carbohydrates"]["grams"] * ratio
            meal_fat = macro_breakdown["fat"]["grams"] * ratio
            
            meal = {
                "name": name,
                "calories": round(meal_calories),
                "macros": {
                    "protein": round(meal_protein),
                    "carbohydrates": round(meal_carbs),
                    "fat": round(meal_fat)
                },
                "food_suggestions": self._get_food_suggestions(
                    name, dietary_restrictions, meal_calories
                )
            }
            meals.append(meal)
        
        return {
            "date": date.today().isoformat(),
            "total_calories": target_calories,
            "total_macros": macro_breakdown,
            "meals_per_day": meals_per_day,
            "meals": meals,
            "dietary_restrictions": [dr.value for dr in dietary_restrictions],
            "hydration_goal_ml": self._calculate_hydration_needs(target_calories),
            "notes": self._generate_nutrition_notes(dietary_restrictions, target_calories)
        }
    
    def _get_food_suggestions(
        self,
        meal_name: str,
        restrictions: List[DietaryRestriction],
        target_calories: float
    ) -> List[str]:
        """Get food suggestions based on meal and restrictions"""
        
        # Basic food suggestions by meal type
        base_suggestions = {
            "Breakfast": [
                "Oatmeal with berries and nuts",
                "Greek yogurt with fruit",
                "Eggs with whole grain toast",
                "Protein smoothie with banana"
            ],
            "Lunch": [
                "Grilled chicken salad",
                "Quinoa bowl with vegetables",
                "Turkey and avocado wrap",
                "Lentil soup with bread"
            ],
            "Dinner": [
                "Baked salmon with sweet potato",
                "Lean beef with rice and vegetables",
                "Chicken stir-fry with brown rice",
                "Tofu curry with quinoa"
            ],
            "Snack": [
                "Apple with almond butter",
                "Greek yogurt with nuts",
                "Protein bar",
                "Hummus with vegetables"
            ],
            "Morning Snack": [
                "Banana with peanut butter",
                "Trail mix",
                "Protein shake",
                "Hard-boiled egg"
            ],
            "Afternoon Snack": [
                "Cottage cheese with fruit",
                "Nuts and seeds",
                "Protein bar",
                "Vegetable sticks with hummus"
            ]
        }
        
        suggestions = base_suggestions.get(meal_name, base_suggestions["Snack"])
        
        # Filter based on dietary restrictions
        if DietaryRestriction.VEGAN in restrictions:
            suggestions = [s for s in suggestions if not any(
                animal in s.lower() for animal in ["chicken", "beef", "salmon", "egg", "yogurt", "cheese"]
            )]
        elif DietaryRestriction.VEGETARIAN in restrictions:
            suggestions = [s for s in suggestions if not any(
                meat in s.lower() for meat in ["chicken", "beef", "salmon", "turkey"]
            )]
        
        if DietaryRestriction.GLUTEN_FREE in restrictions:
            suggestions = [s for s in suggestions if not any(
                gluten in s.lower() for gluten in ["bread", "wrap", "oatmeal"]
            )]
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _calculate_hydration_needs(self, calories: int) -> int:
        """Calculate daily hydration needs in ml"""
        # Basic formula: 1ml per calorie + 500ml base
        return calories + 500
    
    def _generate_nutrition_notes(
        self,
        restrictions: List[DietaryRestriction],
        calories: int
    ) -> List[str]:
        """Generate helpful nutrition notes"""
        notes = []
        
        notes.append("Spread protein intake evenly throughout the day")
        notes.append("Include a variety of colorful vegetables for micronutrients")
        notes.append("Stay hydrated - aim for clear or light yellow urine")
        
        if DietaryRestriction.VEGETARIAN in restrictions or DietaryRestriction.VEGAN in restrictions:
            notes.append("Ensure adequate B12, iron, and omega-3 fatty acids")
        
        if DietaryRestriction.KETOGENIC in restrictions:
            notes.append("Monitor ketone levels and ensure adequate electrolytes")
        
        if calories < 1500:
            notes.append("Consider micronutrient supplementation due to lower calorie intake")
        
        return notes
    
    def generate_nutrition_plan(
        self,
        age: int,
        sex: str,
        weight_kg: float,
        height_cm: float,
        activity_level: ActivityLevel,
        goal: DietGoal,
        dietary_restrictions: List[DietaryRestriction] = None,
        meals_per_day: int = 3
    ) -> Dict[str, Any]:
        """
        Generate complete nutrition plan
        
        Args:
            age: Age in years
            sex: M/F
            weight_kg: Weight in kg
            height_cm: Height in cm
            activity_level: Activity level
            goal: Nutrition goal
            dietary_restrictions: List of dietary restrictions
            meals_per_day: Number of meals per day
            
        Returns:
            Complete nutrition plan with calories, macros, and meal suggestions
        """
        
        if dietary_restrictions is None:
            dietary_restrictions = []
        
        # Calculate calorie needs
        calorie_data = self.calculate_calorie_needs(
            age, sex, weight_kg, height_cm, activity_level, goal
        )
        
        # Calculate macros
        macro_data = self.calculate_macros(
            calorie_data["target_calories"], goal, dietary_restrictions
        )
        
        # Generate meal plan
        meal_plan = self.generate_meal_plan(
            calorie_data["target_calories"], macro_data, dietary_restrictions, meals_per_day
        )
        
        return {
            "user_profile": {
                "age": age,
                "sex": sex,
                "weight_kg": weight_kg,
                "height_cm": height_cm,
                "activity_level": activity_level.value,
                "goal": goal.value
            },
            "calorie_breakdown": calorie_data,
            "macro_targets": macro_data,
            "meal_plan": meal_plan,
            "plan_id": f"nutrition_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_date": datetime.now().isoformat()
        }

# Quick nutrition plan generation
def quick_nutrition_plan(
    weight_kg: float = 70,
    height_cm: float = 175,
    age: int = 30,
    sex: str = "M",
    goal: str = "maintenance"
) -> Dict[str, Any]:
    """Quick nutrition plan for testing"""
    engine = DietEngine()
    
    return engine.generate_nutrition_plan(
        age=age,
        sex=sex,
        weight_kg=weight_kg,
        height_cm=height_cm,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=DietGoal(goal),
        dietary_restrictions=[],
        meals_per_day=3
    )

if __name__ == "__main__":
    # Example nutrition plan generation
    engine = DietEngine()
    
    sample_plan = engine.generate_nutrition_plan(
        age=30,
        sex="M",
        weight_kg=80,
        height_cm=180,
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
        goal=DietGoal.MUSCLE_GAIN,
        dietary_restrictions=[DietaryRestriction.HIGH_PROTEIN],
        meals_per_day=4
    )
    
    print("Generated Nutrition Plan:")
    print(f"Target Calories: {sample_plan['calorie_breakdown']['target_calories']}")
    print(f"Protein: {sample_plan['macro_targets']['protein']['grams']}g")
    print(f"Carbs: {sample_plan['macro_targets']['carbohydrates']['grams']}g")
    print(f"Fat: {sample_plan['macro_targets']['fat']['grams']}g")
    print(f"Meals: {len(sample_plan['meal_plan']['meals'])}")