"""
AI Fitness Coach Lite - Main Backend API

FastAPI-based backend providing endpoints for workout planning,
health data processing, rep counting, and voice feedback.
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

# Import our custom modules
from core.health_parser import HealthDataParser, HealthProfile, SleepData, HeartRateData
from utils.logger import FitnessLogger, WorkoutSession, Exercise, ExerciseSet, WorkoutType, ExerciseCategory
from utils.voice_output import VoiceOutputService, CoachingTone
from plugins.core.plugin_manager import plugin_manager, load_all_plugins, get_sport_plugins
from plugins.core.plugin_store import plugin_store, PluginCategory
from plugins.core.mobile_bridge import mobile_bridge, MobileDeviceInfo, MobilePlatform
from api.ab_testing_api import router as ab_testing_router
from api.analytics_api import router as analytics_router
from api.monitoring_api import router as monitoring_router

# Initialize FastAPI app
app = FastAPI(
    title="AI Fitness Coach Lite",
    description="Offline-capable fitness coaching with AI-powered workout planning and rep tracking",
    version="1.0.0"
)

# Add CORS middleware for web/mobile integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize routers
health_router = APIRouter(prefix="/api/v1/health", tags=["Health Data"])
workout_router = APIRouter(prefix="/api/v1/workout", tags=["Workout Planning"])
logging_router = APIRouter(prefix="/api/v1/logging", tags=["Workout Logging"])
voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Feedback"])
plugin_router = APIRouter(prefix="/api/v1/plugins", tags=["Plugin System"])
store_router = APIRouter(prefix="/api/v1/store", tags=["Plugin Store"])
mobile_router = APIRouter(prefix="/api/v1/mobile", tags=["Mobile Integration"])
ab_testing_router_v1 = APIRouter(prefix="/api/v1", tags=["A/B Testing"])
analytics_router_v1 = APIRouter(prefix="/api/v1", tags=["Analytics"])
monitoring_router_v1 = APIRouter(prefix="/api/v1", tags=["Monitoring"])

# Initialize services
health_parser = HealthDataParser()
fitness_logger = FitnessLogger()
voice_service = VoiceOutputService()

# Pydantic Models for API endpoints
class UserProfileCreate(BaseModel):
    user_id: str
    age: int = Field(..., ge=13, le=120)
    sex: str = Field(..., pattern="^(M|F|Other)$")
    height_cm: float = Field(..., ge=100, le=250)
    weight_kg: Optional[float] = Field(None, ge=30, le=300)
    fitness_level: str = Field("intermediate", pattern="^(beginner|intermediate|advanced)$")
    goals: List[str] = []
    conditions: List[str] = []

class SleepDataInput(BaseModel):
    date: str
    start_time: str
    end_time: str
    duration_hours: float = Field(..., ge=0, le=24)
    quality: str = Field(..., pattern="^(deep|light|interrupted|poor|excellent)$")

class HeartRateInput(BaseModel):
    timestamp: str
    bpm: int = Field(..., ge=30, le=250)
    context: str = "general"

class WorkoutPlanRequest(BaseModel):
    workout_type: str
    duration_minutes: int = Field(..., ge=10, le=300)
    equipment_available: List[str] = []
    target_muscle_groups: List[str] = []
    fitness_level: str = "intermediate"

class ExerciseSetInput(BaseModel):
    reps: int = Field(..., ge=1, le=100)
    weight: Optional[float] = Field(None, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=1)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    rest_time: Optional[int] = Field(None, ge=0)

class ExerciseInput(BaseModel):
    name: str
    category: str
    sets: List[ExerciseSetInput]
    equipment: Optional[str] = None
    form_notes: Optional[str] = None

class WorkoutLogInput(BaseModel):
    workout_type: str
    exercises: List[ExerciseInput]
    duration_minutes: int
    workout_rating: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None
    location: Optional[str] = None

class VoiceMessageRequest(BaseModel):
    text: str
    tone: str = "encouraging"
    play_immediately: bool = True

# Health Data Endpoints
@health_router.post("/profile")
async def create_user_profile(profile_data: UserProfileCreate):
    """Create or update user health profile"""
    try:
        # Convert to HealthProfile object
        from core.health_parser import HealthCondition
        
        conditions = []
        for condition_str in profile_data.conditions:
            try:
                conditions.append(HealthCondition(condition_str))
            except ValueError:
                conditions.append(HealthCondition.NONE)
        
        profile = HealthProfile(
            user_id=profile_data.user_id,
            age=profile_data.age,
            sex=profile_data.sex,
            height_cm=profile_data.height_cm,
            conditions=conditions,
            fitness_level=profile_data.fitness_level,
            goals=profile_data.goals
        )
        
        result = health_parser.create_health_profile(profile)
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@health_router.get("/profile")
async def get_user_profile():
    """Get current user health profile"""
    profile = health_parser.get_health_profile()
    if profile:
        return JSONResponse(content={"profile": profile.__dict__})
    else:
        raise HTTPException(status_code=404, detail="No profile found")

@health_router.post("/sleep")
async def log_sleep_data(sleep_input: SleepDataInput):
    """Log sleep data for recovery assessment"""
    try:
        from core.health_parser import SleepQuality, HealthDataSource
        
        sleep_data = SleepData(
            date=sleep_input.date,
            start_time=sleep_input.start_time,
            end_time=sleep_input.end_time,
            duration_hours=sleep_input.duration_hours,
            quality=SleepQuality(sleep_input.quality),
            source=HealthDataSource.MANUAL
        )
        
        filepath = health_parser.store_sleep_data(sleep_data)
        return JSONResponse(content={
            "message": "Sleep data logged successfully",
            "file_path": filepath
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@health_router.post("/heart-rate")
async def log_heart_rate(hr_input: HeartRateInput):
    """Log heart rate data"""
    try:
        from core.health_parser import HealthDataSource
        
        hr_data = HeartRateData(
            timestamp=hr_input.timestamp,
            bpm=hr_input.bpm,
            context=hr_input.context,
            source=HealthDataSource.MANUAL
        )
        
        filepath = health_parser.store_heart_rate_data(hr_data)
        return JSONResponse(content={
            "message": "Heart rate data logged successfully",
            "file_path": filepath
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@health_router.get("/readiness")
async def get_workout_readiness():
    """Get workout readiness assessment based on health data"""
    try:
        assessment = health_parser.get_readiness_assessment()
        return JSONResponse(content=assessment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@health_router.get("/sleep-analysis")
async def get_sleep_analysis(days: int = 7):
    """Get sleep pattern analysis"""
    try:
        analysis = health_parser.get_sleep_analysis(days)
        return JSONResponse(content=analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Workout Planning Endpoints
@workout_router.post("/plan")
async def generate_workout_plan(plan_request: WorkoutPlanRequest):
    """Generate a workout plan based on parameters"""
    # This is a placeholder - actual workout generation logic to be implemented
    try:
        sample_plan = {
            "workout_id": f"workout_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": plan_request.workout_type,
            "duration_minutes": plan_request.duration_minutes,
            "exercises": [
                {
                    "name": "Sample Exercise 1",
                    "category": "chest",
                    "sets": 3,
                    "reps": "8-12",
                    "equipment": "barbell",
                    "instructions": "Maintain proper form throughout the movement"
                }
            ],
            "equipment_needed": plan_request.equipment_available,
            "estimated_calories": plan_request.duration_minutes * 8,
            "difficulty_level": plan_request.fitness_level
        }
        
        return JSONResponse(content={
            "message": "Workout plan generated successfully",
            "plan": sample_plan
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@workout_router.get("/equipment-substitutions")
async def get_equipment_substitutions(exercise: str, missing_equipment: str):
    """Get exercise substitutions for missing equipment"""
    # Placeholder for equipment substitution logic
    substitutions = {
        "barbell_bench_press": {
            "dumbbell": "Dumbbell bench press",
            "bodyweight": "Push-ups",
            "resistance_band": "Resistance band chest press"
        }
    }
    
    return JSONResponse(content={
        "original_exercise": exercise,
        "missing_equipment": missing_equipment,
        "substitutions": substitutions.get(exercise.lower(), [])
    })

# Workout Logging Endpoints
@logging_router.post("/workout")
async def log_workout(workout_input: WorkoutLogInput):
    """Log a completed workout session"""
    try:
        # Convert input to internal data structures
        exercises = []
        for ex_input in workout_input.exercises:
            sets = []
            for set_input in ex_input.sets:
                exercise_set = ExerciseSet(
                    reps=set_input.reps,
                    weight=set_input.weight or 0.0,
                    duration=set_input.duration_seconds,
                    rpe=set_input.rpe,
                    rest_time=set_input.rest_time
                )
                sets.append(exercise_set)
            
            exercise = Exercise(
                name=ex_input.name,
                category=ExerciseCategory(ex_input.category),
                sets=sets,
                equipment=ex_input.equipment,
                form_notes=ex_input.form_notes
            )
            exercises.append(exercise)
        
        workout_session = WorkoutSession(
            date=datetime.now().isoformat(),
            workout_type=WorkoutType(workout_input.workout_type),
            exercises=exercises,
            duration_minutes=workout_input.duration_minutes,
            workout_rating=workout_input.workout_rating,
            notes=workout_input.notes,
            location=workout_input.location
        )
        
        result = fitness_logger.log_workout(workout_session)
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@logging_router.get("/history")
async def get_workout_history(days: int = 30):
    """Get workout history for specified number of days"""
    try:
        history = fitness_logger.get_workout_history(days)
        return JSONResponse(content={
            "period_days": days,
            "workouts": history
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@logging_router.get("/progress/{exercise_name}")
async def get_exercise_progress(exercise_name: str):
    """Get progress data for a specific exercise"""
    try:
        progress = fitness_logger.get_exercise_progress(exercise_name)
        return JSONResponse(content=progress)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@logging_router.get("/weekly-summary")
async def get_weekly_summary(week_offset: int = 0):
    """Get weekly workout summary"""
    try:
        summary = fitness_logger.get_weekly_summary(week_offset)
        return JSONResponse(content=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Voice Feedback Endpoints
@voice_router.post("/speak")
async def generate_voice_feedback(voice_request: VoiceMessageRequest):
    """Generate voice feedback with specified coaching tone"""
    try:
        from utils.voice_output import CoachingTone
        
        tone = CoachingTone(voice_request.tone)
        audio_path = voice_service.speak_coaching_cue(
            text=voice_request.text,
            tone=tone,
            play_immediately=voice_request.play_immediately
        )
        
        return JSONResponse(content={
            "message": "Voice feedback generated",
            "audio_path": audio_path,
            "text": voice_request.text,
            "tone": voice_request.tone
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@voice_router.post("/rep-feedback")
async def provide_rep_feedback(current_reps: int, target_reps: int):
    """Provide automated rep count feedback"""
    try:
        voice_service.rep_count_feedback(current_reps, target_reps)
        return JSONResponse(content={
            "message": "Rep feedback provided",
            "current_reps": current_reps,
            "target_reps": target_reps
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@voice_router.post("/form-correction")
async def provide_form_correction(correction_message: str):
    """Provide form correction feedback"""
    try:
        voice_service.form_correction(correction_message)
        return JSONResponse(content={
            "message": "Form correction provided",
            "correction": correction_message
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Data Export Endpoints
@app.get("/api/v1/export/fitness-data")
async def export_fitness_data(format_type: str = "json"):
    """Export all fitness data for backup"""
    try:
        export_path = fitness_logger.export_data(format_type)
        return FileResponse(
            path=export_path,
            filename=os.path.basename(export_path),
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/export/health-data")
async def export_health_data():
    """Export all health data for backup"""
    try:
        export_path = health_parser.export_health_data()
        return FileResponse(
            path=export_path,
            filename=os.path.basename(export_path),
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with basic information"""
    active_plugins = plugin_manager.get_active_plugins()
    return {
        "message": "AI Fitness Coach Lite API",
        "version": "1.0.0",
        "features": [
            "Offline-capable workout planning",
            "Health data integration",
            "Voice coaching feedback",
            "Progress tracking",
            "Equipment-aware substitutions",
            "Plugin system for sports analysis"
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "workout": "/api/v1/workout", 
            "logging": "/api/v1/logging",
            "voice": "/api/v1/voice",
            "plugins": "/api/v1/plugins",
            "store": "/api/v1/store"
        },
        "active_plugins": active_plugins,
        "plugin_count": len(active_plugins)
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "health_parser": "operational",
            "fitness_logger": "operational",
            "voice_service": "operational"
        }
    }

