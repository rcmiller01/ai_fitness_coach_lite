"""
Health Data Parser for AI Fitness Coach

Processes health data from HealthKit, Google Fit, or manual input
to inform workout planning and recovery assessment.
"""

import json
import csv
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

class HealthDataSource(Enum):
    """Sources of health data"""
    HEALTHKIT = "healthkit"
    GOOGLE_FIT = "google_fit"
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    JSON_IMPORT = "json_import"

class SleepQuality(Enum):
    """Sleep quality levels"""
    DEEP = "deep"
    LIGHT = "light"
    INTERRUPTED = "interrupted"
    POOR = "poor"
    EXCELLENT = "excellent"

class HealthCondition(Enum):
    """Health conditions that affect workout planning"""
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"
    JOINT_ISSUES = "joint_issues"
    HEART_CONDITION = "heart_condition"
    INJURY_RECOVERY = "injury_recovery"
    NONE = "none"

@dataclass
class SleepData:
    """Sleep tracking data"""
    date: str
    start_time: str
    end_time: str
    duration_hours: float
    quality: SleepQuality
    deep_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    awakenings: Optional[int] = None
    source: HealthDataSource = HealthDataSource.MANUAL
    
    def get_quality_score(self) -> float:
        """Calculate sleep quality score from 0-100"""
        base_score = 50
        
        # Duration factor (7-9 hours optimal)
        if 7 <= self.duration_hours <= 9:
            duration_bonus = 20
        elif 6 <= self.duration_hours <= 10:
            duration_bonus = 10
        else:
            duration_bonus = -10
        
        # Quality factor
        quality_scores = {
            SleepQuality.EXCELLENT: 30,
            SleepQuality.DEEP: 20,
            SleepQuality.LIGHT: 0,
            SleepQuality.INTERRUPTED: -15,
            SleepQuality.POOR: -25
        }
        quality_bonus = quality_scores.get(self.quality, 0)
        
        # Awakenings penalty
        awakening_penalty = -5 * (self.awakenings or 0)
        
        score = base_score + duration_bonus + quality_bonus + awakening_penalty
        return max(0, min(100, score))  # Clamp between 0-100

@dataclass
class HeartRateData:
    """Heart rate data"""
    timestamp: str
    bpm: int
    context: str = "general"  # resting, exercise, recovery
    confidence: Optional[float] = None
    source: HealthDataSource = HealthDataSource.MANUAL

@dataclass
class BiometricData:
    """General biometric measurements"""
    date: str
    weight: Optional[float] = None  # in kg or lbs
    body_fat_percentage: Optional[float] = None
    muscle_mass: Optional[float] = None
    hydration_level: Optional[float] = None
    source: HealthDataSource = HealthDataSource.MANUAL

@dataclass
class ActivityData:
    """Daily activity/movement data"""
    date: str
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    calories_burned: Optional[int] = None
    active_minutes: Optional[int] = None
    floors_climbed: Optional[int] = None
    source: HealthDataSource = HealthDataSource.MANUAL

@dataclass
class HealthProfile:
    """User health profile and conditions"""
    user_id: str
    age: int
    sex: str  # M/F/Other
    height_cm: float
    conditions: List[HealthCondition]
    medications: List[str] = None
    allergies: List[str] = None
    fitness_level: str = "intermediate"  # beginner, intermediate, advanced
    goals: List[str] = None
    created_date: str = ""
    updated_date: str = ""

