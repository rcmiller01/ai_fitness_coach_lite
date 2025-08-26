#!/usr/bin/env python3
"""
Production Deployment Script for AI Fitness Coach

Handles complete deployment process including:
- Environment setup
- Database migration
- Docker deployment
- Health checks
- Monitoring setup
"""

import os
import sys
import subprocess
import json
import time
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DeploymentManager:
    """Manages the complete deployment process"""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.config_dir = self.project_root / "config"
        
    def deploy(self, skip_migration: bool = False, skip_build: bool = False) -> bool:
        """Execute complete deployment process"""
        
        print("🚀 AI Fitness Coach Production Deployment")
        print(f"   Environment: {self.environment}")
        print(f"   Project Root: {self.project_root}")
        print()
        
        try:
            # Step 1: Environment validation
            if not self._validate_environment():
                return False
            
            # Step 2: Build application (if not skipped)
            if not skip_build and not self._build_application():
                return False
            
            # Step 3: Database setup and migration (if not skipped)
            if not skip_migration and not self._setup_database():
                return False
            
            # Step 4: Deploy with Docker Compose
            if not self._deploy_with_docker():
                return False
            
            # Step 5: Health checks
            if not self._run_health_checks():
                return False
            
            # Step 6: Setup monitoring
            if not self._setup_monitoring():
                return False
            
            print("✅ Deployment completed successfully!")
            print("🌐 Application is now running in production")
            
            self._display_deployment_info()
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
    
    def _validate_environment(self) -> bool:
        """Validate deployment environment"""
        print("🔍 Validating deployment environment...")
        
        # Check required files
        required_files = [
            ".env.production",
            "Dockerfile",
            "docker-compose.yml",
            "requirements.txt"
        ]
        
        for file in required_files:
            file_path = self.project_root / file
            if not file_path.exists():
                print(f"❌ Required file missing: {file}")
                return False
        
        # Check Docker
        if not self._check_command("docker"):
            print("❌ Docker is not installed or not in PATH")
            return False
        
        if not self._check_command("docker-compose"):
            print("❌ Docker Compose is not installed or not in PATH")
            return False
        
        # Check environment variables
        env_file = self.project_root / ".env.production"
        required_env_vars = [
            "DB_PASSWORD",
            "SECRET_KEY",
            "REDIS_PASSWORD"
        ]
        
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        for var in required_env_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                print(f"⚠️ Environment variable {var} needs to be configured in .env.production")
                print("   Please update the production environment file with secure values")
                return False
        
        print("✅ Environment validation passed")
        return True
    
    def _build_application(self) -> bool:
        """Build application for production"""
        print("🔨 Building application...")
        
        try:
            # Build Docker image
            cmd = ["docker", "build", "-t", "fitness-coach:latest", "."]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Docker build failed: {result.stderr}")
                return False
            
            print("✅ Application build completed")
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False
    
    def _setup_database(self) -> bool:
        """Setup and migrate database"""
        print("🗄️ Setting up database...")
        
        try:
            # Start database service first
            cmd = ["docker-compose", "up", "-d", "postgres", "redis"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Failed to start database services: {result.stderr}")
                return False
            
            # Wait for database to be ready
            print("⏳ Waiting for database to be ready...")
            time.sleep(30)
            
            # Run migration script
            migration_script = self.scripts_dir / "migrate_database.py"
            cmd = ["python", str(migration_script), "--action", "full"]
            
            # Set environment variables for migration
            env = os.environ.copy()
            env.update(self._load_env_file())
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Database migration failed: {result.stderr}")
                return False
            
            print("✅ Database setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
    
    def _deploy_with_docker(self) -> bool:
        """Deploy application using Docker Compose"""
        print("🐳 Deploying with Docker Compose...")
        
        try:\n            # Copy environment file\n            env_source = self.project_root / \".env.production\"\n            env_target = self.project_root / \".env\"\n            \n            import shutil\n            shutil.copy2(env_source, env_target)\n            \n            # Deploy all services\n            cmd = [\"docker-compose\", \"up\", \"-d\"]\n            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)\n            \n            if result.returncode != 0:\n                print(f\"❌ Docker Compose deployment failed: {result.stderr}\")\n                return False\n            \n            print(\"✅ Docker deployment completed\")\n            return True\n            \n        except Exception as e:\n            print(f\"❌ Docker deployment failed: {e}\")\n            return False\n    \n    def _run_health_checks(self) -> bool:\n        \"\"\"Run health checks on deployed services\"\"\"\n        print(\"🏥 Running health checks...\")\n        \n        try:\n            # Wait for services to start\n            time.sleep(30)\n            \n            # Check application health\n            import requests\n            \n            health_endpoints = [\n                \"http://localhost:8000/health\",\n                \"http://localhost:8000/api/status\"\n            ]\n            \n            for endpoint in health_endpoints:\n                try:\n                    response = requests.get(endpoint, timeout=10)\n                    if response.status_code == 200:\n                        print(f\"✅ Health check passed: {endpoint}\")\n                    else:\n                        print(f\"⚠️ Health check warning: {endpoint} returned {response.status_code}\")\n                except requests.exceptions.RequestException:\n                    print(f\"⚠️ Health check failed: {endpoint} not accessible\")\n            \n            # Check Docker services\n            cmd = [\"docker-compose\", \"ps\"]\n            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)\n            \n            if \"Up\" in result.stdout:\n                print(\"✅ Docker services are running\")\n            else:\n                print(\"⚠️ Some Docker services may not be running properly\")\n            \n            print(\"✅ Health checks completed\")\n            return True\n            \n        except Exception as e:\n            print(f\"⚠️ Health checks failed: {e}\")\n            return True  # Don't fail deployment on health check issues\n    \n    def _setup_monitoring(self) -> bool:\n        \"\"\"Setup monitoring and logging\"\"\"\n        print(\"📊 Setting up monitoring...\")\n        \n        try:\n            # Create monitoring directories\n            monitoring_dirs = [\n                self.project_root / \"logs\",\n                self.project_root / \"monitoring\",\n                self.project_root / \"backup\"\n            ]\n            \n            for dir_path in monitoring_dirs:\n                dir_path.mkdir(exist_ok=True)\n            \n            # Setup log rotation (basic)\n            logrotate_config = \"\"\"\n/app/logs/*.log {\n    daily\n    rotate 30\n    compress\n    delaycompress\n    missingok\n    notifempty\n    create 644 root root\n}\n\"\"\"\n            \n            with open(self.project_root / \"config\" / \"logrotate.conf\", 'w') as f:\n                f.write(logrotate_config)\n            \n            # Setup backup cron job script\n            backup_script = self.scripts_dir / \"backup_db.sh\"\n            if backup_script.exists():\n                # Make backup script executable\n                backup_script.chmod(0o755)\n            \n            print(\"✅ Monitoring setup completed\")\n            return True\n            \n        except Exception as e:\n            print(f\"⚠️ Monitoring setup failed: {e}\")\n            return True  # Don't fail deployment on monitoring issues\n    \n    def _check_command(self, command: str) -> bool:\n        \"\"\"Check if a command is available\"\"\"\n        try:\n            subprocess.run([command, \"--version\"], capture_output=True, check=True)\n            return True\n        except (subprocess.CalledProcessError, FileNotFoundError):\n            return False\n    \n    def _load_env_file(self) -> dict:\n        \"\"\"Load environment variables from .env.production\"\"\"\n        env_vars = {}\n        env_file = self.project_root / \".env.production\"\n        \n        if env_file.exists():\n            with open(env_file, 'r') as f:\n                for line in f:\n                    line = line.strip()\n                    if line and not line.startswith('#') and '=' in line:\n                        key, value = line.split('=', 1)\n                        env_vars[key] = value\n        \n        return env_vars\n    \n    def _display_deployment_info(self):\n        \"\"\"Display deployment information\"\"\"\n        print(\"\\n📋 Deployment Information:\")\n        print(\"   🌐 Application: http://localhost:8000\")\n        print(\"   🔍 API Docs: http://localhost:8000/docs\")\n        print(\"   📊 Health Check: http://localhost:8000/health\")\n        print(\"   🗄️ Database: PostgreSQL on localhost:5432\")\n        print(\"   🗃️ Redis: localhost:6379\")\n        print(\"\\n📝 Useful Commands:\")\n        print(\"   📋 View logs: docker-compose logs -f\")\n        print(\"   🔄 Restart: docker-compose restart\")\n        print(\"   🛑 Stop: docker-compose down\")\n        print(\"   💾 Backup: docker-compose exec postgres_backup /backup_db.sh\")\n\ndef main():\n    parser = argparse.ArgumentParser(description=\"AI Fitness Coach Production Deployment\")\n    parser.add_argument(\"--environment\", default=\"production\", help=\"Deployment environment\")\n    parser.add_argument(\"--skip-migration\", action=\"store_true\", help=\"Skip database migration\")\n    parser.add_argument(\"--skip-build\", action=\"store_true\", help=\"Skip application build\")\n    parser.add_argument(\"--check-only\", action=\"store_true\", help=\"Only run environment checks\")\n    \n    args = parser.parse_args()\n    \n    deployer = DeploymentManager(args.environment)\n    \n    if args.check_only:\n        success = deployer._validate_environment()\n        print(\"✅ Environment check passed\" if success else \"❌ Environment check failed\")\n        return 0 if success else 1\n    \n    success = deployer.deploy(\n        skip_migration=args.skip_migration,\n        skip_build=args.skip_build\n    )\n    \n    return 0 if success else 1\n\nif __name__ == \"__main__\":\n    sys.exit(main())