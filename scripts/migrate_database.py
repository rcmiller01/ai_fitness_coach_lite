#!/usr/bin/env python3
"""
Database Migration Script for AI Fitness Coach

Handles migration from JSON files to PostgreSQL production database.
Can be run standalone or as part of deployment process.
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager, DatabaseMigrator, DatabaseConfig, DatabaseType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def setup_database(config: DatabaseConfig) -> bool:
    """Setup and initialize database"""
    print("🔧 Setting up database...")
    
    db_manager = DatabaseManager(config)
    success = await db_manager.initialize()
    
    if success:
        print("✅ Database setup completed successfully!")
    else:
        print("❌ Database setup failed!")
    
    await db_manager.close()
    return success

async def migrate_data(config: DatabaseConfig, source_dir: str = "data") -> bool:
    """Migrate data from JSON to PostgreSQL"""
    print("🔄 Starting data migration...")
    
    # Update config with source directory
    config.json_data_dir = source_dir
    
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    
    migrator = DatabaseMigrator(db_manager)
    success = await migrator.migrate_json_to_postgres()
    
    await db_manager.close()
    return success

async def verify_migration(config: DatabaseConfig) -> bool:
    """Verify migration was successful"""
    print("🔍 Verifying migration...")
    
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    
    try:
        # Test user creation and retrieval
        test_user = {
            "user_id": "migration_test_user",
            "username": "Migration Test",
            "email": "test@example.com",
            "profile": {"test": True}
        }
        
        # Create test user
        await db_manager.create_user(test_user)
        
        # Retrieve test user
        retrieved_user = await db_manager.get_user("migration_test_user")
        
        if retrieved_user and retrieved_user["username"] == "Migration Test":
            print("✅ Database verification passed!")
            success = True
        else:
            print("❌ Database verification failed!")
            success = False
        
        # Cleanup test user
        if db_manager.session_factory:
            async with db_manager.session_factory() as session:
                from sqlalchemy.sql import text
                await session.execute(text("DELETE FROM users WHERE user_id = 'migration_test_user'"))
                await session.commit()
    
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        success = False
    
    await db_manager.close()
    return success

async def create_backup(config: DatabaseConfig, backup_dir: str = "backup") -> bool:
    """Create backup of current data"""
    print("💾 Creating data backup...")
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy JSON data if it exists
        import shutil
        if os.path.exists(config.json_data_dir):
            backup_path = os.path.join(backup_dir, f"json_backup_{int(asyncio.get_event_loop().time())}")
            shutil.copytree(config.json_data_dir, backup_path)
            print(f"✅ JSON data backed up to: {backup_path}")
        
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def load_config_from_env() -> DatabaseConfig:
    """Load database configuration from environment variables"""
    return DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "fitness_coach"),
        username=os.getenv("DB_USER", "fitness_user"),
        password=os.getenv("DB_PASSWORD", ""),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        json_data_dir=os.getenv("JSON_DATA_DIR", "data")
    )

async def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(description="AI Fitness Coach Database Migration")
    parser.add_argument("--action", choices=["setup", "migrate", "verify", "backup", "full"], 
                       default="full", help="Migration action to perform")
    parser.add_argument("--source-dir", default="data", help="Source JSON data directory")
    parser.add_argument("--backup-dir", default="backup", help="Backup directory")
    parser.add_argument("--config-file", help="Database configuration file")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config_file and os.path.exists(args.config_file):
        import json
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
        config = DatabaseConfig(**config_data)
    else:
        config = load_config_from_env()
    
    print("🚀 AI Fitness Coach Database Migration")
    print(f"   Database: {config.database}@{config.host}:{config.port}")
    print(f"   Action: {args.action}")
    print(f"   Source: {args.source_dir}")
    print()
    
    success = True
    
    if args.action in ["setup", "full"]:
        success &= await setup_database(config)
    
    if args.action in ["backup", "full"]:
        success &= await create_backup(config, args.backup_dir)
    
    if args.action in ["migrate", "full"]:
        success &= await migrate_data(config, args.source_dir)
    
    if args.action in ["verify", "full"]:
        success &= await verify_migration(config)
    
    if success:
        print("\n✅ Migration completed successfully!")
        return 0
    else:
        print("\n❌ Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))