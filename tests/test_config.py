"""
AI Fitness Coach Lite - Comprehensive Testing Framework

Test configuration and utilities for all core components.
Following project testing specifications and ensuring robust test coverage.
"""

import pytest
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from datetime import datetime, timedelta

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class TestConfig:
    """Test configuration and constants"""
    
    # Test data directories
    TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")
    TEMP_DATA_DIR = tempfile.mkdtemp()
    
    # Mock data for testing
    MOCK_USER_PROFILE = {
        "user_id": "test_user_001",
        "age": 30,
        "sex": "M",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "fitness_level": "intermediate",
        "goals": ["strength", "weight_loss"],
        "conditions": []
    }
    
    MOCK_SLEEP_DATA = {
        "date": "2024-08-26",
        "start_time": "23:00",
        "end_time": "07:00",
        "duration_hours": 8.0,
        "quality": "deep"
    }
    
    MOCK_WORKOUT_SESSION = {
        "date": "2024-08-26T10:00:00",
        "workout_type": "strength",
        "exercises": [
            {
                "name": "Push-ups",
                "category": "upper_body",
                "sets": [
                    {"reps": 15, "weight": None, "rpe": 7}
                ]
            }
        ],
        "duration_minutes": 45,
        "workout_rating": 8
    }
    
    MOCK_POSE_DATA = {
        "keypoints": [
            {"name": "left_shoulder", "x": 0.3, "y": 0.4, "confidence": 0.9},
            {"name": "right_shoulder", "x": 0.7, "y": 0.4, "confidence": 0.9},
            {"name": "left_hip", "x": 0.3, "y": 0.7, "confidence": 0.8},
            {"name": "right_hip", "x": 0.7, "y": 0.7, "confidence": 0.8}
        ],
        "timestamp": "2024-08-26T10:00:00",
        "confidence": 0.85
    }
    
    MOCK_DEVICE_INFO = {
        "device_id": "test_device_001",
        "platform": "ios",
        "os_version": "16.0",
        "app_version": "1.0.0",
        "device_model": "iPhone 14 Pro",
        "screen_resolution": "1179x2556",
        "camera_specs": {"resolution": "12MP", "fps": 60},
        "sensors_available": ["camera", "microphone", "accelerometer", "gyroscope"]
    }

class MockServices:
    """Mock services for testing without external dependencies"""
    
    @staticmethod
    def mock_edge_tts():
        """Mock Edge TTS service"""
        mock_communicate = Mock()
        mock_communicate.save.return_value = None
        return mock_communicate
    
    @staticmethod
    def mock_pose_estimator():
        """Mock pose estimator"""
        mock_estimator = Mock()
        mock_estimator.process_frame.return_value = TestConfig.MOCK_POSE_DATA
        mock_estimator.is_available = True
        return mock_estimator
    
    @staticmethod
    def mock_file_system():
        """Mock file system operations"""
        return {
            "read": Mock(return_value="{}"),
            "write": Mock(return_value=True),
            "exists": Mock(return_value=True),
            "makedirs": Mock(return_value=True)
        }

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests"""
    return TestConfig.TEMP_DATA_DIR

@pytest.fixture
def mock_user_profile():
    """Provide mock user profile data"""
    return TestConfig.MOCK_USER_PROFILE.copy()

@pytest.fixture
def mock_sleep_data():
    """Provide mock sleep data"""
    return TestConfig.MOCK_SLEEP_DATA.copy()

@pytest.fixture
def mock_workout_session():
    """Provide mock workout session data"""
    return TestConfig.MOCK_WORKOUT_SESSION.copy()

@pytest.fixture
def mock_pose_data():
    """Provide mock pose data"""
    return TestConfig.MOCK_POSE_DATA.copy()

@pytest.fixture
def mock_device_info():
    """Provide mock device information"""
    return TestConfig.MOCK_DEVICE_INFO.copy()

@pytest.fixture
def mock_edge_tts():
    """Mock Edge TTS for voice testing"""
    with patch('edge_tts.Communicate') as mock_comm:
        mock_comm.return_value = MockServices.mock_edge_tts()
        yield mock_comm

@pytest.fixture
def mock_pose_estimator():
    """Mock pose estimator for ML testing"""
    return MockServices.mock_pose_estimator()

@pytest.fixture
def mock_file_operations():
    """Mock file operations"""
    mocks = MockServices.mock_file_system()
    with patch('builtins.open'), \
         patch('os.path.exists', mocks['exists']), \
         patch('os.makedirs', mocks['makedirs']), \
         patch('json.load', return_value={}), \
         patch('json.dump', return_value=None):
        yield mocks

def create_test_data_files():
    """Create test data files for testing"""
    os.makedirs(TestConfig.TEST_DATA_DIR, exist_ok=True)
    
    # Create test configuration files
    test_files = {
        "user_profile.json": TestConfig.MOCK_USER_PROFILE,
        "sleep_data.json": [TestConfig.MOCK_SLEEP_DATA],
        "workout_history.json": [TestConfig.MOCK_WORKOUT_SESSION],
        "plugin_manifest.json": {
            "id": "test_plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "Test plugin for unit testing",
            "author": "Test Team",
            "plugin_type": "sport_analysis",
            "price": 0.0,
            "trial_days": 0,
            "requires_core_version": "1.0.0"
        }
    }
    
    for filename, data in test_files.items():
        filepath = os.path.join(TestConfig.TEST_DATA_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

class TestHelpers:
    """Helper functions for testing"""
    
    @staticmethod
    def assert_api_response(response, expected_status=200, expected_keys=None):
        """Assert API response format"""
        assert response.status_code == expected_status
        
        if expected_keys:
            response_data = response.json()
            for key in expected_keys:
                assert key in response_data
    
    @staticmethod
    def create_mock_plugin(plugin_id="test_plugin", price=0.0, trial_days=0):
        """Create mock plugin for testing"""
        from plugins.core.plugin_manager import PluginManifest, PluginType
        
        return PluginManifest(
            id=plugin_id,
            name=f"Test Plugin {plugin_id}",
            version="1.0.0",
            description="Test plugin for unit testing",
            author="Test Team",
            plugin_type=PluginType.SPORT_ANALYSIS,
            price=price,
            trial_days=trial_days,
            requires_core_version="1.0.0",
            dependencies=[],
            permissions=[],
            entry_point="test_plugin.py",
            icon="test_icon.png",
            screenshots=[],
            tags=["test"],
            created_date=datetime.now().isoformat(),
            updated_date=datetime.now().isoformat()
        )
    
    @staticmethod
    def create_mock_license(plugin_id="test_plugin", is_trial=False, is_expired=False):
        """Create mock license for testing"""
        from plugins.core.plugin_manager import PluginLicense
        
        expiry_date = None
        if is_trial or is_expired:
            if is_expired:
                expiry_date = (datetime.now() - timedelta(days=1)).isoformat()
            else:
                expiry_date = (datetime.now() + timedelta(days=7)).isoformat()
        
        return PluginLicense(
            plugin_id=plugin_id,
            license_key="TEST_LICENSE_KEY" if not is_trial else "TRIAL",
            activation_date=datetime.now().isoformat(),
            expiry_date=expiry_date,
            device_id="test_device_001",
            trial_used=is_trial,
            activation_count=1
        )

# Initialize test data when module is imported
if __name__ != "__main__":
    create_test_data_files()