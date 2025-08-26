"""
Integration Tests for Plugin System and Licensing

Tests end-to-end plugin workflows including discovery, licensing,
activation, and plugin functionality integration.
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from plugins.core.plugin_manager import PluginManager, PluginManifest, PluginLicense
from plugins.core.mobile_bridge import MobilePluginBridge, MobileDeviceInfo, MobilePlatform
from tests.test_config import TestConfig, TestHelpers

class TestPluginDiscoveryIntegration:
    """Integration tests for plugin discovery"""
    
    @pytest.fixture
    def temp_plugin_dir(self):
        """Create temporary plugin directory structure"""
        temp_dir = tempfile.mkdtemp()
        
        # Create golf plugin structure
        golf_dir = os.path.join(temp_dir, "sports", "golf_pro")
        os.makedirs(golf_dir, exist_ok=True)
        
        # Create manifest
        manifest_data = {
            "id": "golf_pro",
            "name": "Golf Pro Swing Analyzer",
            "version": "1.0.0",
            "description": "Professional golf swing analysis",
            "author": "AI Fitness Coach Team",
            "plugin_type": "sport_analysis",
            "price": 9.99,
            "trial_days": 7,
            "requires_core_version": "1.0.0",
            "dependencies": [],
            "permissions": ["camera", "pose_analysis", "voice_feedback"],
            "entry_point": "golf_plugin.py",
            "icon": "golf_icon.png",
            "screenshots": ["swing_analysis.png"],
            "tags": ["golf", "swing", "analysis"],
            "created_date": "2024-08-26T10:00:00",
            "updated_date": "2024-08-26T10:00:00"
        }
        
        with open(os.path.join(golf_dir, "manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=2)
        
        # Create mock plugin file
        plugin_code = '''
from plugins.core.plugin_system import SportPlugin

class GolfProPlugin(SportPlugin):
    def initialize(self):
        return True
    
    def analyze_pose(self, pose_data):
        return {"swing_phase": "backswing", "score": 85}
    
    def cleanup(self):
        pass
'''
        with open(os.path.join(golf_dir, "golf_plugin.py"), "w") as f:
            f.write(plugin_code)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_full_plugin_discovery(self, temp_plugin_dir):
        """Test complete plugin discovery process"""
        
        manager = PluginManager(plugins_dir=temp_plugin_dir)
        
        # Discover plugins
        discovered = manager.discover_plugins()
        
        assert len(discovered) >= 1
        golf_plugin = next((p for p in discovered if p.id == "golf_pro"), None)
        assert golf_plugin is not None
        assert golf_plugin.name == "Golf Pro Swing Analyzer"
        assert golf_plugin.price == 9.99
        assert "camera" in golf_plugin.permissions
    
    def test_plugin_manifest_validation(self, temp_plugin_dir):
        """Test plugin manifest validation during discovery"""
        
        manager = PluginManager(plugins_dir=temp_plugin_dir)
        
        # Create invalid manifest
        invalid_dir = os.path.join(temp_plugin_dir, "sports", "invalid_plugin")
        os.makedirs(invalid_dir, exist_ok=True)
        
        invalid_manifest = {
            "id": "invalid_plugin",
            "name": "Invalid Plugin",
            # Missing required fields
        }
        
        with open(os.path.join(invalid_dir, "manifest.json"), "w") as f:
            json.dump(invalid_manifest, f)
        
        discovered = manager.discover_plugins()
        
        # Should only discover valid plugins
        plugin_ids = [p.id for p in discovered]
        assert "golf_pro" in plugin_ids
        assert "invalid_plugin" not in plugin_ids

class TestLicensingIntegration:
    """Integration tests for licensing system"""
    
    @pytest.fixture
    def manager_with_plugin(self):
        """Plugin manager with test plugin"""
        manager = PluginManager()
        
        # Add test plugin manifest
        golf_manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99, trial_days=7)
        manager.manifests["golf_pro"] = golf_manifest
        
        return manager
    
    def test_trial_activation_workflow(self, manager_with_plugin):
        """Test complete trial activation workflow"""
        
        manager = manager_with_plugin
        
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device_001"), \
             patch.object(manager, 'save_licenses') as mock_save:
            
            # Check initial license status
            assert not manager.check_license("golf_pro")  # Should fail initially
            
            # Start trial (should happen automatically in check_license for plugins with trials)
            manager.start_trial("golf_pro")
            
            # Verify trial license created
            assert "golf_pro" in manager.licenses
            trial_license = manager.licenses["golf_pro"]
            assert trial_license.trial_used == True
            assert trial_license.device_id == "test_device_001"
            
            # Check license now passes
            assert manager.check_license("golf_pro") == True
            
            # Verify save was called
            mock_save.assert_called()
    
    def test_license_expiry_handling(self, manager_with_plugin):
        """Test handling of expired licenses"""
        
        manager = manager_with_plugin
        
        # Create expired license
        expired_license = PluginLicense(
            plugin_id="golf_pro",
            license_key="EXPIRED_LICENSE",
            activation_date=(datetime.now() - timedelta(days=10)).isoformat(),
            expiry_date=(datetime.now() - timedelta(days=1)).isoformat(),
            device_id="test_device_001",
            trial_used=True
        )
        
        manager.licenses["golf_pro"] = expired_license
        
        with patch.object(manager, '_is_online', return_value=False):
            # License check should fail for expired license
            assert manager.check_license("golf_pro") == False
    
    def test_activation_code_redemption_workflow(self, manager_with_plugin):
        """Test activation code redemption workflow"""
        
        manager = manager_with_plugin
        
        with patch.object(manager, '_is_online', return_value=True), \
             patch('plugins.core.plugin_manager.license_server') as mock_server, \
             patch.object(manager, 'save_licenses'):
            
            # Mock server responses
            mock_server.redeem_activation_code.return_value = (True, {
                "plugin_id": "golf_pro",
                "license_key": "GOLF-PRO-LICENSE-123",
                "license_type": "personal",
                "features": ["swing_analysis", "voice_coaching"]
            })
            
            with patch.object(manager, '_activate_license_online', return_value=True):
                # Redeem activation code
                result = manager.redeem_activation_code("GOLF2024PROMO")
                
                assert result["success"] == True
                assert result["plugin_id"] == "golf_pro"
                assert result["license_key"] == "GOLF-PRO-LICENSE-123"
    
    def test_offline_license_validation(self, manager_with_plugin):
        """Test offline license validation"""
        
        manager = manager_with_plugin
        
        # Create valid license
        valid_license = PluginLicense(
            plugin_id="golf_pro",
            license_key="VALID_LICENSE_123",
            activation_date=datetime.now().isoformat(),
            expiry_date=(datetime.now() + timedelta(days=365)).isoformat(),
            device_id="test_device_001",
            trial_used=False
        )
        
        manager.licenses["golf_pro"] = valid_license
        
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="test_device_001"):
            
            # Should pass offline validation
            assert manager.check_license("golf_pro") == True
        
        # Test with wrong device ID
        with patch.object(manager, '_is_online', return_value=False), \
             patch.object(manager, 'get_device_id', return_value="different_device"):
            
            # Should fail with wrong device
            assert manager.check_license("golf_pro") == False

class TestPluginLoadingIntegration:
    """Integration tests for plugin loading"""
    
    @pytest.fixture
    def manager_with_license(self):
        """Plugin manager with valid license"""
        manager = PluginManager()
        
        # Add plugin manifest
        golf_manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99)
        manager.manifests["golf_pro"] = golf_manifest
        
        # Add valid license
        valid_license = TestHelpers.create_mock_license("golf_pro")
        manager.licenses["golf_pro"] = valid_license
        
        return manager
    
    def test_plugin_loading_with_valid_license(self, manager_with_license):
        """Test plugin loading with valid license"""
        
        manager = manager_with_license
        
        with patch.object(manager, 'check_license', return_value=True), \
             patch.object(manager, 'get_plugin_directory', return_value="/mock/plugin/dir"), \
             patch('os.path.exists', return_value=True), \
             patch('importlib.util.spec_from_file_location') as mock_spec, \
             patch('importlib.util.module_from_spec') as mock_module:
            
            # Mock module loading
            mock_plugin_class = Mock()
            mock_plugin_instance = Mock()
            mock_plugin_instance.initialize.return_value = True
            mock_plugin_class.return_value = mock_plugin_instance
            
            mock_module_obj = Mock()
            setattr(mock_module_obj, 'GolfProPlugin', mock_plugin_class)
            mock_module.return_value = mock_module_obj
            
            # Mock spec and loader
            mock_spec_obj = Mock()
            mock_loader = Mock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj
            
            # Load plugin
            result = manager.load_plugin("golf_pro")
            
            assert result == True
            assert "golf_pro" in manager.plugins
    
    def test_plugin_loading_without_license(self, manager_with_license):
        """Test plugin loading fails without valid license"""
        
        manager = manager_with_license
        
        with patch.object(manager, 'check_license', return_value=False):
            
            result = manager.load_plugin("golf_pro")
            
            assert result == False
            assert "golf_pro" not in manager.plugins

class TestMobileIntegration:
    """Integration tests for mobile plugin integration"""
    
    @pytest.fixture
    def mobile_bridge(self):
        """Mobile bridge with test setup"""
        return MobilePluginBridge()
    
    @pytest.fixture
    def test_device(self):
        """Test mobile device"""
        return MobileDeviceInfo(
            device_id="test_iphone_001",
            platform=MobilePlatform.IOS,
            os_version="16.0",
            app_version="1.0.0",
            device_model="iPhone 14 Pro",
            screen_resolution="1179x2556",
            camera_specs={"resolution": "12MP", "fps": 60},
            sensors_available=["camera", "microphone", "accelerometer", "gyroscope"]
        )
    
    def test_mobile_device_registration_workflow(self, mobile_bridge, test_device):
        """Test mobile device registration workflow"""
        
        result = mobile_bridge.register_device(test_device)
        
        assert result["device_id"] == "test_iphone_001"
        assert "registration_time" in result
        assert "compatible_plugins" in result
        assert "supported_capabilities" in result
        
        # Device should be registered
        assert "test_iphone_001" in mobile_bridge.registered_devices
    
    def test_mobile_session_lifecycle(self, mobile_bridge, test_device):
        """Test complete mobile session lifecycle"""
        
        # Register device
        mobile_bridge.register_device(test_device)
        
        # Start session
        session_result = mobile_bridge.start_session(
            "test_iphone_001", "golf_pro", "golf_swing_analysis"
        )
        
        assert "session_id" in session_result
        assert session_result["status"] == "started"
        session_id = session_result["session_id"]
        
        # Verify session is active
        assert session_id in mobile_bridge.active_sessions
        
        # Process data
        test_data = {
            "pose_data": {
                "keypoints": [{"x": 100, "y": 200, "confidence": 0.9}],
                "timestamp": datetime.now().isoformat()
            }
        }
        
        process_result = mobile_bridge.process_mobile_data(session_id, test_data)
        
        assert process_result["status"] == "success"
        assert "analysis" in process_result
        
        # End session
        end_result = mobile_bridge.end_session(session_id)
        
        assert end_result["status"] == "ended"
        assert "duration_seconds" in end_result
        
        # Session should be removed
        assert session_id not in mobile_bridge.active_sessions
    
    def test_mobile_compatibility_checking(self, mobile_bridge):
        """Test mobile device compatibility checking"""
        
        # Test compatible device
        compatible_device = MobileDeviceInfo(
            device_id="compatible_device",
            platform=MobilePlatform.IOS,
            os_version="16.0",
            app_version="1.0.0",
            device_model="iPhone 14",
            screen_resolution="1179x2556",
            camera_specs={"resolution": "12MP"},
            sensors_available=["camera", "microphone", "accelerometer"]
        )
        
        result = mobile_bridge.register_device(compatible_device)
        compatible_plugins = result["compatible_plugins"]
        
        assert len(compatible_plugins) > 0
        golf_plugin = next((p for p in compatible_plugins if p["plugin_id"] == "golf_pro"), None)
        assert golf_plugin is not None
        
        # Test incompatible device (old OS)
        incompatible_device = MobileDeviceInfo(
            device_id="incompatible_device",
            platform=MobilePlatform.IOS,
            os_version="12.0",  # Too old
            app_version="1.0.0",
            device_model="iPhone 8",
            screen_resolution="750x1334",
            camera_specs={"resolution": "8MP"},
            sensors_available=["camera"]
        )
        
        result = mobile_bridge.register_device(incompatible_device)
        compatible_plugins = result["compatible_plugins"]
        
        # Should have fewer or no compatible plugins
        golf_plugin = next((p for p in compatible_plugins if p["plugin_id"] == "golf_pro"), None)
        # Golf plugin might not be compatible with old iOS

class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_complete_plugin_workflow(self):
        """Test complete workflow from discovery to usage"""
        
        # Setup
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = PluginManager(plugins_dir=temp_dir)
            mobile_bridge = MobilePluginBridge()
            
            # Add test plugin
            golf_manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99, trial_days=7)
            manager.manifests["golf_pro"] = golf_manifest
            
            # Step 1: Check plugin availability
            available_plugins = manager.get_available_plugins()
            assert len(available_plugins) >= 1
            
            # Step 2: Start trial
            with patch.object(manager, '_is_online', return_value=False), \
                 patch.object(manager, 'get_device_id', return_value="test_device"), \
                 patch.object(manager, 'save_licenses'):
                
                trial_result = manager.start_trial("golf_pro")
                assert trial_result == True
            
            # Step 3: Verify license
            license_valid = manager.check_license("golf_pro")
            assert license_valid == True
            
            # Step 4: Register mobile device
            test_device = MobileDeviceInfo(
                device_id="test_device_mobile",
                platform=MobilePlatform.IOS,
                os_version="16.0",
                app_version="1.0.0",
                device_model="iPhone 14",
                screen_resolution="1179x2556",
                camera_specs={"resolution": "12MP"},
                sensors_available=["camera", "microphone"]
            )
            
            mobile_result = mobile_bridge.register_device(test_device)
            assert mobile_result["device_id"] == "test_device_mobile"
            
            # Step 5: Start mobile session
            session_result = mobile_bridge.start_session(
                "test_device_mobile", "golf_pro", "golf_swing_analysis"
            )
            assert session_result["status"] == "started"
            
            # Step 6: Process data and get results
            test_data = {"pose_data": {"keypoints": []}}
            analysis_result = mobile_bridge.process_mobile_data(
                session_result["session_id"], test_data
            )
            assert analysis_result["status"] == "success"
            
            print("✅ Complete workflow test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])