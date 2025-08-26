"""
API Integration Tests for Plugin System

Tests FastAPI endpoints for plugin management, licensing,
and mobile integration through HTTP API calls.
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from plugins.core.plugin_manager import PluginManager, PluginManifest, PluginLicense
from plugins.core.mobile_bridge import MobilePluginBridge, MobileDeviceInfo, MobilePlatform
from plugins.core.license_server import LicenseServerSimulator
from tests.test_config import TestConfig, TestHelpers

# Mock FastAPI app for testing
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Create test FastAPI app
app = FastAPI(title="AI Fitness Coach Plugin API")

# Test data models
class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    price: float
    trial_days: int
    is_licensed: bool
    is_active: bool

class LicenseRequest(BaseModel):
    plugin_id: str
    license_key: str

class ActivationCodeRequest(BaseModel):
    activation_code: str

class TrialRequest(BaseModel):
    plugin_id: str

class MobileRegistration(BaseModel):
    device_id: str
    platform: str
    os_version: str
    app_version: str
    device_model: str
    camera_specs: Dict[str, Any]
    sensors_available: List[str]

class SessionRequest(BaseModel):
    device_id: str
    plugin_id: str
    capability_id: str

# Global instances for testing
plugin_manager = PluginManager()
mobile_bridge = MobilePluginBridge()
license_server = LicenseServerSimulator()

# API Routes
@app.get("/api/v1/plugins", response_model=List[PluginInfo])
async def list_plugins():
    """List all available plugins"""
    available_plugins = plugin_manager.get_available_plugins()
    
    plugin_list = []
    for manifest in available_plugins:
        plugin_info = plugin_manager.get_plugin_info(manifest.id)
        
        plugin_list.append(PluginInfo(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            price=manifest.price,
            trial_days=manifest.trial_days,
            is_licensed=plugin_info.get("license") is not None,
            is_active=plugin_info.get("is_active", False)
        ))
    
    return plugin_list

@app.get("/api/v1/plugins/{plugin_id}")
async def get_plugin_details(plugin_id: str):
    """Get detailed plugin information"""
    plugin_info = plugin_manager.get_plugin_info(plugin_id)
    
    if not plugin_info:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return plugin_info

@app.post("/api/v1/plugins/{plugin_id}/trial")
async def start_plugin_trial(plugin_id: str):
    """Start trial for a plugin"""
    success = plugin_manager.start_trial(plugin_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Trial could not be started")
    
    return {
        "success": True,
        "plugin_id": plugin_id,
        "message": "Trial started successfully"
    }

@app.post("/api/v1/plugins/activate")
async def activate_license(request: LicenseRequest):
    """Activate a plugin license"""
    success = plugin_manager.activate_license(request.plugin_id, request.license_key)
    
    if not success:
        raise HTTPException(status_code=400, detail="License activation failed")
    
    return {
        "success": True,
        "plugin_id": request.plugin_id,
        "message": "License activated successfully"
    }

@app.post("/api/v1/plugins/redeem")
async def redeem_activation_code(request: ActivationCodeRequest):
    """Redeem an activation code"""
    result = plugin_manager.redeem_activation_code(request.activation_code)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/api/v1/mobile/register")
async def register_mobile_device(registration: MobileRegistration):
    """Register a mobile device"""
    device_info = MobileDeviceInfo(
        device_id=registration.device_id,
        platform=MobilePlatform(registration.platform),
        os_version=registration.os_version,
        app_version=registration.app_version,
        device_model=registration.device_model,
        screen_resolution="1179x2556",  # Default
        camera_specs=registration.camera_specs,
        sensors_available=registration.sensors_available
    )
    
    result = mobile_bridge.register_device(device_info)
    return result

@app.post("/api/v1/mobile/session/start")
async def start_mobile_session(request: SessionRequest):
    """Start a mobile plugin session"""
    result = mobile_bridge.start_session(
        request.device_id,
        request.plugin_id,
        request.capability_id
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/api/v1/mobile/session/{session_id}/data")
async def process_mobile_data(session_id: str, data: Dict[str, Any]):
    """Process data from mobile device"""
    result = mobile_bridge.process_mobile_data(session_id, data)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/api/v1/mobile/session/{session_id}/end")
async def end_mobile_session(session_id: str):
    """End a mobile plugin session"""
    result = mobile_bridge.end_session(session_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.get("/api/v1/mobile/sdk/{platform}")
async def get_mobile_sdk_config(platform: str):
    """Get mobile SDK configuration"""
    try:
        platform_enum = MobilePlatform(platform)
        config = mobile_bridge.get_mobile_sdk_config(platform_enum)
        return config
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")

# Test Classes
class TestPluginAPIEndpoints:
    """Test plugin management API endpoints"""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data for each test"""
        # Add test plugin
        golf_manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99, trial_days=7)
        plugin_manager.manifests["golf_pro"] = golf_manifest
        
        yield
        
        # Cleanup
        plugin_manager.manifests.clear()
        plugin_manager.licenses.clear()
        plugin_manager.plugins.clear()
    
    def test_list_plugins_endpoint(self, client):
        """Test listing available plugins"""
        response = client.get("/api/v1/plugins")
        
        assert response.status_code == 200
        plugins = response.json()
        assert len(plugins) >= 1
        
        golf_plugin = next((p for p in plugins if p["id"] == "golf_pro"), None)
        assert golf_plugin is not None
        assert golf_plugin["name"] == "Test Plugin"
        assert golf_plugin["price"] == 9.99
        assert golf_plugin["trial_days"] == 7
    
    def test_get_plugin_details_endpoint(self, client):
        """Test getting plugin details"""
        response = client.get("/api/v1/plugins/golf_pro")
        
        assert response.status_code == 200
        plugin_info = response.json()
        assert plugin_info["manifest"]["id"] == "golf_pro"
        assert "license" in plugin_info
        assert "status" in plugin_info
    
    def test_get_nonexistent_plugin(self, client):
        """Test getting details for non-existent plugin"""
        response = client.get("/api/v1/plugins/nonexistent_plugin")
        
        assert response.status_code == 404
        assert "Plugin not found" in response.json()["detail"]
    
    def test_start_trial_endpoint(self, client):
        """Test starting plugin trial"""
        with patch.object(plugin_manager, 'start_trial', return_value=True):
            response = client.post("/api/v1/plugins/golf_pro/trial")
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] == True
            assert result["plugin_id"] == "golf_pro"
    
    def test_start_trial_failure(self, client):
        """Test trial start failure"""
        with patch.object(plugin_manager, 'start_trial', return_value=False):
            response = client.post("/api/v1/plugins/golf_pro/trial")
            
            assert response.status_code == 400
            assert "Trial could not be started" in response.json()["detail"]
    
    def test_activate_license_endpoint(self, client):
        """Test license activation"""
        with patch.object(plugin_manager, 'activate_license', return_value=True):
            response = client.post("/api/v1/plugins/activate", json={
                "plugin_id": "golf_pro",
                "license_key": "VALID_LICENSE_123"
            })
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] == True
            assert result["plugin_id"] == "golf_pro"
    
    def test_redeem_activation_code_endpoint(self, client):
        """Test activation code redemption"""
        mock_result = {
            "success": True,
            "plugin_id": "golf_pro",
            "license_key": "GOLF-PRO-LICENSE-123",
            "license_type": "personal"
        }
        
        with patch.object(plugin_manager, 'redeem_activation_code', return_value=mock_result):
            response = client.post("/api/v1/plugins/redeem", json={
                "activation_code": "GOLF2024PROMO"
            })
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] == True
            assert result["plugin_id"] == "golf_pro"

