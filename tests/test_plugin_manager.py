"""
Unit Tests for Plugin Management System

Tests plugin discovery, loading, licensing, and integration functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
import json
import tempfile
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from plugins.core.plugin_manager import (
    PluginManager, BasePlugin, SportPlugin, PluginManifest, PluginLicense,
    PluginType, PluginStatus, plugin_manager, load_all_plugins
)
from tests.test_config import TestConfig, TestHelpers

class TestPluginManifest:
    """Test PluginManifest data class"""
    
    def test_manifest_creation(self):
        """Test creating a plugin manifest"""
        manifest = PluginManifest(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
            description="Test plugin for unit testing",
            author="Test Team",
            plugin_type=PluginType.SPORT_ANALYSIS,
            price=9.99,
            trial_days=7,
            requires_core_version="1.0.0",
            dependencies=[],
            permissions=["camera"],
            entry_point="test_plugin.py",
            icon="test_icon.png",
            screenshots=["screenshot1.png"],
            tags=["test", "sport"],
            created_date="2024-08-26T10:00:00",
            updated_date="2024-08-26T10:00:00"
        )
        
        assert manifest.id == "test_plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.plugin_type == PluginType.SPORT_ANALYSIS
        assert manifest.price == 9.99
        assert manifest.trial_days == 7
        assert len(manifest.permissions) == 1
        assert "camera" in manifest.permissions

class TestPluginLicense:
    """Test PluginLicense functionality"""
    
    def test_license_creation(self):
        """Test creating a plugin license"""
        license_data = PluginLicense(
            plugin_id="test_plugin",
            license_key="TEST_LICENSE_123",
            activation_date=datetime.now().isoformat(),
            expiry_date=(datetime.now() + timedelta(days=30)).isoformat(),
            device_id="test_device_001",
            trial_used=False,
            activation_count=1,
            max_activations=3
        )
        
        assert license_data.plugin_id == "test_plugin"
        assert license_data.license_key == "TEST_LICENSE_123"
        assert license_data.activation_count == 1
        assert license_data.max_activations == 3
    
    def test_trial_license(self):
        """Test trial license creation"""
        trial_license = TestHelpers.create_mock_license("test_plugin", is_trial=True)
        
        assert trial_license.trial_used == True
        assert trial_license.license_key == "TRIAL"
        assert trial_license.expiry_date is not None

class TestBasePlugin:
    """Test BasePlugin abstract class"""
    
    def test_base_plugin_interface(self):
        """Test BasePlugin provides correct interface"""
        manifest = TestHelpers.create_mock_plugin()
        
        # Cannot instantiate abstract class directly
        with pytest.raises(TypeError):
            BasePlugin(manifest)

class TestPluginManager:
    """Test PluginManager core functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create plugin manager with temporary directory"""
        temp_dir = tempfile.mkdtemp()
        with patch('plugins.core.plugin_manager.os.makedirs'):
            return PluginManager(plugins_dir=temp_dir)
    
    def test_manager_initialization(self, manager):
        """Test plugin manager initializes correctly"""
        assert manager is not None
        assert hasattr(manager, 'plugins_dir')
        assert hasattr(manager, 'plugins')
        assert hasattr(manager, 'manifests')
        assert hasattr(manager, 'licenses')
    
    @patch('plugins.core.plugin_manager.os.walk')
    @patch('builtins.open', mock_open())
    @patch('json.load')
    def test_discover_plugins(self, mock_json_load, mock_walk, manager):
        """Test plugin discovery functionality"""
        
        # Mock file system structure
        mock_walk.return_value = [
            ("/plugins/test_plugin", [], ["manifest.json", "plugin.py"]),
            ("/plugins/another_plugin", [], ["manifest.json", "plugin.py"])
        ]
        
        # Mock manifest data
        mock_manifest_data = {
            "id": "test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test Team",
            "plugin_type": "sport_analysis",
            "price": 0.0,
            "trial_days": 0,
            "requires_core_version": "1.0.0",
            "dependencies": [],
            "permissions": [],
            "entry_point": "plugin.py",
            "icon": "icon.png",
            "screenshots": [],
            "tags": [],
            "created_date": "2024-08-26T10:00:00",
            "updated_date": "2024-08-26T10:00:00"
        }
        
        mock_json_load.return_value = mock_manifest_data
        
        discovered = manager.discover_plugins()
        
        assert len(discovered) == 2
        assert all(isinstance(plugin, PluginManifest) for plugin in discovered)
    
    def test_load_manifest(self, manager):
        """Test loading plugin manifest from file"""
        
        manifest_data = {
            "id": "test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test Team",
            "plugin_type": "sport_analysis",
            "price": 0.0,
            "trial_days": 0,
            "requires_core_version": "1.0.0",
            "dependencies": [],
            "permissions": [],
            "entry_point": "plugin.py",
            "icon": "icon.png",
            "screenshots": [],
            "tags": [],
            "created_date": "2024-08-26T10:00:00",
            "updated_date": "2024-08-26T10:00:00"
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(manifest_data))), \
             patch('json.load', return_value=manifest_data):
            
            manifest = manager.load_manifest("test_manifest.json")
            
            assert manifest is not None
            assert manifest.id == "test_plugin"
            assert manifest.plugin_type == PluginType.SPORT_ANALYSIS
    
    def test_check_license_free_plugin(self, manager):
        """Test license check for free plugins"""
        
        # Create free plugin manifest
        free_manifest = TestHelpers.create_mock_plugin("free_plugin", price=0.0)
        manager.manifests["free_plugin"] = free_manifest
        
        # Free plugins should always pass license check
        assert manager.check_license("free_plugin") == True
    
    def test_check_license_paid_plugin_no_license(self, manager):
        """Test license check for paid plugin without license"""
        
        # Create paid plugin manifest with trial
        paid_manifest = TestHelpers.create_mock_plugin("paid_plugin", price=9.99, trial_days=7)
        manager.manifests["paid_plugin"] = paid_manifest
        
        with patch.object(manager, 'start_trial', return_value=True):
            # Should attempt to start trial
            result = manager.check_license("paid_plugin")
            assert result == True
    
    def test_check_license_valid_license(self, manager):
        """Test license check with valid license"""
        
        # Create paid plugin manifest
        paid_manifest = TestHelpers.create_mock_plugin("paid_plugin", price=9.99)
        manager.manifests["paid_plugin"] = paid_manifest
        
        # Create valid license
        valid_license = TestHelpers.create_mock_license("paid_plugin")
        manager.licenses["paid_plugin"] = valid_license
        
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device_001"):
            
            result = manager.check_license("paid_plugin")
            assert result == True
    
    def test_check_license_expired_license(self, manager):
        """Test license check with expired license"""
        
        # Create paid plugin manifest
        paid_manifest = TestHelpers.create_mock_plugin("paid_plugin", price=9.99)
        manager.manifests["paid_plugin"] = paid_manifest
        
        # Create expired license
        expired_license = TestHelpers.create_mock_license("paid_plugin", is_expired=True)
        manager.licenses["paid_plugin"] = expired_license
        
        with patch.object(manager, '_is_online', return_value=False):
            result = manager.check_license("paid_plugin")
            assert result == False
    
    def test_start_trial(self, manager):
        """Test starting plugin trial"""
        
        # Create plugin with trial
        trial_manifest = TestHelpers.create_mock_plugin("trial_plugin", price=9.99, trial_days=7)
        manager.manifests["trial_plugin"] = trial_manifest
        
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device_001"), \
             patch.object(manager, 'save_licenses'):
            
            result = manager.start_trial("trial_plugin")
            
            assert result == True
            assert "trial_plugin" in manager.licenses
            assert manager.licenses["trial_plugin"].trial_used == True
    
    def test_activate_license_offline(self, manager):
        """Test license activation in offline mode"""
        
        # Create paid plugin
        paid_manifest = TestHelpers.create_mock_plugin("paid_plugin", price=9.99)
        manager.manifests["paid_plugin"] = paid_manifest
        
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device_001"), \
             patch.object(manager, 'save_licenses'):
            
            result = manager.activate_license("paid_plugin", "VALID_LICENSE_KEY_123")
            
            assert result == True
            assert "paid_plugin" in manager.licenses
            assert manager.licenses["paid_plugin"].license_key == "VALID_LICENSE_KEY_123"
    
    def test_get_plugin_info(self, manager):
        """Test getting plugin information"""
        
        # Create plugin and license
        manifest = TestHelpers.create_mock_plugin("info_plugin", price=9.99)
        license_data = TestHelpers.create_mock_license("info_plugin")
        
        manager.manifests["info_plugin"] = manifest
        manager.licenses["info_plugin"] = license_data
        
        info = manager.get_plugin_info("info_plugin")
        
        assert info is not None
        assert "manifest" in info
        assert "license" in info
        assert "status" in info
        assert "is_active" in info
        assert info["manifest"]["id"] == "info_plugin"
    
    def test_get_available_plugins(self, manager):
        """Test getting all available plugins"""
        
        # Add test plugins
        plugin1 = TestHelpers.create_mock_plugin("plugin1")
        plugin2 = TestHelpers.create_mock_plugin("plugin2")
        
        manager.manifests["plugin1"] = plugin1
        manager.manifests["plugin2"] = plugin2
        
        available = manager.get_available_plugins()
        
        assert len(available) == 2
        assert all(isinstance(plugin, PluginManifest) for plugin in available)
    
    def test_device_id_generation(self, manager):
        """Test device ID generation"""
        
        with patch('platform.node', return_value="test_computer"), \
             patch('platform.system', return_value="Windows"):
            
            device_id = manager.get_device_id()
            
            assert device_id is not None
            assert len(device_id) == 16  # MD5 hash truncated to 16 chars
    
    def test_license_persistence(self, manager):
        """Test license saving and loading"""
        
        # Create license
        license_data = TestHelpers.create_mock_license("test_plugin")
        manager.licenses["test_plugin"] = license_data
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump, \
             patch('os.makedirs'):
            
            manager.save_licenses()
            
            mock_file.assert_called()
            mock_json_dump.assert_called()
    
    def test_redeem_activation_code(self, manager):
        """Test activation code redemption"""
        
        # Create plugin manifest
        manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99)
        manager.manifests["golf_pro"] = manifest
        
        with patch.object(manager, '_is_online', return_value=True), \
             patch('plugins.core.plugin_manager.license_server') as mock_server:
            
            # Mock server response
            mock_server.redeem_activation_code.return_value = (True, {
                "plugin_id": "golf_pro",
                "license_key": "GOLF-PRO-LICENSE-123",
                "license_type": "personal",
                "features": ["swing_analysis"]
            })
            
            with patch.object(manager, '_activate_license_online', return_value=True):
                result = manager.redeem_activation_code("GOLF2024")
                
                assert result["success"] == True
                assert result["plugin_id"] == "golf_pro"

class TestPluginIntegration:
    """Integration tests for plugin system"""
    
    def test_plugin_lifecycle(self):
        """Test complete plugin lifecycle"""
        
        with patch('plugins.core.plugin_manager.os.makedirs'):
            manager = PluginManager()
        
        # Create test plugin
        manifest = TestHelpers.create_mock_plugin("lifecycle_plugin", price=9.99, trial_days=7)
        manager.manifests["lifecycle_plugin"] = manifest
        
        # Test discovery
        assert "lifecycle_plugin" in manager.manifests
        
        # Test trial start
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device"), \
             patch.object(manager, 'save_licenses'):
            
            trial_result = manager.start_trial("lifecycle_plugin")
            assert trial_result == True
        
        # Test license check
        license_result = manager.check_license("lifecycle_plugin")
        assert license_result == True
        
        # Test plugin info
        info = manager.get_plugin_info("lifecycle_plugin")
        assert info["status"] == "inactive"  # Not loaded yet

if __name__ == "__main__":
    pytest.main([__file__, "-v"])