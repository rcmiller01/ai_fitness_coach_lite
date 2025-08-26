"""
Mobile Plugin Integration Framework

Provides integration layer for mobile apps (iOS/Android) to interact
with the plugin system and access sports analysis features.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

class MobilePlatform(Enum):
    """Mobile platforms"""
    IOS = "ios"
    ANDROID = "android"

class DataFormat(Enum):
    """Data exchange formats"""
    JSON = "json"
    PROTOBUF = "protobuf"

@dataclass
class MobilePluginCapability:
    """Mobile plugin capability definition"""
    capability_id: str
    name: str
    description: str
    required_permissions: List[str]
    supported_platforms: List[MobilePlatform]
    min_os_version: Dict[str, str]
    data_format: DataFormat
    real_time: bool
    offline_capable: bool

@dataclass
class MobileDeviceInfo:
    """Mobile device information"""
    device_id: str
    platform: MobilePlatform
    os_version: str
    app_version: str
    device_model: str
    screen_resolution: str
    camera_specs: Dict[str, Any]
    sensors_available: List[str]

class MobilePluginBridge:
    """Bridge between mobile apps and plugin system"""
    
    def __init__(self):
        self.registered_devices: Dict[str, MobileDeviceInfo] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.plugin_capabilities: Dict[str, List[MobilePluginCapability]] = {}
        self.initialize_capabilities()
    
    def initialize_capabilities(self):
        """Initialize mobile plugin capabilities"""
        
        # Golf Pro capabilities
        golf_capabilities = [
            MobilePluginCapability(
                capability_id="golf_swing_analysis",
                name="Golf Swing Analysis",
                description="Real-time golf swing analysis using device camera",
                required_permissions=["camera", "microphone", "storage"],
                supported_platforms=[MobilePlatform.IOS, MobilePlatform.ANDROID],
                min_os_version={"ios": "14.0", "android": "8.0"},
                data_format=DataFormat.JSON,
                real_time=True,
                offline_capable=True
            )
        ]
        
        self.plugin_capabilities["golf_pro"] = golf_capabilities
    
    def register_device(self, device_info: MobileDeviceInfo) -> Dict[str, Any]:
        """Register a mobile device with the plugin system"""
        
        device_id = device_info.device_id
        self.registered_devices[device_id] = device_info
        
        compatible_plugins = self._check_plugin_compatibility(device_info)
        
        return {
            "device_id": device_id,
            "registration_time": datetime.now().isoformat(),
            "compatible_plugins": compatible_plugins,
            "supported_capabilities": self._get_supported_capabilities(device_info)
        }
    
    def _check_plugin_compatibility(self, device_info: MobileDeviceInfo) -> List[Dict[str, Any]]:
        """Check which plugins are compatible with the device"""
        
        compatible = []
        
        for plugin_id, capabilities in self.plugin_capabilities.items():
            supported_caps = []
            
            for capability in capabilities:
                if device_info.platform in capability.supported_platforms:
                    min_version = capability.min_os_version.get(device_info.platform.value)
                    if min_version and self._version_compare(device_info.os_version, min_version) >= 0:
                        supported_caps.append(capability.capability_id)
            
            if supported_caps:
                compatible.append({
                    "plugin_id": plugin_id,
                    "supported_capabilities": supported_caps
                })
        
        return compatible
    
    def _get_supported_capabilities(self, device_info: MobileDeviceInfo) -> List[Dict[str, Any]]:
        """Get all supported capabilities for a device"""
        
        supported = []
        
        for plugin_id, capabilities in self.plugin_capabilities.items():
            for capability in capabilities:
                if (device_info.platform in capability.supported_platforms and
                    self._check_capability_requirements(device_info, capability)):
                    supported.append({
                        "plugin_id": plugin_id,
                        "capability": asdict(capability)
                    })
        
        return supported
    
    def _check_capability_requirements(self, device_info: MobileDeviceInfo, 
                                     capability: MobilePluginCapability) -> bool:
        """Check if device meets capability requirements"""
        
        min_version = capability.min_os_version.get(device_info.platform.value)
        if min_version and self._version_compare(device_info.os_version, min_version) < 0:
            return False
        
        if "camera" in capability.required_permissions:
            if "camera" not in device_info.sensors_available:
                return False
        
        return True
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare version strings"""
        
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    def start_session(self, device_id: str, plugin_id: str, 
                     capability_id: str) -> Dict[str, Any]:
        """Start a plugin session on a mobile device"""
        
        if device_id not in self.registered_devices:
            return {"error": "Device not registered"}
        
        if plugin_id not in self.plugin_capabilities:
            return {"error": "Plugin not found"}
        
        capability = None
        for cap in self.plugin_capabilities[plugin_id]:
            if cap.capability_id == capability_id:
                capability = cap
                break
        
        if not capability:
            return {"error": "Capability not found"}
        
        device_info = self.registered_devices[device_id]
        if not self._check_capability_requirements(device_info, capability):
            return {"error": "Device not compatible with capability"}
        
        session_id = f"{device_id}_{plugin_id}_{capability_id}_{int(datetime.now().timestamp())}"
        
        session_data = {
            "session_id": session_id,
            "device_id": device_id,
            "plugin_id": plugin_id,
            "capability_id": capability_id,
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "data_format": capability.data_format.value,
            "real_time": capability.real_time
        }
        
        self.active_sessions[session_id] = session_data
        
        return {
            "session_id": session_id,
            "status": "started",
            "capability": asdict(capability),
            "data_format": capability.data_format.value
        }
    
    def process_mobile_data(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data from mobile device"""
        
        if session_id not in self.active_sessions:
            return {"error": "Invalid session"}
        
        session = self.active_sessions[session_id]
        plugin_id = session["plugin_id"]
        capability_id = session["capability_id"]
        
        if plugin_id == "golf_pro":
            return self._process_golf_data(capability_id, data)
        else:
            return {"error": "Plugin not implemented"}
    
    def _process_golf_data(self, capability_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process golf plugin data from mobile"""
        
        if capability_id == "golf_swing_analysis":
            analysis_result = {
                "swing_phase": "backswing",
                "tempo_ratio": 2.8,
                "swing_plane_angle": 65.2,
                "feedback": ["Good shoulder turn", "Maintain spine angle"],
                "score": 78.5,
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "capability": capability_id,
                "analysis": analysis_result,
                "status": "success"
            }
        
        return {"error": "Unknown golf capability"}
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a plugin session"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        session["end_time"] = datetime.now().isoformat()
        session["status"] = "ended"
        
        start_time = datetime.fromisoformat(session["start_time"])
        end_time = datetime.fromisoformat(session["end_time"])
        duration = (end_time - start_time).total_seconds()
        
        del self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "status": "ended",
            "duration_seconds": duration
        }
    
    def get_device_sessions(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a device"""
        
        device_sessions = []
        for session in self.active_sessions.values():
            if session["device_id"] == device_id:
                device_sessions.append(session)
        
        return device_sessions
    
    def get_mobile_sdk_config(self, platform: MobilePlatform) -> Dict[str, Any]:
        """Get mobile SDK configuration for a platform"""
        
        base_config = {
            "api_base_url": "http://localhost:8000/api/v1",
            "supported_data_formats": ["json"],
            "max_session_duration": 3600,
            "heartbeat_interval": 30,
        }
        
        platform_specific = {
            MobilePlatform.IOS: {
                "min_ios_version": "14.0",
                "required_frameworks": ["AVFoundation", "CoreMotion", "Vision"],
                "permissions": {
                    "camera": "NSCameraUsageDescription",
                    "microphone": "NSMicrophoneUsageDescription"
                }
            },
            MobilePlatform.ANDROID: {
                "min_api_level": 26,
                "required_permissions": [
                    "android.permission.CAMERA",
                    "android.permission.RECORD_AUDIO",
                    "android.permission.INTERNET"
                ]
            }
        }
        
        config = base_config.copy()
        config.update(platform_specific.get(platform, {}))
        
        return config

# Global mobile bridge instance
mobile_bridge = MobilePluginBridge()

if __name__ == "__main__":
    # Test mobile integration
    print("📱 Testing Mobile Plugin Integration...")
    
    test_device = MobileDeviceInfo(
        device_id="test_iphone_001",
        platform=MobilePlatform.IOS,
        os_version="16.0",
        app_version="1.0.0",
        device_model="iPhone 14 Pro",
        screen_resolution="1179x2556",
        camera_specs={"resolution": "12MP", "fps": 60},
        sensors_available=["camera", "microphone", "accelerometer", "gyroscope"]
    )
    
    registration = mobile_bridge.register_device(test_device)
    print(f"✅ Device registered: {registration['device_id']}")
    print(f"   Compatible plugins: {len(registration['compatible_plugins'])}")
    
    session_result = mobile_bridge.start_session(
        "test_iphone_001", "golf_pro", "golf_swing_analysis"
    )
    print(f"✅ Session started: {session_result['session_id']}")
    
    test_data = {
        "pose_data": {
            "keypoints": [],
            "timestamp": datetime.now().isoformat()
        }
    }
    
    result = mobile_bridge.process_mobile_data(session_result['session_id'], test_data)
    print(f"✅ Data processed: Score {result['analysis']['score']}")
    
    ios_config = mobile_bridge.get_mobile_sdk_config(MobilePlatform.IOS)
    print(f"✅ iOS SDK config: {ios_config['min_ios_version']}")
    
    print("✅ Mobile integration test completed!")