class TestMobileAPIEndpoints:
    """Test mobile integration API endpoints"""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Cleanup after each test"""
        yield
        mobile_bridge.registered_devices.clear()
        mobile_bridge.active_sessions.clear()
    
    def test_register_mobile_device_endpoint(self, client):
        """Test mobile device registration"""
        registration_data = {
            "device_id": "test_iphone_001",
            "platform": "ios",
            "os_version": "16.0",
            "app_version": "1.0.0",
            "device_model": "iPhone 14 Pro",
            "camera_specs": {"resolution": "12MP", "fps": 60},
            "sensors_available": ["camera", "microphone", "accelerometer"]
        }
        
        response = client.post("/api/v1/mobile/register", json=registration_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["device_id"] == "test_iphone_001"
        assert "registration_time" in result
        assert "compatible_plugins" in result
    
    def test_start_mobile_session_endpoint(self, client):
        """Test starting mobile session"""
        # First register device
        registration_data = {
            "device_id": "test_device_001",
            "platform": "ios",
            "os_version": "16.0",
            "app_version": "1.0.0",
            "device_model": "iPhone 14",
            "camera_specs": {"resolution": "12MP"},
            "sensors_available": ["camera", "microphone"]
        }
        
        client.post("/api/v1/mobile/register", json=registration_data)
        
        # Start session
        session_data = {
            "device_id": "test_device_001",
            "plugin_id": "golf_pro",
            "capability_id": "golf_swing_analysis"
        }
        
        response = client.post("/api/v1/mobile/session/start", json=session_data)
        
        assert response.status_code == 200
        result = response.json()
        assert "session_id" in result
        assert result["status"] == "started"
    
    def test_process_mobile_data_endpoint(self, client):
        """Test processing mobile data"""
        # Setup device and session
        registration_data = {
            "device_id": "test_device_002",
            "platform": "ios",
            "os_version": "16.0",
            "app_version": "1.0.0",
            "device_model": "iPhone 14",
            "camera_specs": {"resolution": "12MP"},
            "sensors_available": ["camera", "microphone"]
        }
        
        client.post("/api/v1/mobile/register", json=registration_data)
        
        session_response = client.post("/api/v1/mobile/session/start", json={
            "device_id": "test_device_002",
            "plugin_id": "golf_pro",
            "capability_id": "golf_swing_analysis"
        })
        
        session_id = session_response.json()["session_id"]
        
        # Process data
        test_data = {
            "pose_data": {
                "keypoints": [{"x": 100, "y": 200, "confidence": 0.9}],
                "timestamp": datetime.now().isoformat()
            }
        }
        
        response = client.post(f"/api/v1/mobile/session/{session_id}/data", json=test_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "analysis" in result
    
    def test_end_mobile_session_endpoint(self, client):
        """Test ending mobile session"""
        # Setup device and session
        registration_data = {
            "device_id": "test_device_003",
            "platform": "ios",
            "os_version": "16.0",
            "app_version": "1.0.0",
            "device_model": "iPhone 14",
            "camera_specs": {"resolution": "12MP"},
            "sensors_available": ["camera", "microphone"]
        }
        
        client.post("/api/v1/mobile/register", json=registration_data)
        
        session_response = client.post("/api/v1/mobile/session/start", json={
            "device_id": "test_device_003",
            "plugin_id": "golf_pro",
            "capability_id": "golf_swing_analysis"
        })
        
        session_id = session_response.json()["session_id"]
        
        # End session
        response = client.post(f"/api/v1/mobile/session/{session_id}/end")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ended"
        assert "duration_seconds" in result
    
    def test_get_mobile_sdk_config_endpoint(self, client):
        """Test getting mobile SDK configuration"""
        response = client.get("/api/v1/mobile/sdk/ios")
        
        assert response.status_code == 200
        config = response.json()
        assert "api_base_url" in config
        assert "min_ios_version" in config
        assert "required_frameworks" in config
    
    def test_invalid_platform_sdk_config(self, client):
        """Test SDK config with invalid platform"""
        response = client.get("/api/v1/mobile/sdk/invalid_platform")
        
        assert response.status_code == 400
        assert "Invalid platform" in response.json()["detail"]

class TestLicensingIntegrationAPI:
    """Test licensing integration through API"""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data"""
        # Add test plugin
        golf_manifest = TestHelpers.create_mock_plugin("golf_pro", price=9.99, trial_days=7)
        plugin_manager.manifests["golf_pro"] = golf_manifest
        
        yield
        
        # Cleanup
        plugin_manager.manifests.clear()
        plugin_manager.licenses.clear()
    
    def test_complete_licensing_workflow_api(self, client):
        """Test complete licensing workflow through API"""
        
        # Step 1: List plugins
        response = client.get("/api/v1/plugins")
        assert response.status_code == 200
        plugins = response.json()
        golf_plugin = next((p for p in plugins if p["id"] == "golf_pro"), None)
        assert golf_plugin is not None
        
        # Step 2: Get plugin details
        response = client.get("/api/v1/plugins/golf_pro")
        assert response.status_code == 200
        plugin_details = response.json()
        assert not plugin_details["license"]  # No license initially
        
        # Step 3: Start trial
        with patch.object(plugin_manager, 'start_trial', return_value=True):
            response = client.post("/api/v1/plugins/golf_pro/trial")
            assert response.status_code == 200
            result = response.json()
            assert result["success"] == True
        
        # Step 4: Redeem activation code
        mock_redeem_result = {
            "success": True,
            "plugin_id": "golf_pro",
            "license_key": "GOLF-PRO-LICENSE-123",
            "license_type": "personal"
        }
        
        with patch.object(plugin_manager, 'redeem_activation_code', return_value=mock_redeem_result):
            response = client.post("/api/v1/plugins/redeem", json={
                "activation_code": "GOLF2024PROMO"
            })
            assert response.status_code == 200
            result = response.json()
            assert result["plugin_id"] == "golf_pro"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])