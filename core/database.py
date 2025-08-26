"""
Database Management System for AI Fitness Coach

Provides production-ready database layer with PostgreSQL support,
data migrations, and connection management.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Database dependencies
try:
    import asyncpg
    import psycopg2
    from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.sql import text
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logging.warning("PostgreSQL dependencies not available. Using JSON fallback.")

class DatabaseType(Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    JSON_FILE = "json_file"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_type: DatabaseType = DatabaseType.JSON_FILE
    host: str = "localhost"
    port: int = 5432
    database: str = "fitness_coach"
    username: str = "fitness_user"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    json_data_dir: str = "data"

class DatabaseManager:
    """Production database management system"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.session_factory = None
        self.connection_pool = None
        self.Base = declarative_base() if POSTGRES_AVAILABLE else None
        
        # JSON fallback
        self.json_data_dir = config.json_data_dir
        os.makedirs(self.json_data_dir, exist_ok=True)
        
    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            if self.config.db_type == DatabaseType.POSTGRESQL and POSTGRES_AVAILABLE:
                return await self._initialize_postgresql()
            else:
                return self._initialize_json_fallback()
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            return False
    
    async def _initialize_postgresql(self) -> bool:
        """Initialize PostgreSQL connection"""
        try:
            # Create connection string
            connection_string = (
                f"postgresql+asyncpg://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )
            
            # Create async engine
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            
            self.engine = create_async_engine(
                connection_string,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=False
            )
            
            # Create async session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            await self._create_tables()
            
            logging.info("✅ PostgreSQL database initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"PostgreSQL initialization failed: {e}")
            return self._initialize_json_fallback()
    
    def _initialize_json_fallback(self) -> bool:
        """Initialize JSON file fallback"""
        try:
            # Create data directories
            os.makedirs(os.path.join(self.json_data_dir, "users"), exist_ok=True)
            os.makedirs(os.path.join(self.json_data_dir, "workouts"), exist_ok=True)
            os.makedirs(os.path.join(self.json_data_dir, "plugins"), exist_ok=True)
            os.makedirs(os.path.join(self.json_data_dir, "analytics"), exist_ok=True)
            
            logging.info("✅ JSON file database initialized successfully")
            return True
        except Exception as e:
            logging.error(f"JSON fallback initialization failed: {e}")
            return False
    
    async def _create_tables(self):
        """Create database tables"""
        if not POSTGRES_AVAILABLE or not self.engine:
            return
        
        async with self.engine.begin() as conn:
            # Create users table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    profile_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create workouts table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    workout_id VARCHAR(255) UNIQUE NOT NULL,
                    workout_type VARCHAR(100),
                    exercises JSONB,
                    metrics JSONB,
                    duration INTEGER,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create plugin_licenses table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS plugin_licenses (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    plugin_id VARCHAR(255) NOT NULL,
                    license_key VARCHAR(255) NOT NULL,
                    activation_date TIMESTAMP,
                    expiry_date TIMESTAMP,
                    trial_used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create analytics table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_analytics (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    event_data JSONB,
                    plugin_id VARCHAR(255),
                    session_id VARCHAR(255),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
    
    async def get_session(self):
        """Get database session"""
        if self.session_factory:
            return self.session_factory()
        return None
    
    # User Management
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._create_user_postgres(user_data)
        else:
            return self._create_user_json(user_data)
    
    async def _create_user_postgres(self, user_data: Dict[str, Any]) -> bool:
        """Create user in PostgreSQL"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("""
                    INSERT INTO users (user_id, username, email, profile_data)
                    VALUES (:user_id, :username, :email, :profile_data)
                """), {
                    "user_id": user_data["user_id"],
                    "username": user_data["username"],
                    "email": user_data.get("email"),
                    "profile_data": json.dumps(user_data.get("profile", {}))
                })
                await session.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to create user in PostgreSQL: {e}")
            return False
    
    def _create_user_json(self, user_data: Dict[str, Any]) -> bool:
        """Create user in JSON file"""
        try:
            user_file = os.path.join(self.json_data_dir, "users", f"{user_data['user_id']}.json")
            user_data["created_at"] = datetime.now().isoformat()
            user_data["updated_at"] = datetime.now().isoformat()
            
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to create user in JSON: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._get_user_postgres(user_id)
        else:
            return self._get_user_json(user_id)
    
    async def _get_user_postgres(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from PostgreSQL"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("""
                    SELECT user_id, username, email, profile_data, created_at, updated_at
                    FROM users WHERE user_id = :user_id
                """), {"user_id": user_id})
                
                row = result.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "profile": json.loads(row[3] or "{}"),
                        "created_at": row[4].isoformat() if row[4] else None,
                        "updated_at": row[5].isoformat() if row[5] else None
                    }
        except Exception as e:
            logging.error(f"Failed to get user from PostgreSQL: {e}")
        return None
    
    def _get_user_json(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from JSON file"""
        try:
            user_file = os.path.join(self.json_data_dir, "users", f"{user_id}.json")
            if os.path.exists(user_file):
                with open(user_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to get user from JSON: {e}")
        return None
    
    # Workout Management
    async def save_workout(self, workout_data: Dict[str, Any]) -> bool:
        """Save workout data"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._save_workout_postgres(workout_data)
        else:
            return self._save_workout_json(workout_data)
    
    async def _save_workout_postgres(self, workout_data: Dict[str, Any]) -> bool:
        """Save workout to PostgreSQL"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("""
                    INSERT INTO workouts (user_id, workout_id, workout_type, exercises, metrics, duration, started_at, completed_at)
                    VALUES (:user_id, :workout_id, :workout_type, :exercises, :metrics, :duration, :started_at, :completed_at)
                """), {
                    "user_id": workout_data["user_id"],
                    "workout_id": workout_data["workout_id"],
                    "workout_type": workout_data.get("workout_type"),
                    "exercises": json.dumps(workout_data.get("exercises", [])),
                    "metrics": json.dumps(workout_data.get("metrics", {})),
                    "duration": workout_data.get("duration"),
                    "started_at": workout_data.get("started_at"),
                    "completed_at": workout_data.get("completed_at")
                })
                await session.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to save workout to PostgreSQL: {e}")
            return False
    
    def _save_workout_json(self, workout_data: Dict[str, Any]) -> bool:
        """Save workout to JSON file"""
        try:
            workout_file = os.path.join(self.json_data_dir, "workouts", f"{workout_data['workout_id']}.json")
            workout_data["created_at"] = datetime.now().isoformat()
            
            with open(workout_file, 'w') as f:
                json.dump(workout_data, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to save workout to JSON: {e}")
            return False
    
    async def get_user_workouts(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user workouts"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._get_user_workouts_postgres(user_id, limit)
        else:
            return self._get_user_workouts_json(user_id, limit)
    
    async def _get_user_workouts_postgres(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get user workouts from PostgreSQL"""
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("""
                    SELECT workout_id, workout_type, exercises, metrics, duration, started_at, completed_at, created_at
                    FROM workouts WHERE user_id = :user_id
                    ORDER BY created_at DESC LIMIT :limit
                """), {"user_id": user_id, "limit": limit})
                
                workouts = []
                for row in result.fetchall():
                    workouts.append({
                        "workout_id": row[0],
                        "workout_type": row[1],
                        "exercises": json.loads(row[2] or "[]"),
                        "metrics": json.loads(row[3] or "{}"),
                        "duration": row[4],
                        "started_at": row[5].isoformat() if row[5] else None,
                        "completed_at": row[6].isoformat() if row[6] else None,
                        "created_at": row[7].isoformat() if row[7] else None
                    })
                return workouts
        except Exception as e:
            logging.error(f"Failed to get workouts from PostgreSQL: {e}")
        return []
    
    def _get_user_workouts_json(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get user workouts from JSON files"""
        try:
            workouts = []
            workout_dir = os.path.join(self.json_data_dir, "workouts")
            
            for filename in os.listdir(workout_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(workout_dir, filename), 'r') as f:
                        workout = json.load(f)
                        if workout.get("user_id") == user_id:
                            workouts.append(workout)
            
            # Sort by created_at and limit
            workouts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return workouts[:limit]
        except Exception as e:
            logging.error(f"Failed to get workouts from JSON: {e}")
        return []
    
    # Plugin License Management
    async def save_plugin_license(self, license_data: Dict[str, Any]) -> bool:
        """Save plugin license"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._save_license_postgres(license_data)
        else:
            return self._save_license_json(license_data)
    
    async def _save_license_postgres(self, license_data: Dict[str, Any]) -> bool:
        """Save license to PostgreSQL"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("""
                    INSERT INTO plugin_licenses (user_id, plugin_id, license_key, activation_date, expiry_date, trial_used)
                    VALUES (:user_id, :plugin_id, :license_key, :activation_date, :expiry_date, :trial_used)
                    ON CONFLICT (user_id, plugin_id) DO UPDATE SET
                        license_key = EXCLUDED.license_key,
                        activation_date = EXCLUDED.activation_date,
                        expiry_date = EXCLUDED.expiry_date,
                        trial_used = EXCLUDED.trial_used
                """), license_data)
                await session.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to save license to PostgreSQL: {e}")
            return False
    
    def _save_license_json(self, license_data: Dict[str, Any]) -> bool:
        """Save license to JSON file"""
        try:
            license_file = os.path.join(self.json_data_dir, "plugins", "licenses.json")
            
            licenses = {}
            if os.path.exists(license_file):
                with open(license_file, 'r') as f:
                    licenses = json.load(f)
            
            user_id = license_data["user_id"]
            plugin_id = license_data["plugin_id"]
            
            if user_id not in licenses:
                licenses[user_id] = {}
            
            licenses[user_id][plugin_id] = license_data
            
            with open(license_file, 'w') as f:
                json.dump(licenses, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to save license to JSON: {e}")
            return False
    
    # Analytics
    async def log_analytics_event(self, event_data: Dict[str, Any]) -> bool:
        """Log analytics event"""
        if self.config.db_type == DatabaseType.POSTGRESQL and self.session_factory:
            return await self._log_analytics_postgres(event_data)
        else:
            return self._log_analytics_json(event_data)
    
    async def _log_analytics_postgres(self, event_data: Dict[str, Any]) -> bool:
        """Log analytics to PostgreSQL"""
        try:
            async with self.session_factory() as session:
                await session.execute(text("""
                    INSERT INTO user_analytics (user_id, event_type, event_data, plugin_id, session_id)
                    VALUES (:user_id, :event_type, :event_data, :plugin_id, :session_id)
                """), {
                    "user_id": event_data["user_id"],
                    "event_type": event_data["event_type"],
                    "event_data": json.dumps(event_data.get("event_data", {})),
                    "plugin_id": event_data.get("plugin_id"),
                    "session_id": event_data.get("session_id")
                })
                await session.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to log analytics to PostgreSQL: {e}")
            return False
    
    def _log_analytics_json(self, event_data: Dict[str, Any]) -> bool:
        """Log analytics to JSON file"""
        try:
            analytics_file = os.path.join(self.json_data_dir, "analytics", f"{datetime.now().strftime('%Y-%m-%d')}.json")
            
            events = []
            if os.path.exists(analytics_file):
                with open(analytics_file, 'r') as f:
                    events = json.load(f)
            
            event_data["timestamp"] = datetime.now().isoformat()
            events.append(event_data)
            
            with open(analytics_file, 'w') as f:
                json.dump(events, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to log analytics to JSON: {e}")
            return False
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()

# Migration utilities
class DatabaseMigrator:
    """Database migration utilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def migrate_json_to_postgres(self) -> bool:
        """Migrate data from JSON files to PostgreSQL"""
        if not POSTGRES_AVAILABLE:
            logging.error("PostgreSQL not available for migration")
            return False
        
        try:
            logging.info("🔄 Starting JSON to PostgreSQL migration...")
            
            # Migrate users
            await self._migrate_users()
            
            # Migrate workouts
            await self._migrate_workouts()
            
            # Migrate plugin licenses
            await self._migrate_licenses()
            
            # Migrate analytics
            await self._migrate_analytics()
            
            logging.info("✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            logging.error(f"Migration failed: {e}")
            return False
    
    async def _migrate_users(self):
        """Migrate user data"""
        users_dir = os.path.join(self.db_manager.json_data_dir, "users")
        if not os.path.exists(users_dir):
            return
        
        for filename in os.listdir(users_dir):
            if filename.endswith('.json'):
                with open(os.path.join(users_dir, filename), 'r') as f:
                    user_data = json.load(f)
                    await self.db_manager._create_user_postgres(user_data)
        
        logging.info("✅ User migration completed")
    
    async def _migrate_workouts(self):
        """Migrate workout data"""
        workouts_dir = os.path.join(self.db_manager.json_data_dir, "workouts")
        if not os.path.exists(workouts_dir):
            return
        
        for filename in os.listdir(workouts_dir):
            if filename.endswith('.json'):
                with open(os.path.join(workouts_dir, filename), 'r') as f:
                    workout_data = json.load(f)
                    await self.db_manager._save_workout_postgres(workout_data)
        
        logging.info("✅ Workout migration completed")
    
    async def _migrate_licenses(self):
        """Migrate license data"""
        license_file = os.path.join(self.db_manager.json_data_dir, "plugins", "licenses.json")
        if not os.path.exists(license_file):
            return
        
        with open(license_file, 'r') as f:
            licenses = json.load(f)
        
        for user_id, user_licenses in licenses.items():
            for plugin_id, license_data in user_licenses.items():
                license_data["user_id"] = user_id
                license_data["plugin_id"] = plugin_id
                await self.db_manager._save_license_postgres(license_data)
        
        logging.info("✅ License migration completed")
    
    async def _migrate_analytics(self):
        """Migrate analytics data"""
        analytics_dir = os.path.join(self.db_manager.json_data_dir, "analytics")
        if not os.path.exists(analytics_dir):
            return
        
        for filename in os.listdir(analytics_dir):
            if filename.endswith('.json'):
                with open(os.path.join(analytics_dir, filename), 'r') as f:
                    events = json.load(f)
                    for event in events:
                        await self.db_manager._log_analytics_postgres(event)
        
        logging.info("✅ Analytics migration completed")

# Database factory
def create_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Create database manager with configuration"""
    if config is None:
        # Default configuration
        db_type = DatabaseType.POSTGRESQL if POSTGRES_AVAILABLE else DatabaseType.JSON_FILE
        config = DatabaseConfig(
            db_type=db_type,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "fitness_coach"),
            username=os.getenv("DB_USER", "fitness_user"),
            password=os.getenv("DB_PASSWORD", ""),
            json_data_dir=os.getenv("DATA_DIR", "data")
        )
    
    return DatabaseManager(config)