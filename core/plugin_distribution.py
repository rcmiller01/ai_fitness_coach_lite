"""
Plugin Distribution System for AI Fitness Coach

Handles plugin packaging, distribution, downloads, and updates.
Integrates with cloud storage for secure plugin delivery.
"""

import os
import json
import zipfile
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, BinaryIO
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import tempfile
import shutil

from .cloud_storage import CloudStorageManager, StorageConfig

@dataclass
class PluginPackage:
    """Plugin package information"""
    plugin_id: str
    version: str
    size: int
    checksum: str
    download_url: str
    manifest: Dict[str, Any]
    dependencies: List[str]
    created_at: str
    updated_at: str

@dataclass
class PluginDownload:
    """Plugin download record"""
    download_id: str
    user_id: str
    plugin_id: str
    version: str
    download_started: str
    download_completed: Optional[str] = None
    download_size: int = 0
    status: str = "pending"  # pending, downloading, completed, failed
    error_message: Optional[str] = None

class PluginDistributionManager:
    """Manages plugin packaging and distribution"""
    
    def __init__(self, storage_manager: CloudStorageManager, plugins_dir: str = "plugins"):
        self.storage_manager = storage_manager
        self.plugins_dir = Path(plugins_dir)
        self.packages_cache = {}
        self.download_records = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize directories
        self.temp_dir = Path(tempfile.gettempdir()) / "fitness_coach_plugins"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def package_plugin(self, plugin_id: str, plugin_path: str, version: str = None) -> Optional[PluginPackage]:
        """Package a plugin for distribution"""
        try:
            plugin_path = Path(plugin_path)
            
            if not plugin_path.exists():
                self.logger.error(f"Plugin path does not exist: {plugin_path}")
                return None
            
            # Load manifest
            manifest_file = plugin_path / "manifest.json"
            if not manifest_file.exists():
                self.logger.error(f"Plugin manifest not found: {manifest_file}")
                return None
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Use version from manifest if not provided
            if version is None:
                version = manifest.get("version", "1.0.0")
            
            # Create package
            package_filename = f"{plugin_id}_v{version}.zip"
            package_path = self.temp_dir / package_filename
            
            # Create zip package
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in plugin_path.rglob('*'):
                    if file_path.is_file():
                        # Skip hidden files and cache
                        if file_path.name.startswith('.') or '__pycache__' in str(file_path):
                            continue
                        
                        arcname = file_path.relative_to(plugin_path)
                        zipf.write(file_path, arcname)
            
            # Calculate checksum
            with open(package_path, 'rb') as f:
                package_data = f.read()
                checksum = hashlib.sha256(package_data).hexdigest()
            
            # Upload to cloud storage
            storage_key = self.storage_manager.get_plugin_download_path(plugin_id, version)
            
            upload_success = await self.storage_manager.upload_file(
                package_data,
                storage_key,
                "application/zip",
                metadata={
                    "plugin_id": plugin_id,
                    "version": version,
                    "checksum": checksum,
                    "manifest": json.dumps(manifest)
                }
            )
            
            if not upload_success:
                self.logger.error(f"Failed to upload plugin package: {plugin_id}")
                return None
            
            # Generate download URL
            download_url = await self.storage_manager.generate_presigned_url(
                storage_key, expiration=3600
            )
            
            # Create package record
            package = PluginPackage(
                plugin_id=plugin_id,
                version=version,
                size=len(package_data),
                checksum=checksum,
                download_url=download_url or f"/api/plugins/{plugin_id}/download/{version}",
                manifest=manifest,
                dependencies=manifest.get("dependencies", []),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Cache package info
            self.packages_cache[f"{plugin_id}_{version}"] = package
            
            # Cleanup temp file
            package_path.unlink()
            
            self.logger.info(f"✅ Plugin packaged successfully: {plugin_id} v{version}")
            return package
            
        except Exception as e:
            self.logger.error(f"Plugin packaging failed: {e}")
            return None
    
    async def get_available_plugins(self) -> List[PluginPackage]:
        """Get list of available plugins for download"""
        try:
            plugins = []
            
            # List plugin packages in storage
            plugin_files = await self.storage_manager.list_files("plugins/downloads/")
            
            for file_obj in plugin_files:
                if file_obj.key.endswith('.zip'):
                    # Parse plugin ID and version from filename
                    filename = Path(file_obj.key).name
                    if '_v' in filename:
                        plugin_id, version_part = filename.replace('.zip', '').split('_v', 1)
                        
                        # Get file info with metadata
                        file_info = await self.storage_manager.get_file_info(file_obj.key)
                        
                        if file_info and file_info.metadata:
                            manifest_str = file_info.metadata.get('manifest')
                            if manifest_str:
                                manifest = json.loads(manifest_str)
                                
                                # Generate download URL
                                download_url = await self.storage_manager.generate_presigned_url(
                                    file_obj.key, expiration=3600
                                )
                                
                                package = PluginPackage(
                                    plugin_id=plugin_id,
                                    version=version_part,
                                    size=file_info.size,
                                    checksum=file_info.metadata.get('checksum', ''),
                                    download_url=download_url or f"/api/plugins/{plugin_id}/download/{version_part}",
                                    manifest=manifest,
                                    dependencies=manifest.get("dependencies", []),
                                    created_at=file_info.metadata.get('uploaded_at', file_info.last_modified.isoformat()),
                                    updated_at=file_info.last_modified.isoformat()
                                )
                                
                                plugins.append(package)
            
            return plugins
            
        except Exception as e:
            self.logger.error(f"Failed to get available plugins: {e}")
            return []
    
    async def get_plugin_package(self, plugin_id: str, version: str = None) -> Optional[PluginPackage]:
        """Get specific plugin package information"""
        try:
            # Check cache first
            cache_key = f"{plugin_id}_{version}" if version else plugin_id
            if cache_key in self.packages_cache:
                return self.packages_cache[cache_key]
            
            # Search in available plugins
            available_plugins = await self.get_available_plugins()
            
            for package in available_plugins:
                if package.plugin_id == plugin_id:
                    if version is None or package.version == version:
                        self.packages_cache[cache_key] = package
                        return package
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get plugin package: {e}")
            return None
    
    async def initiate_plugin_download(self, user_id: str, plugin_id: str, version: str) -> Optional[PluginDownload]:
        """Initiate plugin download for a user"""
        try:
            # Check if plugin package exists
            package = await self.get_plugin_package(plugin_id, version)
            if not package:
                self.logger.error(f"Plugin package not found: {plugin_id} v{version}")
                return None
            
            # Create download record
            download_id = f"{user_id}_{plugin_id}_{version}_{int(datetime.now().timestamp())}"
            
            download_record = PluginDownload(
                download_id=download_id,
                user_id=user_id,
                plugin_id=plugin_id,
                version=version,
                download_started=datetime.now().isoformat(),
                status="pending"
            )
            
            # Store download record
            self.download_records[download_id] = download_record
            
            # Start download process
            asyncio.create_task(self._process_plugin_download(download_record, package))
            
            return download_record
            
        except Exception as e:
            self.logger.error(f"Failed to initiate plugin download: {e}")
            return None
    
    async def _process_plugin_download(self, download_record: PluginDownload, package: PluginPackage):
        """Process plugin download in background"""
        try:
            download_record.status = "downloading"
            
            # Download plugin package from storage
            storage_key = self.storage_manager.get_plugin_download_path(
                package.plugin_id, package.version
            )
            
            plugin_data = await self.storage_manager.download_file(storage_key)
            
            if not plugin_data:
                download_record.status = "failed"
                download_record.error_message = "Failed to download plugin package"
                return
            
            # Verify checksum
            actual_checksum = hashlib.sha256(plugin_data).hexdigest()
            if actual_checksum != package.checksum:
                download_record.status = "failed"
                download_record.error_message = "Package checksum mismatch"
                return
            
            # Store user's plugin copy
            user_plugin_key = self.storage_manager.get_user_data_path(
                download_record.user_id,
                f"plugins/{package.plugin_id}_v{package.version}.zip"
            )
            
            upload_success = await self.storage_manager.upload_file(
                plugin_data,
                user_plugin_key,
                "application/zip",
                metadata={
                    "download_id": download_record.download_id,
                    "original_checksum": package.checksum,
                    "download_date": datetime.now().isoformat()
                }
            )
            
            if upload_success:
                download_record.status = "completed"
                download_record.download_completed = datetime.now().isoformat()
                download_record.download_size = len(plugin_data)
                
                self.logger.info(f"✅ Plugin download completed: {package.plugin_id} for user {download_record.user_id}")
            else:
                download_record.status = "failed"
                download_record.error_message = "Failed to store user plugin copy"
            
        except Exception as e:
            download_record.status = "failed"
            download_record.error_message = str(e)
            self.logger.error(f"Plugin download processing failed: {e}")
    
    async def get_download_status(self, download_id: str) -> Optional[PluginDownload]:
        """Get download status"""
        return self.download_records.get(download_id)
    
    async def get_user_plugins(self, user_id: str) -> List[Dict[str, Any]]:
        """Get plugins downloaded by a user"""
        try:
            user_plugins = []
            
            # List user's plugin files
            user_plugin_prefix = f"users/{user_id}/data/plugins/"
            plugin_files = await self.storage_manager.list_files(user_plugin_prefix)
            
            for file_obj in plugin_files:
                if file_obj.key.endswith('.zip'):
                    # Parse plugin info from filename
                    filename = Path(file_obj.key).name
                    if '_v' in filename:
                        plugin_id, version_part = filename.replace('.zip', '').split('_v', 1)
                        
                        # Get file metadata
                        file_info = await self.storage_manager.get_file_info(file_obj.key)
                        
                        user_plugins.append({
                            "plugin_id": plugin_id,
                            "version": version_part,
                            "download_date": file_info.metadata.get('download_date') if file_info.metadata else None,
                            "size": file_obj.size,
                            "status": "installed"
                        })
            
            return user_plugins
            
        except Exception as e:
            self.logger.error(f"Failed to get user plugins: {e}")
            return []
    
    async def install_plugin(self, user_id: str, plugin_id: str, version: str, target_dir: str) -> bool:
        """Install plugin for a user"""
        try:
            # Get user's plugin file
            user_plugin_key = self.storage_manager.get_user_data_path(
                user_id,
                f"plugins/{plugin_id}_v{version}.zip"
            )
            
            plugin_data = await self.storage_manager.download_file(user_plugin_key)
            
            if not plugin_data:
                self.logger.error(f"User plugin file not found: {user_plugin_key}")
                return False
            
            # Extract plugin to target directory
            target_path = Path(target_dir) / plugin_id
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Create temporary zip file
            temp_zip_path = self.temp_dir / f"{plugin_id}_install.zip"
            
            with open(temp_zip_path, 'wb') as f:
                f.write(plugin_data)
            
            # Extract zip file
            with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
                zipf.extractall(target_path)
            
            # Cleanup temp file
            temp_zip_path.unlink()
            
            self.logger.info(f"✅ Plugin installed successfully: {plugin_id} v{version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Plugin installation failed: {e}")
            return False
    
    async def check_plugin_updates(self, user_id: str) -> List[Dict[str, Any]]:
        """Check for plugin updates for a user"""
        try:
            updates_available = []
            
            # Get user's installed plugins
            user_plugins = await self.get_user_plugins(user_id)
            
            # Get available plugins
            available_plugins = await self.get_available_plugins()
            
            # Check for updates
            for user_plugin in user_plugins:
                plugin_id = user_plugin["plugin_id"]
                current_version = user_plugin["version"]
                
                # Find latest version in available plugins
                latest_version = None
                latest_package = None
                
                for package in available_plugins:
                    if package.plugin_id == plugin_id:
                        if latest_version is None or self._compare_versions(package.version, latest_version) > 0:
                            latest_version = package.version
                            latest_package = package
                
                # Check if update is available
                if latest_version and self._compare_versions(latest_version, current_version) > 0:
                    updates_available.append({
                        "plugin_id": plugin_id,
                        "current_version": current_version,
                        "latest_version": latest_version,
                        "package_info": asdict(latest_package) if latest_package else None
                    })
            
            return updates_available
            
        except Exception as e:
            self.logger.error(f"Failed to check plugin updates: {e}")
            return []
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings (simple implementation)"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            
            return 0
            
        except Exception:
            # Fallback to string comparison
            return 1 if version1 > version2 else (-1 if version1 < version2 else 0)
    
    async def cleanup_old_downloads(self, retention_days: int = 30):
        """Cleanup old download records and temp files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Cleanup download records
            to_remove = []
            for download_id, record in self.download_records.items():
                record_date = datetime.fromisoformat(record.download_started)
                if record_date < cutoff_date:
                    to_remove.append(download_id)
            
            for download_id in to_remove:
                del self.download_records[download_id]
            
            # Cleanup temp directory
            for temp_file in self.temp_dir.glob('*'):
                if temp_file.is_file():
                    file_age = datetime.now() - datetime.fromtimestamp(temp_file.stat().st_mtime)
                    if file_age.days > 1:  # Remove temp files older than 1 day
                        temp_file.unlink()
            
            self.logger.info(f"✅ Cleaned up {len(to_remove)} old download records")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

# Plugin marketplace integration
class PluginMarketplace:
    """Plugin marketplace interface"""
    
    def __init__(self, distribution_manager: PluginDistributionManager):
        self.distribution_manager = distribution_manager
        self.logger = logging.getLogger(__name__)
    
    async def get_featured_plugins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured plugins for marketplace"""
        try:
            all_plugins = await self.distribution_manager.get_available_plugins()
            
            # Sort by some criteria (e.g., popularity, rating)
            # For now, just return most recent
            sorted_plugins = sorted(all_plugins, key=lambda x: x.updated_at, reverse=True)
            
            featured = []
            for package in sorted_plugins[:limit]:
                featured.append({
                    "plugin_id": package.plugin_id,
                    "name": package.manifest.get("name", package.plugin_id),
                    "description": package.manifest.get("description", ""),
                    "version": package.version,
                    "price": package.manifest.get("price", 0),
                    "rating": 4.5,  # Mock rating
                    "downloads": 1000,  # Mock download count
                    "icon": package.manifest.get("icon", "default_icon.png"),
                    "screenshots": package.manifest.get("screenshots", []),
                    "tags": package.manifest.get("tags", [])
                })
            
            return featured
            
        except Exception as e:
            self.logger.error(f"Failed to get featured plugins: {e}")
            return []
    
    async def search_plugins(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Search plugins in marketplace"""
        try:
            all_plugins = await self.distribution_manager.get_available_plugins()
            
            results = []
            query_lower = query.lower()
            
            for package in all_plugins:
                manifest = package.manifest
                
                # Check if query matches
                name_match = query_lower in manifest.get("name", "").lower()
                desc_match = query_lower in manifest.get("description", "").lower()
                tag_match = any(query_lower in tag.lower() for tag in manifest.get("tags", []))
                
                if name_match or desc_match or tag_match:
                    # Check category filter
                    if category is None or manifest.get("plugin_type") == category:
                        results.append({
                            "plugin_id": package.plugin_id,
                            "name": manifest.get("name", package.plugin_id),
                            "description": manifest.get("description", ""),
                            "version": package.version,
                            "price": manifest.get("price", 0),
                            "category": manifest.get("plugin_type", ""),
                            "tags": manifest.get("tags", [])
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Plugin search failed: {e}")
            return []

# Factory function
def create_plugin_distribution_manager(storage_manager: CloudStorageManager, plugins_dir: str = "plugins") -> PluginDistributionManager:
    """Create plugin distribution manager"""
    return PluginDistributionManager(storage_manager, plugins_dir)

# Usage example
async def test_plugin_distribution():
    """Test plugin distribution system"""
    from .cloud_storage import create_storage_manager
    
    # Create storage manager
    storage_manager = create_storage_manager()
    await storage_manager.initialize()
    
    # Create distribution manager
    dist_manager = create_plugin_distribution_manager(storage_manager)
    
    # Test getting available plugins
    plugins = await dist_manager.get_available_plugins()
    print(f"Available plugins: {len(plugins)}")
    
    # Test marketplace
    marketplace = PluginMarketplace(dist_manager)
    featured = await marketplace.get_featured_plugins()
    print(f"Featured plugins: {len(featured)}")

if __name__ == "__main__":
    asyncio.run(test_plugin_distribution())