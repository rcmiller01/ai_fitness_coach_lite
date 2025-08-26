"""
License Server Simulation for Integration Testing

Simulates a remote license server for testing plugin licensing,
activation codes, and online validation scenarios.
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Tuple, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class LicenseType(Enum):
    """License types"""
    TRIAL = "trial"
    PERSONAL = "personal" 
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class ServerLicense:
    """Server-side license record"""
    license_key: str
    plugin_id: str
    license_type: LicenseType
    user_id: str
    device_id: Optional[str]
    activation_date: str
    expiry_date: Optional[str]
    max_activations: int
    current_activations: int
    features: List[str]
    created_date: str
    last_validated: Optional[str]
    is_active: bool

@dataclass
class ActivationCode:
    """Activation code record"""
    code: str
    plugin_id: str
    license_type: LicenseType
    features: List[str]
    max_uses: int
    current_uses: int
    expiry_date: Optional[str]
    created_date: str
    is_active: bool

class LicenseServerSimulator:
    """Simulates license server for testing"""
    
    def __init__(self):
        self.licenses: Dict[str, ServerLicense] = {}
        self.activation_codes: Dict[str, ActivationCode] = {}
        self.device_registrations: Dict[str, Dict[str, Any]] = {}
        self.validation_logs: List[Dict[str, Any]] = []
        
        # Initialize with test data
        self._initialize_test_data()
    
    def _initialize_test_data(self):
        """Initialize test data for integration testing"""
        
        # Create test activation codes
        golf_code = ActivationCode(
            code="GOLF2024PROMO",
            plugin_id="golf_pro",
            license_type=LicenseType.PERSONAL,
            features=["swing_analysis", "voice_coaching", "progress_tracking"],
            max_uses=1000,
            current_uses=0,
            expiry_date=(datetime.now() + timedelta(days=90)).isoformat(),
            created_date=datetime.now().isoformat(),
            is_active=True
        )
        
        tennis_code = ActivationCode(
            code="TENNIS2024",
            plugin_id="tennis_pro", 
            license_type=LicenseType.PROFESSIONAL,
            features=["stroke_analysis", "serve_analysis", "match_analytics"],
            max_uses=500,
            current_uses=0,
            expiry_date=(datetime.now() + timedelta(days=60)).isoformat(),
            created_date=datetime.now().isoformat(),
            is_active=True
        )
        
        self.activation_codes = {
            "GOLF2024PROMO": golf_code,
            "TENNIS2024": tennis_code
        }
    
    def redeem_activation_code(self, code: str) -> Tuple[bool, Dict[str, Any]]:
        """Redeem an activation code for a license"""
        
        if code not in self.activation_codes:
            return False, {"error": "Invalid activation code"}
        
        activation_code = self.activation_codes[code]
        
        if not activation_code.is_active:
            return False, {"error": "Activation code is inactive"}
        
        if activation_code.current_uses >= activation_code.max_uses:
            return False, {"error": "Activation code usage limit exceeded"}
        
        if activation_code.expiry_date:
            expiry = datetime.fromisoformat(activation_code.expiry_date)
            if datetime.now() > expiry:
                return False, {"error": "Activation code has expired"}
        
        # Generate license key
        license_key = self._generate_license_key(activation_code.plugin_id)
        
        # Update usage count
        activation_code.current_uses += 1
        
        return True, {
            "plugin_id": activation_code.plugin_id,
            "license_key": license_key,
            "license_type": activation_code.license_type.value,
            "features": activation_code.features,
            "expiry_date": (datetime.now() + timedelta(days=365)).isoformat()
        }
    
    def generate_trial_license(self, plugin_id: str, device_id: str, 
                             trial_days: int) -> Tuple[bool, Dict[str, Any]]:
        """Generate a trial license"""
        
        # Check if device already used trial for this plugin
        device_key = f"{device_id}_{plugin_id}"
        if device_key in self.device_registrations:
            device_info = self.device_registrations[device_key]
            if device_info.get("trial_used", False):
                return False, {"error": "Trial already used for this device"}
        
        # Generate trial license
        trial_license_key = f"TRIAL_{self._generate_license_key(plugin_id)}"
        expiry_date = (datetime.now() + timedelta(days=trial_days)).isoformat()
        
        # Create server license record
        trial_license = ServerLicense(
            license_key=trial_license_key,
            plugin_id=plugin_id,
            license_type=LicenseType.TRIAL,
            user_id="trial_user",
            device_id=device_id,
            activation_date=datetime.now().isoformat(),
            expiry_date=expiry_date,
            max_activations=1,
            current_activations=1,
            features=self._get_trial_features(plugin_id),
            created_date=datetime.now().isoformat(),
            last_validated=datetime.now().isoformat(),
            is_active=True
        )
        
        self.licenses[trial_license_key] = trial_license
        
        # Mark device as trial used
        self.device_registrations[device_key] = {
            "device_id": device_id,
            "plugin_id": plugin_id,
            "trial_used": True,
            "trial_date": datetime.now().isoformat()
        }
        
        return True, {
            "trial_license_key": trial_license_key,
            "expiry_date": expiry_date,
            "features": trial_license.features,
            "device_id": device_id
        }
    
    def validate_license_online(self, license_key: str, device_id: str) -> Dict[str, Any]:
        """Validate license online"""
        
        validation_log = {
            "license_key": license_key,
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "ip_address": "127.0.0.1"  # Simulated
        }
        
        if license_key not in self.licenses:
            validation_log["result"] = "failed"
            validation_log["reason"] = "License not found"
            self.validation_logs.append(validation_log)
            
            return {
                "success": False,
                "data": {"error": "License not found"}
            }
        
        license_data = self.licenses[license_key]
        
        # Check if license is active
        if not license_data.is_active:
            validation_log["result"] = "failed"
            validation_log["reason"] = "License inactive"
            self.validation_logs.append(validation_log)
            
            return {
                "success": False,
                "data": {"error": "License is inactive"}
            }
        
        # Check expiry
        if license_data.expiry_date:
            expiry = datetime.fromisoformat(license_data.expiry_date)
            if datetime.now() > expiry:
                validation_log["result"] = "failed"
                validation_log["reason"] = "License expired"
                self.validation_logs.append(validation_log)
                
                return {
                    "success": False,
                    "data": {"error": "License has expired"}
                }
        
        # Check device binding
        if license_data.device_id and license_data.device_id != device_id:
            validation_log["result"] = "failed"
            validation_log["reason"] = "Device mismatch"
            self.validation_logs.append(validation_log)
            
            return {
                "success": False,
                "data": {"error": "License not valid for this device"}
            }
        
        # Check activation limit
        if license_data.current_activations >= license_data.max_activations:
            validation_log["result"] = "failed"
            validation_log["reason"] = "Activation limit exceeded"
            self.validation_logs.append(validation_log)
            
            return {
                "success": False,
                "data": {"error": "Activation limit exceeded"}
            }
        
        # Update last validated
        license_data.last_validated = datetime.now().isoformat()
        
        validation_log["result"] = "success"
        validation_log["plugin_id"] = license_data.plugin_id
        validation_log["license_type"] = license_data.license_type.value
        self.validation_logs.append(validation_log)
        
        return {
            "success": True,
            "data": {
                "plugin_id": license_data.plugin_id,
                "license_type": license_data.license_type.value,
                "features": license_data.features,
                "expiry_date": license_data.expiry_date,
                "last_validated": license_data.last_validated
            }
        }
    
    def activate_license(self, license_key: str, device_id: str) -> Dict[str, Any]:
        """Activate a license for a device"""
        
        if license_key not in self.licenses:
            return {
                "success": False,
                "error": "License not found"
            }
        
        license_data = self.licenses[license_key]
        
        # Check if already activated for this device
        if license_data.device_id and license_data.device_id != device_id:
            if license_data.current_activations >= license_data.max_activations:
                return {
                    "success": False,
                    "error": "License already activated on maximum devices"
                }
        
        # Activate license
        if not license_data.device_id:
            license_data.device_id = device_id
            license_data.activation_date = datetime.now().isoformat()
        
        license_data.current_activations += 1
        license_data.last_validated = datetime.now().isoformat()
        
        return {
            "success": True,
            "activation_date": license_data.activation_date,
            "device_id": device_id,
            "features": license_data.features
        }
    
    def get_user_licenses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all licenses for a user"""
        
        user_licenses = []
        for license_data in self.licenses.values():
            if license_data.user_id == user_id:
                user_licenses.append({
                    "license_key": license_data.license_key,
                    "plugin_id": license_data.plugin_id,
                    "license_type": license_data.license_type.value,
                    "activation_date": license_data.activation_date,
                    "expiry_date": license_data.expiry_date,
                    "is_active": license_data.is_active,
                    "features": license_data.features
                })
        
        return user_licenses
    
    def revoke_license(self, license_key: str) -> bool:
        """Revoke a license"""
        
        if license_key in self.licenses:
            self.licenses[license_key].is_active = False
            return True
        
        return False
    
    def get_validation_logs(self, plugin_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get validation logs"""
        
        if plugin_id:
            return [log for log in self.validation_logs if log.get("plugin_id") == plugin_id]
        
        return self.validation_logs
    
    def _generate_license_key(self, plugin_id: str) -> str:
        """Generate a license key"""
        
        base_string = f"{plugin_id}_{datetime.now().isoformat()}_{uuid.uuid4()}"
        hash_object = hashlib.sha256(base_string.encode())
        return hash_object.hexdigest()[:32].upper()
    
    def _get_trial_features(self, plugin_id: str) -> List[str]:
        """Get trial features for a plugin"""
        
        trial_features = {
            "golf_pro": ["swing_analysis", "basic_feedback"],
            "tennis_pro": ["stroke_analysis", "basic_tips"],
            "basketball_pro": ["shooting_analysis", "basic_coaching"]
        }
        
        return trial_features.get(plugin_id, ["basic_analysis"])

# Simulation function for testing
def simulate_online_validation(license_key: str, device_id: str) -> Dict[str, Any]:
    """Simulate online license validation"""
    
    # Create temporary server instance
    server = LicenseServerSimulator()
    
    # Create a test license for simulation
    if license_key == "VALID_LICENSE_123":
        test_license = ServerLicense(
            license_key=license_key,
            plugin_id="golf_pro",
            license_type=LicenseType.PERSONAL,
            user_id="test_user",
            device_id=device_id,
            activation_date=datetime.now().isoformat(),
            expiry_date=(datetime.now() + timedelta(days=365)).isoformat(),
            max_activations=3,
            current_activations=1,
            features=["swing_analysis", "voice_coaching"],
            created_date=datetime.now().isoformat(),
            last_validated=None,
            is_active=True
        )
        server.licenses[license_key] = test_license
    
    return server.validate_license_online(license_key, device_id)

# Global license server instance for testing
license_server = LicenseServerSimulator()

if __name__ == "__main__":
    # Test license server functionality
    print("🔒 Testing License Server Simulator...")
    
    server = LicenseServerSimulator()
    
    # Test activation code redemption
    print("\n1. Testing activation code redemption...")
    success, result = server.redeem_activation_code("GOLF2024PROMO")
    if success:
        print(f"✅ Code redeemed: {result['plugin_id']}")
        print(f"   License Key: {result['license_key']}")
        print(f"   Features: {result['features']}")
    
    # Test trial license generation
    print("\n2. Testing trial license generation...")
    trial_success, trial_result = server.generate_trial_license("tennis_pro", "test_device_001", 7)
    if trial_success:
        print(f"✅ Trial generated: {trial_result['trial_license_key']}")
        print(f"   Expires: {trial_result['expiry_date']}")
    
    # Test license validation
    print("\n3. Testing license validation...")
    if trial_success:
        validation_result = server.validate_license_online(
            trial_result['trial_license_key'], 
            "test_device_001"
        )
        if validation_result['success']:
            print(f"✅ License validated: {validation_result['data']['plugin_id']}")
        else:
            print(f"❌ Validation failed: {validation_result['data']['error']}")
    
    # Test validation logs
    print("\n4. Testing validation logs...")
    logs = server.get_validation_logs()
    print(f"✅ Generated {len(logs)} validation log entries")
    
    print("\n✅ License server simulation test completed!")