class HealthDataParser:
    """
    Comprehensive health data processing and analysis system
    """
    
    def __init__(self, user_id: str = "default_user", data_dir: str = "data"):
        self.user_id = user_id
        self.data_dir = data_dir
        self.health_data_path = os.path.join(data_dir, "health_data")
        self.profile_path = os.path.join(data_dir, "user_profile.json")
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.health_data_path, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
    
    # Profile Management
    def create_health_profile(self, profile: HealthProfile) -> Dict[str, Any]:
        """
        Create or update user health profile
        
        Args:
            profile: HealthProfile object
            
        Returns:
            Status and profile data
        """
        profile.updated_date = datetime.now().isoformat()
        if not profile.created_date:
            profile.created_date = profile.updated_date
            
        profile_data = asdict(profile)
        
        with open(self.profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2, default=str)
            
        return {
            "status": "profile_updated",
            "profile": profile_data
        }
    
    def get_health_profile(self) -> Optional[HealthProfile]:
        """Load user health profile"""
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                data = json.load(f)
                return HealthProfile(**data)
        return None
    
    # Data Import Functions
    def import_healthkit_data(self, healthkit_export_path: str) -> Dict[str, Any]:
        """
        Import data from HealthKit export
        
        Args:
            healthkit_export_path: Path to HealthKit export file
            
        Returns:
            Import results summary
        """
        # This would parse HealthKit XML/JSON export
        # For now, returning a placeholder structure
        return {
            "status": "healthkit_import_ready",
            "message": "HealthKit import functionality to be implemented",
            "suggested_fields": [
                "sleep_analysis",
                "heart_rate",
                "steps",
                "workouts",
                "body_measurements"
            ]
        }
    
    def import_google_fit_data(self, google_fit_export_path: str) -> Dict[str, Any]:
        """
        Import data from Google Fit export
        
        Args:
            google_fit_export_path: Path to Google Fit export
            
        Returns:
            Import results summary
        """
        # This would parse Google Fit JSON export
        return {
            "status": "google_fit_import_ready",
            "message": "Google Fit import functionality to be implemented",
            "suggested_fields": [
                "activity_data",
                "sleep_data",
                "heart_rate",
                "weight",
                "nutrition"
            ]
        }
    
    def import_csv_data(self, csv_path: str, data_type: str) -> Dict[str, Any]:
        """
        Import health data from CSV file
        
        Args:
            csv_path: Path to CSV file
            data_type: Type of data (sleep, heart_rate, activity, biometric)
            
        Returns:
            Import results
        """
        imported_records = 0
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    if data_type == "sleep":
                        self._process_sleep_row(row)
                    elif data_type == "heart_rate":
                        self._process_heart_rate_row(row)
                    elif data_type == "activity":
                        self._process_activity_row(row)
                    elif data_type == "biometric":
                        self._process_biometric_row(row)
                    
                    imported_records += 1
                    
            return {
                "status": "csv_import_complete",
                "imported_records": imported_records,
                "data_type": data_type
            }
            
        except Exception as e:
            return {
                "status": "csv_import_error",
                "error": str(e)
            }
    
    def _process_sleep_row(self, row: Dict[str, str]):
        """Process a single sleep data row"""
        sleep_data = SleepData(
            date=row.get("date", ""),
            start_time=row.get("start_time", ""),
            end_time=row.get("end_time", ""),
            duration_hours=float(row.get("duration_hours", 0)),
            quality=SleepQuality(row.get("quality", "light")),
            source=HealthDataSource.CSV_IMPORT
        )
        self.store_sleep_data(sleep_data)
    
    def _process_heart_rate_row(self, row: Dict[str, str]):
        """Process a single heart rate data row"""
        hr_data = HeartRateData(
            timestamp=row.get("timestamp", ""),
            bpm=int(row.get("bpm", 0)),
            context=row.get("context", "general"),
            source=HealthDataSource.CSV_IMPORT
        )
        self.store_heart_rate_data(hr_data)
    
    def _process_activity_row(self, row: Dict[str, str]):
        """Process a single activity data row"""
        activity_data = ActivityData(
            date=row.get("date", ""),
            steps=int(row.get("steps", 0)) if row.get("steps") else None,
            distance_km=float(row.get("distance_km", 0)) if row.get("distance_km") else None,
            calories_burned=int(row.get("calories_burned", 0)) if row.get("calories_burned") else None,
            source=HealthDataSource.CSV_IMPORT
        )
        self.store_activity_data(activity_data)
    
    def _process_biometric_row(self, row: Dict[str, str]):
        """Process a single biometric data row"""
        biometric_data = BiometricData(
            date=row.get("date", ""),
            weight=float(row.get("weight", 0)) if row.get("weight") else None,
            body_fat_percentage=float(row.get("body_fat", 0)) if row.get("body_fat") else None,
            source=HealthDataSource.CSV_IMPORT
        )
        self.store_biometric_data(biometric_data)
    
    # Data Storage Functions
    def store_sleep_data(self, sleep_data: SleepData) -> str:
        """Store sleep data"""
        filename = f"sleep_{sleep_data.date}.json"
        filepath = os.path.join(self.health_data_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(sleep_data), f, indent=2, default=str)
            
        return filepath
    
    def store_heart_rate_data(self, hr_data: HeartRateData) -> str:
        """Store heart rate data"""
        date_str = datetime.fromisoformat(hr_data.timestamp).date().isoformat()
        filename = f"heart_rate_{date_str}.json"
        filepath = os.path.join(self.health_data_path, filename)
        
        # Append to existing file or create new
        existing_data = []
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                existing_data = json.load(f)
        
        existing_data.append(asdict(hr_data))
        
        with open(filepath, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)
            
        return filepath
    
    def store_activity_data(self, activity_data: ActivityData) -> str:
        """Store daily activity data"""
        filename = f"activity_{activity_data.date}.json"
        filepath = os.path.join(self.health_data_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(activity_data), f, indent=2, default=str)
            
        return filepath
    
    def store_biometric_data(self, biometric_data: BiometricData) -> str:
        """Store biometric measurements"""
        filename = f"biometric_{biometric_data.date}.json"
        filepath = os.path.join(self.health_data_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(biometric_data), f, indent=2, default=str)
            
        return filepath
    
    # Analysis Functions
    def get_sleep_analysis(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze recent sleep patterns
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Sleep analysis summary
        """
        cutoff_date = (datetime.now().date() - timedelta(days=days)).isoformat()
        sleep_records = []
        
        for filename in os.listdir(self.health_data_path):
            if filename.startswith("sleep_") and filename.endswith(".json"):
                date_str = filename.replace("sleep_", "").replace(".json", "")
                if date_str >= cutoff_date:
                    filepath = os.path.join(self.health_data_path, filename)
                    with open(filepath, 'r') as f:
                        sleep_records.append(json.load(f))
        
        if not sleep_records:
            return {"error": "No sleep data found"}
        
        # Calculate averages
        avg_duration = sum(r["duration_hours"] for r in sleep_records) / len(sleep_records)
        quality_counts = {}
        for record in sleep_records:
            quality = record["quality"]
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        return {
            "period_days": days,
            "records_found": len(sleep_records),
            "average_duration_hours": round(avg_duration, 1),
            "quality_distribution": quality_counts,
            "recovery_score": self._calculate_recovery_score(sleep_records)
        }
    
    def _calculate_recovery_score(self, sleep_records: List[Dict]) -> float:
        """Calculate a simple recovery score based on sleep data"""
        if not sleep_records:
            return 0.5
        
        # Simple scoring based on duration and quality
        score = 0
        for record in sleep_records:
            duration_score = min(record["duration_hours"] / 8.0, 1.0)  # Target 8 hours
            
            quality_scores = {
                "excellent": 1.0,
                "deep": 0.9,
                "light": 0.6,
                "interrupted": 0.4,
                "poor": 0.2
            }
            quality_score = quality_scores.get(record["quality"], 0.5)
            
            score += (duration_score + quality_score) / 2
        
        return round(score / len(sleep_records), 2)
    
    def get_readiness_assessment(self) -> Dict[str, Any]:
        """
        Assess user readiness for workout based on health data
        
        Returns:
            Readiness assessment with recommendations
        """
        profile = self.get_health_profile()
        sleep_analysis = self.get_sleep_analysis(days=3)
        
        readiness_score = 0.7  # Default moderate readiness
        recommendations = []
        
        # Adjust based on sleep
        if sleep_analysis.get("recovery_score", 0.5) > 0.8:
            readiness_score += 0.2
            recommendations.append("Great sleep quality - ready for intense training")
        elif sleep_analysis.get("recovery_score", 0.5) < 0.4:
            readiness_score -= 0.3
            recommendations.append("Poor sleep quality - consider lighter workout or rest")
        
        # Adjust based on health conditions
        if profile and profile.conditions:
            for condition in profile.conditions:
                if condition == HealthCondition.HEART_CONDITION:
                    recommendations.append("Monitor heart rate closely during exercise")
                elif condition == HealthCondition.JOINT_ISSUES:
                    recommendations.append("Focus on low-impact exercises")
                elif condition == HealthCondition.DIABETES:
                    recommendations.append("Monitor blood glucose before and after exercise")
        
        readiness_score = max(0.0, min(1.0, readiness_score))  # Clamp to [0,1]
        
        return {
            "readiness_score": round(readiness_score, 2),
            "level": "high" if readiness_score > 0.8 else "moderate" if readiness_score > 0.5 else "low",
            "recommendations": recommendations,
            "factors_considered": ["sleep_quality", "health_conditions"]
        }
    
    def export_health_data(self) -> str:
        """Export all health data for backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join("exports", f"health_data_{timestamp}.json")
        
        # Collect all health data
        all_data = {
            "user_id": self.user_id,
            "export_timestamp": datetime.now().isoformat(),
            "profile": None,
            "health_records": []
        }
        
        # Add profile
        profile = self.get_health_profile()
        if profile:
            all_data["profile"] = asdict(profile)
        
        # Add all health records
        for filename in os.listdir(self.health_data_path):
            if filename.endswith(".json"):
                filepath = os.path.join(self.health_data_path, filename)
                with open(filepath, 'r') as f:
                    all_data["health_records"].append({
                        "filename": filename,
                        "data": json.load(f)
                    })
        
        os.makedirs("exports", exist_ok=True)
        with open(export_path, 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        
        return export_path

# Convenience functions
def quick_health_check(user_id: str = "default_user") -> Dict[str, Any]:
    """Quick health readiness check"""
    parser = HealthDataParser(user_id)
    return parser.get_readiness_assessment()

def create_sample_profile() -> HealthProfile:
    """Create a sample health profile for testing"""
    return HealthProfile(
        user_id="sample_user",
        age=30,
        sex="M",
        height_cm=175,
        conditions=[HealthCondition.NONE],
        fitness_level="intermediate",
        goals=["strength", "endurance"],
        created_date=datetime.now().isoformat()
    )

# Example usage
if __name__ == "__main__":
    # Example health data processing
    parser = HealthDataParser()
    
    # Create sample profile
    profile = create_sample_profile()
    parser.create_health_profile(profile)
    
    # Add sample sleep data
    sleep_data = SleepData(
        date=date.today().isoformat(),
        start_time="23:00",
        end_time="07:00",
        duration_hours=8.0,
        quality=SleepQuality.DEEP
    )
    parser.store_sleep_data(sleep_data)
    
    # Get readiness assessment
    readiness = parser.get_readiness_assessment()
    print(f"Workout readiness: {readiness}")
    
    # Get sleep analysis
    sleep_analysis = parser.get_sleep_analysis()
    print(f"Sleep analysis: {sleep_analysis}")