# Plugin System Endpoints
@plugin_router.get("/discover")
async def discover_plugins():
    """Discover all available plugins"""
    try:
        discovered = plugin_manager.discover_plugins()
        return JSONResponse(content={
            "message": f"Discovered {len(discovered)} plugins",
            "plugins": [{
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "description": manifest.description,
                "type": manifest.plugin_type.value,
                "price": manifest.price,
                "trial_days": manifest.trial_days,
                "author": manifest.author,
                "tags": manifest.tags
            } for manifest in discovered]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/available")
async def get_available_plugins():
    """Get all available plugins with status"""
    try:
        plugins_info = []
        for manifest in plugin_manager.get_available_plugins():
            info = plugin_manager.get_plugin_info(manifest.id)
            plugins_info.append(info)
        
        return JSONResponse(content={
            "plugins": plugins_info
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/active")
async def get_active_plugins():
    """Get currently active plugins"""
    try:
        active_ids = plugin_manager.get_active_plugins()
        active_info = []
        
        for plugin_id in active_ids:
            info = plugin_manager.get_plugin_info(plugin_id)
            if info:
                active_info.append(info)
        
        return JSONResponse(content={
            "active_plugins": active_info,
            "count": len(active_info)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.post("/load/{plugin_id}")
async def load_plugin(plugin_id: str):
    """Load and activate a specific plugin"""
    try:
        success = plugin_manager.load_plugin(plugin_id)
        if success:
            return JSONResponse(content={
                "message": f"Plugin {plugin_id} loaded successfully",
                "plugin_id": plugin_id,
                "status": "active"
            })
        else:
            raise HTTPException(status_code=400, detail=f"Failed to load plugin {plugin_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@plugin_router.post("/unload/{plugin_id}")
async def unload_plugin(plugin_id: str):
    """Unload a specific plugin"""
    try:
        success = plugin_manager.unload_plugin(plugin_id)
        if success:
            return JSONResponse(content={
                "message": f"Plugin {plugin_id} unloaded successfully",
                "plugin_id": plugin_id,
                "status": "inactive"
            })
        else:
            raise HTTPException(status_code=400, detail=f"Plugin {plugin_id} not found or already inactive")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class TrialRequest(BaseModel):
    plugin_id: str

@plugin_router.post("/trial/start")
async def start_plugin_trial(trial_request: TrialRequest):
    """Start a trial for a premium plugin"""
    try:
        success = plugin_manager.start_trial(trial_request.plugin_id)
        if success:
            return JSONResponse(content={
                "message": f"Trial started for {trial_request.plugin_id}",
                "plugin_id": trial_request.plugin_id,
                "status": "trial_active"
            })
        else:
            raise HTTPException(status_code=400, detail="Trial could not be started. Check if trial is available or already used.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class LicenseActivation(BaseModel):
    plugin_id: str
    license_key: str

class ActivationCodeRedemption(BaseModel):
    activation_code: str

@plugin_router.post("/license/activate")
async def activate_plugin_license(license_request: LicenseActivation):
    """Activate a plugin with license key"""
    try:
        success = plugin_manager.activate_license(license_request.plugin_id, license_request.license_key)
        if success:
            return JSONResponse(content={
                "message": f"License activated for {license_request.plugin_id}",
                "plugin_id": license_request.plugin_id,
                "status": "licensed"
            })
        else:
            raise HTTPException(status_code=400, detail="Invalid license key")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@plugin_router.post("/license/redeem")
async def redeem_activation_code(redemption_request: ActivationCodeRedemption):
    """Redeem an activation code for a license"""
    try:
        result = plugin_manager.redeem_activation_code(redemption_request.activation_code)
        if result['success']:
            return JSONResponse(content={
                "message": "Activation code redeemed successfully",
                "plugin_id": result['plugin_id'],
                "license_type": result['license_type'],
                "features": result['features']
            })
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@plugin_router.get("/trial/status/{plugin_id}")
async def get_trial_status(plugin_id: str):
    """Get trial status for a plugin"""
    try:
        status = plugin_manager.get_trial_status(plugin_id)
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/info/{plugin_id}")
async def get_plugin_info(plugin_id: str):
    """Get detailed information about a specific plugin"""
    try:
        info = plugin_manager.get_plugin_info(plugin_id)
        if info:
            return JSONResponse(content=info)
        else:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Plugin Store Endpoints
@store_router.get("/featured")
async def get_featured_plugins():
    """Get featured plugins for homepage"""
    try:
        featured = plugin_store.get_featured_plugins()
        return JSONResponse(content={
            "featured_plugins": [{
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "short_description": plugin.short_description,
                "price": plugin.price,
                "discounted_price": plugin.discounted_price,
                "discount_percent": plugin.discount_percent,
                "rating": plugin.rating,
                "review_count": plugin.review_count,
                "trial_days": plugin.trial_days,
                "screenshots": plugin.screenshots[:2],  # First 2 screenshots
                "is_free": plugin.is_free
            } for plugin in featured]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@store_router.get("/categories/{category}")
async def get_plugins_by_category(category: str):
    """Get plugins by category"""
    try:
        # Convert string to enum
        category_enum = PluginCategory(category)
        plugins = plugin_store.get_plugins_by_category(category_enum)
        
        return JSONResponse(content={
            "category": category,
            "plugins": [{
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "short_description": plugin.short_description,
                "price": plugin.price,
                "discounted_price": plugin.discounted_price,
                "rating": plugin.rating,
                "review_count": plugin.review_count,
                "trial_days": plugin.trial_days,
                "is_free": plugin.is_free
            } for plugin in plugins]
        })
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@store_router.get("/search")
async def search_plugins(q: str):
    """Search plugins by query"""
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
        
        results = plugin_store.search_plugins(q)
        
        return JSONResponse(content={
            "query": q,
            "results": [{
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "short_description": plugin.short_description,
                "price": plugin.price,
                "rating": plugin.rating,
                "review_count": plugin.review_count,
                "trial_days": plugin.trial_days,
                "is_free": plugin.is_free,
                "features": plugin.features
            } for plugin in results],
            "count": len(results)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@store_router.get("/details/{plugin_id}")
async def get_plugin_details(plugin_id: str):
    """Get detailed plugin information including reviews"""
    try:
        details = plugin_store.get_plugin_details(plugin_id)
        if not details:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        return JSONResponse(content=details)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@store_router.get("/stats")
async def get_store_stats():
    """Get marketplace statistics"""
    try:
        stats = plugin_store.get_store_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@store_router.get("/categories")
async def get_all_categories():
    """Get all available plugin categories"""
    try:
        categories = [{
            "id": category.value,
            "name": category.value.replace("_", " ").title(),
            "plugin_count": len(plugin_store.categories.get(category, []))
        } for category in PluginCategory]
        
        return JSONResponse(content={
            "categories": categories
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PurchaseRequest(BaseModel):
    plugin_id: str
    payment_method: str = "credit_card"
    
@store_router.post("/purchase")
async def purchase_plugin(purchase_request: PurchaseRequest):
    """Simulate plugin purchase (would integrate with payment processor)"""
    try:
        # Get plugin details
        details = plugin_store.get_plugin_details(purchase_request.plugin_id)
        if not details:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        plugin = details['plugin']
        
        # For demo, simulate successful purchase
        import secrets
        activation_code = f"{plugin['name'].upper().replace(' ', '')[:4]}{secrets.token_hex(4).upper()}"
        
        return JSONResponse(content={
            "message": "Purchase successful!",
            "plugin_id": plugin['plugin_id'],
            "plugin_name": plugin['name'],
            "amount_paid": plugin['discounted_price'],
            "activation_code": activation_code,
            "instructions": "Use the activation code in the Plugins section to activate your purchase."
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Mobile Integration Endpoints
class MobileDeviceRegistration(BaseModel):
    device_id: str
    platform: str  # "ios" or "android"
    os_version: str
    app_version: str
    device_model: str
    screen_resolution: str = "1920x1080"
    camera_specs: Dict[str, Any] = {}
    sensors_available: List[str] = []

@mobile_router.post("/register")
async def register_mobile_device(device_reg: MobileDeviceRegistration):
    """Register a mobile device for plugin integration"""
    try:
        platform = MobilePlatform(device_reg.platform)
        
        device_info = MobileDeviceInfo(
            device_id=device_reg.device_id,
            platform=platform,
            os_version=device_reg.os_version,
            app_version=device_reg.app_version,
            device_model=device_reg.device_model,
            screen_resolution=device_reg.screen_resolution,
            camera_specs=device_reg.camera_specs,
            sensors_available=device_reg.sensors_available
        )
        
        registration_result = mobile_bridge.register_device(device_info)
        return JSONResponse(content=registration_result)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mobile_router.get("/sdk-config/{platform}")
async def get_mobile_sdk_config(platform: str):
    """Get mobile SDK configuration for a platform"""
    try:
        platform_enum = MobilePlatform(platform)
        config = mobile_bridge.get_mobile_sdk_config(platform_enum)
        return JSONResponse(content=config)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SessionStartRequest(BaseModel):
    device_id: str
    plugin_id: str
    capability_id: str

@mobile_router.post("/session/start")
async def start_mobile_session(session_req: SessionStartRequest):
    """Start a plugin session on mobile device"""
    try:
        result = mobile_bridge.start_session(
            session_req.device_id,
            session_req.plugin_id,
            session_req.capability_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class MobileDataInput(BaseModel):
    session_id: str
    data: Dict[str, Any]

@mobile_router.post("/session/data")
async def process_mobile_data(data_input: MobileDataInput):
    """Process data from mobile device during active session"""
    try:
        result = mobile_bridge.process_mobile_data(
            data_input.session_id,
            data_input.data
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mobile_router.post("/session/end/{session_id}")
async def end_mobile_session(session_id: str):
    """End a mobile plugin session"""
    try:
        result = mobile_bridge.end_session(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@mobile_router.get("/device/{device_id}/sessions")
async def get_device_sessions(device_id: str):
    """Get all active sessions for a mobile device"""
    try:
        sessions = mobile_bridge.get_device_sessions(device_id)
        return JSONResponse(content={
            "device_id": device_id,
            "active_sessions": sessions,
            "session_count": len(sessions)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sports Analysis Endpoints (for active sport plugins)
class PoseAnalysisRequest(BaseModel):
    pose_data: Dict[str, Any]
    sport_type: str = "general"

@plugin_router.post("/sports/analyze")
async def analyze_sports_movement(analysis_request: PoseAnalysisRequest):
    """Analyze movement using active sport plugins"""
    try:
        sport_plugins = get_sport_plugins()
        results = []
        
        for plugin in sport_plugins:
            if hasattr(plugin, 'analyze_movement'):
                try:
                    result = plugin.analyze_movement(analysis_request.pose_data)
                    results.append({
                        "plugin_id": plugin.manifest.id,
                        "plugin_name": plugin.manifest.name,
                        "analysis": result
                    })
                except Exception as e:
                    results.append({
                        "plugin_id": plugin.manifest.id,
                        "plugin_name": plugin.manifest.name,
                        "error": str(e)
                    })
        
        return JSONResponse(content={
            "sport_type": analysis_request.sport_type,
            "analyses": results,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@plugin_router.get("/sports/exercises/{plugin_id}")
async def get_sport_exercises(plugin_id: str):
    """Get exercise library from a sport plugin"""
    try:
        if plugin_id not in plugin_manager.plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not active")
        
        plugin = plugin_manager.plugins[plugin_id]
        if hasattr(plugin, 'get_exercise_library'):
            exercises = plugin.get_exercise_library()
            return JSONResponse(content={
                "plugin_id": plugin_id,
                "exercises": exercises
            })
        else:
            raise HTTPException(status_code=400, detail="Plugin does not provide exercise library")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include routers
app.include_router(health_router)
app.include_router(workout_router)
app.include_router(logging_router)
app.include_router(voice_router)
app.include_router(plugin_router)
app.include_router(store_router)
app.include_router(mobile_router)
app.include_router(ab_testing_router)
app.include_router(analytics_router)
app.include_router(monitoring_router)

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "message": "Check the API documentation for available endpoints"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Initialize plugin system
    print("🔌 Initializing Plugin System...")
    load_all_plugins()
    discovered = plugin_manager.discover_plugins()
    print(f"✅ Plugin system ready with {len(discovered)} available plugins")
    
    # Run the API server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development mode
        log_level="info"
    )