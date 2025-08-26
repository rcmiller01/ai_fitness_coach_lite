"""
Plugin Architecture System for AI Fitness Coach

Provides a flexible plugin system for sports-specific modules and extensions.
Supports discovery, loading, licensing, and integration of premium modules.
"""

import json
import os
import importlib
import importlib.util
import inspect
from typing import Dict, List, Any, Optional, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib

class PluginType(Enum):
    """Types of plugins"""
    SPORT_ANALYSIS = "sport_analysis"
    EXERCISE_LIBRARY = "exercise_library"
    NUTRITION_ADDON = "nutrition_addon"
    INTEGRATION = "integration"
    UI_THEME = "ui_theme"

class PluginStatus(Enum):
    """Plugin activation status"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    ERROR = "error"

@dataclass
class PluginManifest:
    """Plugin manifest data structure"""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    price: float = 0.0  # USD, 0 for free
    trial_days: int = 0  # 0 for no trial
    requires_core_version: str = "1.0.0"
    dependencies: List[str] = None
    permissions: List[str] = None
    entry_point: str = "main.py"
    icon: str = "icon.png"
    screenshots: List[str] = None
    tags: List[str] = None
    created_date: str = ""
    updated_date: str = ""

@dataclass
class PluginLicense:
    """Plugin license and activation data"""
    plugin_id: str
    license_key: str
    activation_date: str
    expiry_date: Optional[str] = None
    device_id: str = ""
    trial_used: bool = False
    activation_count: int = 0
    max_activations: int = 1

class BasePlugin(ABC):
    """Base class for all plugins"""
    
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self.is_loaded = False
        self.config = {}
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
    
    @abstractmethod
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """Return API routes this plugin provides"""
        pass
    
    @abstractmethod
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Return UI components this plugin provides"""
        pass
    
    def cleanup(self):
        """Cleanup when plugin is unloaded"""
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for this plugin"""
        return {}
    
    def update_config(self, config: Dict[str, Any]):
        """Update plugin configuration"""
        self.config.update(config)

class SportPlugin(BasePlugin):
    """Base class for sport-specific plugins"""
    
    @abstractmethod
    def analyze_movement(self, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sport-specific movement from pose data"""
        pass
    
    @abstractmethod
    def get_coaching_tips(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate coaching tips based on analysis"""
        pass
    
    @abstractmethod
    def get_exercise_library(self) -> List[Dict[str, Any]]:
        """Return sport-specific exercises"""
        pass

class PluginManager:
    """
    Central plugin management system
    """
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, BasePlugin] = {}
        self.manifests: Dict[str, PluginManifest] = {}
        self.licenses: Dict[str, PluginLicense] = {}
        
        # Initialize directories
        self.setup_directories()
        self.load_licenses()
    
    def setup_directories(self):
        """Create necessary plugin directories"""
        os.makedirs(self.plugins_dir, exist_ok=True)
        os.makedirs(os.path.join(self.plugins_dir, "core"), exist_ok=True)
        os.makedirs(os.path.join(self.plugins_dir, "sports"), exist_ok=True)
        os.makedirs(os.path.join(self.plugins_dir, "data"), exist_ok=True)
    
    def discover_plugins(self) -> List[PluginManifest]:
        """Discover all available plugins"""
        discovered = []
        
        for root, dirs, files in os.walk(self.plugins_dir):
            if "manifest.json" in files:
                manifest_path = os.path.join(root, "manifest.json")
                try:
                    manifest = self.load_manifest(manifest_path)
                    if manifest:
                        discovered.append(manifest)
                        self.manifests[manifest.id] = manifest
                except Exception as e:
                    print(f"Error loading manifest {manifest_path}: {e}")
        
        return discovered
    
    def load_manifest(self, manifest_path: str) -> Optional[PluginManifest]:
        """Load plugin manifest from file"""
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
            
            # Convert string enum values
            data['plugin_type'] = PluginType(data['plugin_type'])
            
            # Handle optional fields
            data.setdefault('dependencies', [])
            data.setdefault('permissions', [])
            data.setdefault('screenshots', [])
            data.setdefault('tags', [])
            
            return PluginManifest(**data)
            
        except Exception as e:
            print(f"Error loading manifest: {e}")
            return None
    
    def install_plugin(self, plugin_path: str) -> bool:
        """Install a plugin from a zip file or directory"""
        # This would handle plugin installation
        # For now, assume plugins are already in the plugins directory
        return True
    
    def load_plugin(self, plugin_id: str) -> bool:
        """Load and initialize a specific plugin"""
        
        if plugin_id in self.plugins:
            return True  # Already loaded
        
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            print(f"Plugin {plugin_id} not found")
            return False
        
        # Check license
        if not self.check_license(plugin_id):
            print(f"Plugin {plugin_id} license check failed")
            return False
        
        try:
            # Dynamically import plugin
            plugin_dir = self.get_plugin_directory(plugin_id)
            entry_point = os.path.join(plugin_dir, manifest.entry_point)
            
            if not os.path.exists(entry_point):
                print(f"Plugin entry point not found: {entry_point}")
                return False
            
            # Import the plugin module
            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", entry_point)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin and 
                    obj != SportPlugin):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                print(f"No valid plugin class found in {entry_point}")
                return False
            
            # Instantiate and initialize
            plugin_instance = plugin_class(manifest)
            if plugin_instance.initialize():
                self.plugins[plugin_id] = plugin_instance
                print(f"✅ Plugin {plugin_id} loaded successfully")
                return True
            else:
                print(f"Plugin {plugin_id} initialization failed")
                return False
                
        except Exception as e:
            print(f"Error loading plugin {plugin_id}: {e}")
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].cleanup()
            del self.plugins[plugin_id]
            print(f"Plugin {plugin_id} unloaded")
            return True
        return False
    
    def get_plugin_directory(self, plugin_id: str) -> str:
        """Get the directory path for a plugin"""
        # Simple implementation - plugins are in subdirectories named by ID
        return os.path.join(self.plugins_dir, "sports", plugin_id)
    
    def check_license(self, plugin_id: str) -> bool:
        """Check if plugin license is valid"""
        
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            return False
        
        # Free plugins always pass
        if manifest.price == 0.0:
            return True
        
        license_data = self.licenses.get(plugin_id)
        if not license_data:
            # Check if trial is available
            if manifest.trial_days > 0:
                return self.start_trial(plugin_id)
            return False
        
        # Validate with license server if online
        if self._is_online():
            return self._validate_license_online(plugin_id, license_data)
        
        # Offline validation
        return self._validate_license_offline(license_data)
    
    def _is_online(self) -> bool:
        """Check if we have internet connectivity"""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=1)
            return True
        except:
            return False
    
    def _validate_license_online(self, plugin_id: str, license_data: PluginLicense) -> bool:
        """Validate license with online server"""
        try:
            from .license_server import simulate_online_validation
            
            device_id = self.get_device_id()
            result = simulate_online_validation(license_data.license_key, device_id)
            
            if result['success']:
                # Update local license data with server response
                server_data = result['data']
                if 'expiry_date' in server_data:
                    license_data.expiry_date = server_data['expiry_date']
                self.save_licenses()
                return True
            else:
                print(f"❌ Online license validation failed: {result['data'].get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"⚠️ Online validation failed, using offline: {e}")
            return self._validate_license_offline(license_data)
    
    def _validate_license_offline(self, license_data: PluginLicense) -> bool:
        """Validate license offline"""
        
        # Check expiry
        if license_data.expiry_date:
            expiry = datetime.fromisoformat(license_data.expiry_date)
            if datetime.now() > expiry:
                print(f"❌ License expired: {license_data.expiry_date}")
                return False
        
        # Check device ID (basic anti-piracy)
        if license_data.device_id != self.get_device_id():
            print("❌ License not valid for this device")
            return False
        
        return True
    
    def start_trial(self, plugin_id: str) -> bool:
        """Start a trial for a plugin"""
        
        manifest = self.manifests.get(plugin_id)
        if not manifest or manifest.trial_days == 0:
            print(f"❌ No trial available for {plugin_id}")
            return False
        
        # Check if trial already used
        license_data = self.licenses.get(plugin_id)
        if license_data and license_data.trial_used:
            print(f"❌ Trial already used for {plugin_id}")
            return False
        
        # Try online trial generation first
        if self._is_online():
            return self._start_trial_online(plugin_id, manifest.trial_days)
        else:
            return self._start_trial_offline(plugin_id, manifest.trial_days)
    
    def _start_trial_online(self, plugin_id: str, trial_days: int) -> bool:
        """Start trial using online server"""
        try:
            from .license_server import license_server
            
            device_id = self.get_device_id()
            success, trial_info = license_server.generate_trial_license(plugin_id, device_id, trial_days)
            
            if success:
                # Create local trial license
                trial_license = PluginLicense(
                    plugin_id=plugin_id,
                    license_key=trial_info['trial_license_key'],
                    activation_date=datetime.now().isoformat(),
                    expiry_date=trial_info['expiry_date'],
                    device_id=device_id,
                    trial_used=True
                )
                
                self.licenses[plugin_id] = trial_license
                self.save_licenses()
                
                print(f"✅ Trial started for {plugin_id} ({trial_days} days)")
                print(f"   Expires: {trial_info['expiry_date']}")
                print(f"   Features: {trial_info['features']}")
                return True
            else:
                print(f"❌ Trial generation failed: {trial_info.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"⚠️ Online trial failed: {e}")
            return self._start_trial_offline(plugin_id, trial_days)
    
    def _start_trial_offline(self, plugin_id: str, trial_days: int) -> bool:
        """Start trial offline"""
        
        # Create offline trial license
        trial_license = PluginLicense(
            plugin_id=plugin_id,
            license_key="OFFLINE_TRIAL",
            activation_date=datetime.now().isoformat(),
            expiry_date=(datetime.now() + timedelta(days=trial_days)).isoformat(),
            device_id=self.get_device_id(),
            trial_used=True
        )
        
        self.licenses[plugin_id] = trial_license
        self.save_licenses()
        
        print(f"✅ Offline trial started for {plugin_id} ({trial_days} days)")
        print("⚠️  Note: Trial will be validated when online")
        return True
    
    def redeem_activation_code(self, activation_code: str, device_id: str = "") -> Dict[str, Any]:
        """Redeem an activation code for a license (with device_id parameter for backward compatibility)"""
        
        if not device_id:
            device_id = self.get_device_id()
        
        # Mock activation codes for testing
        valid_codes = {
            "GOLF2024PROMO": {
                "plugin_id": "golf_pro",
                "license_type": "personal",
                "expiry_days": 365
            },
            "TENNIS2024": {
                "plugin_id": "tennis_pro", 
                "license_type": "personal",
                "expiry_days": 365
            }
        }
        
        if activation_code not in valid_codes:
            return {
                "success": False,
                "error": "Invalid activation code"
            }
        
        code_info = valid_codes[activation_code]
        plugin_id = code_info["plugin_id"]
        
        # Check if plugin exists
        if plugin_id not in self.manifests:
            return {
                "success": False,
                "error": "Plugin not found"
            }
        
        # Generate license key
        license_key = f"LICENSE_{plugin_id}_{int(datetime.now().timestamp())}"
        
        # Create license
        license_data = PluginLicense(
            plugin_id=plugin_id,
            license_key=license_key,
            activation_date=datetime.now().isoformat(),
            expiry_date=(datetime.now() + timedelta(days=code_info["expiry_days"])).isoformat(),
            device_id=device_id,
            trial_used=False,
            activation_count=1,
            max_activations=3
        )
        
        # Store license
        self.licenses[plugin_id] = license_data
        self.save_licenses()
        
        return {
            "success": True,
            "license_key": license_key,
            "plugin_id": plugin_id,
            "expiry_date": license_data.expiry_date,
            "message": f"Successfully activated {self.manifests[plugin_id].name}"
        }
    
    def redeem_activation_code_old(self, activation_code: str) -> Dict[str, Any]:
        """Redeem an activation code for a license"""
        
        if not self._is_online():
            return {
                "success": False,
                "error": "Internet connection required for activation code redemption"
            }
        
        try:
            from .license_server import license_server
            
            success, license_info = license_server.redeem_activation_code(activation_code)
            
            if success:
                plugin_id = license_info['plugin_id']
                license_key = license_info['license_key']
                
                # Activate the license
                activation_success = self._activate_license_online(plugin_id, license_key)
                
                if activation_success:
                    return {
                        "success": True,
                        "plugin_id": plugin_id,
                        "license_key": license_key,
                        "license_type": license_info['license_type'],
                        "features": license_info['features']
                    }
                else:
                    return {
                        "success": False,
                        "error": "License redemption succeeded but activation failed"
                    }
            else:
                return {
                    "success": False,
                    "error": license_info.get('error', 'Invalid activation code')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Redemption failed: {str(e)}"
            }
    
    def get_trial_status(self, plugin_id: str) -> Dict[str, Any]:
        """Get trial status for a plugin"""
        
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            return {"available": False, "reason": "Plugin not found"}
        
        if manifest.trial_days == 0:
            return {"available": False, "reason": "No trial offered"}
        
        license_data = self.licenses.get(plugin_id)
        if license_data and license_data.trial_used:
            # Check if trial is still active
            if license_data.expiry_date:
                expiry = datetime.fromisoformat(license_data.expiry_date)
                if datetime.now() < expiry:
                    remaining_days = (expiry - datetime.now()).days
                    return {
                        "available": False,
                        "reason": "Trial active",
                        "remaining_days": remaining_days,
                        "expiry_date": license_data.expiry_date
                    }
                else:
                    return {"available": False, "reason": "Trial expired"}
            else:
                return {"available": False, "reason": "Trial used"}
        
        return {
            "available": True,
            "trial_days": manifest.trial_days,
            "plugin_name": manifest.name
        }
    
    def activate_license(self, plugin_id: str, license_key: str) -> bool:
        """Activate a paid plugin license"""
        
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            print(f"❌ Plugin {plugin_id} not found")
            return False
        
        # Try online activation first
        if self._is_online():
            return self._activate_license_online(plugin_id, license_key)
        else:
            print("⚠️ No internet connection, using offline activation")
            return self._activate_license_offline(plugin_id, license_key)
    
    def _activate_license_online(self, plugin_id: str, license_key: str) -> bool:
        """Activate license using online server"""
        try:
            from .license_server import simulate_license_activation
            
            device_id = self.get_device_id()
            result = simulate_license_activation(license_key, device_id)
            
            if result['success']:
                # Create local license record
                license_data = PluginLicense(
                    plugin_id=plugin_id,
                    license_key=license_key,
                    activation_date=datetime.now().isoformat(),
                    expiry_date=result['data'].get('expiry_date'),
                    device_id=device_id,
                    activation_count=1
                )
                
                self.licenses[plugin_id] = license_data
                self.save_licenses()
                
                print(f"✅ License activated for {plugin_id}")
                print(f"   Features: {result['data'].get('features', [])}")
                if license_data.expiry_date:
                    print(f"   Expires: {license_data.expiry_date}")
                
                return True
            else:
                print(f"❌ License activation failed: {result['data'].get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"⚠️ Online activation failed: {e}")
            return self._activate_license_offline(plugin_id, license_key)
    
    def _activate_license_offline(self, plugin_id: str, license_key: str) -> bool:
        """Activate license offline (basic validation only)"""
        
        # Basic offline validation - check key format
        if len(license_key) < 10:
            print("❌ Invalid license key format")
            return False
        
        # Create offline license record (no expiry validation)
        license_data = PluginLicense(
            plugin_id=plugin_id,
            license_key=license_key,
            activation_date=datetime.now().isoformat(),
            device_id=self.get_device_id(),
            activation_count=1
        )
        
        self.licenses[plugin_id] = license_data
        self.save_licenses()
        
        print(f"✅ License activated offline for {plugin_id}")
        print("⚠️  Note: License will be validated when online")
        return True
    
    def get_device_id(self) -> str:
        """Get unique device identifier"""
        import platform
        device_info = f"{platform.node()}-{platform.system()}"
        return hashlib.md5(device_info.encode()).hexdigest()[:16]
    
    def load_licenses(self):
        """Load license data from file"""
        license_file = os.path.join(self.plugins_dir, "data", "licenses.json")
        
        if os.path.exists(license_file):
            try:
                with open(license_file, 'r') as f:
                    data = json.load(f)
                
                for plugin_id, license_data in data.items():
                    self.licenses[plugin_id] = PluginLicense(**license_data)
                    
            except Exception as e:
                print(f"Error loading licenses: {e}")
    
    def save_licenses(self):
        """Save license data to file"""
        license_file = os.path.join(self.plugins_dir, "data", "licenses.json")
        os.makedirs(os.path.dirname(license_file), exist_ok=True)
        
        try:
            data = {}
            for plugin_id, license_data in self.licenses.items():
                data[plugin_id] = asdict(license_data)
            
            with open(license_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving licenses: {e}")
    
    def get_active_plugins(self) -> List[str]:
        """Get list of active plugin IDs"""
        return list(self.plugins.keys())
    
    def get_available_plugins(self) -> List[PluginManifest]:
        """Get list of all available plugins"""
        return list(self.manifests.values())
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a plugin"""
        
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            return None
        
        license_data = self.licenses.get(plugin_id)
        is_active = plugin_id in self.plugins
        
        # Determine status
        if is_active:
            status = PluginStatus.ACTIVE
        elif license_data:
            if license_data.expiry_date:
                expiry = datetime.fromisoformat(license_data.expiry_date)
                if datetime.now() > expiry:
                    status = PluginStatus.EXPIRED
                elif license_data.license_key == "TRIAL":
                    status = PluginStatus.TRIAL
                else:
                    status = PluginStatus.INACTIVE
            else:
                status = PluginStatus.INACTIVE
        else:
            status = PluginStatus.INACTIVE
        
        return {
            "manifest": asdict(manifest),
            "license": asdict(license_data) if license_data else None,
            "status": status.value,
            "is_active": is_active
        }
    
    def get_plugin_api_routes(self) -> List[Dict[str, Any]]:
        """Get all API routes from active plugins"""
        routes = []
        for plugin in self.plugins.values():
            routes.extend(plugin.get_api_routes())
        return routes
    
    def get_plugin_ui_components(self) -> List[Dict[str, Any]]:
        """Get all UI components from active plugins"""
        components = []
        for plugin in self.plugins.values():
            components.extend(plugin.get_ui_components())
        return components

# Global plugin manager instance
plugin_manager = PluginManager()

# Utility functions
def load_all_plugins():
    """Discover and load all available plugins"""
    plugin_manager.discover_plugins()
    
    for manifest in plugin_manager.get_available_plugins():
        if plugin_manager.check_license(manifest.id):
            plugin_manager.load_plugin(manifest.id)

def get_sport_plugins() -> List[BasePlugin]:
    """Get all active sport plugins"""
    return [
        plugin for plugin in plugin_manager.plugins.values()
        if isinstance(plugin, SportPlugin)
    ]

if __name__ == "__main__":
    # Test plugin system
    print("🔌 Testing Plugin System...")
    
    # Discover plugins
    discovered = plugin_manager.discover_plugins()
    print(f"✅ Discovered {len(discovered)} plugins")
    
    # Show available plugins
    for manifest in discovered:
        info = plugin_manager.get_plugin_info(manifest.id)
        print(f"   {manifest.name} ({manifest.version}) - {info['status']}")
    
    print("✅ Plugin system test completed!")