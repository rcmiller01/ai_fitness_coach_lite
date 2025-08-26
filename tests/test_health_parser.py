"""
Unit Tests for Health Data Parser

Tests all functionality of the health data integration system including
HealthKit/Google Fit data processing, profile management, and readiness assessment.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.health_parser import (
    HealthDataParser, HealthProfile, SleepData, HeartRateData,
    HealthCondition, SleepQuality, HealthDataSource
)
from tests.test_config import TestConfig, TestHelpers, mock_file_operations

class TestHealthProfile:
    """Test HealthProfile data class"""
    
    def test_health_profile_creation(self, mock_user_profile):
        """Test creating a health profile"""
        profile = HealthProfile(
            user_id=mock_user_profile["user_id"],
            age=mock_user_profile["age"],
            sex=mock_user_profile["sex"],
            height_cm=mock_user_profile["height_cm"],
            conditions=[HealthCondition.NONE],
            fitness_level=mock_user_profile["fitness_level"],
            goals=mock_user_profile["goals"]
        )
        
        assert profile.user_id == "test_user_001"
        assert profile.age == 30
        assert profile.sex == "M"
        assert profile.height_cm == 175.0
        assert profile.fitness_level == "intermediate"
        assert len(profile.goals) == 2
    
    def test_health_profile_validation(self):
        """Test health profile field validation"""
        # Test invalid age
        with pytest.raises(ValueError):
            HealthProfile(
                user_id="test",
                age=10,  # Too young
                sex="M",
                height_cm=175.0,
                conditions=[],
                fitness_level="intermediate",
                goals=[]
            )

class TestSleepData:
    """Test SleepData functionality"""
    
    def test_sleep_data_creation(self, mock_sleep_data):
        """Test creating sleep data"""
        sleep = SleepData(
            date=mock_sleep_data["date"],
            start_time=mock_sleep_data["start_time"],
            end_time=mock_sleep_data["end_time"],
            duration_hours=mock_sleep_data["duration_hours"],
            quality=SleepQuality(mock_sleep_data["quality"]),
            source=HealthDataSource.MANUAL
        )
        
        assert sleep.date == "2024-08-26"
        assert sleep.duration_hours == 8.0
        assert sleep.quality == SleepQuality.DEEP
    
    def test_sleep_quality_score(self):
        """Test sleep quality scoring"""
        sleep = SleepData(
            date="2024-08-26",
            start_time="23:00",
            end_time="07:00",
            duration_hours=8.0,
            quality=SleepQuality.DEEP,
            source=HealthDataSource.MANUAL
        )
        
        score = sleep.get_quality_score()
        assert 80 <= score <= 100  # Deep sleep should score high

class TestHeartRateData:
    """Test HeartRateData functionality"""
    
    def test_heart_rate_creation(self):
        """Test creating heart rate data"""
        hr = HeartRateData(
            timestamp=datetime.now().isoformat(),
            bpm=75,
            context="rest",
            source=HealthDataSource.MANUAL
        )
        
        assert hr.bpm == 75
        assert hr.context == "rest"
    
    def test_heart_rate_validation(self):
        """Test heart rate validation"""
        with pytest.raises(ValueError):
            HeartRateData(
                timestamp=datetime.now().isoformat(),
                bpm=250,  # Too high
                context="rest",
                source=HealthDataSource.MANUAL
            )

class TestHealthDataParser:
    """Test HealthDataParser main functionality"""
    
    @pytest.fixture
    def parser(self, mock_file_operations):
        """Create health data parser with mocked file operations"""
        return HealthDataParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly"""
        assert parser is not None
        assert hasattr(parser, 'data_dir')
        assert hasattr(parser, 'user_profile')
    
    @patch('core.health_parser.os.makedirs')
    @patch('core.health_parser.os.path.exists', return_value=False)
    def test_create_health_profile(self, mock_exists, mock_makedirs, parser, mock_user_profile):
        """Test creating and storing health profile"""
        profile = HealthProfile(
            user_id=mock_user_profile["user_id"],
            age=mock_user_profile["age"],
            sex=mock_user_profile["sex"],
            height_cm=mock_user_profile["height_cm"],
            conditions=[HealthCondition.NONE],
            fitness_level=mock_user_profile["fitness_level"],
            goals=mock_user_profile["goals"]
        )
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump:
            
            result = parser.create_health_profile(profile)
            
            assert result["status"] == "success"
            assert result["profile"]["user_id"] == "test_user_001"
            mock_file.assert_called()
            mock_json_dump.assert_called()
    
    @patch('core.health_parser.os.path.exists', return_value=True)
    def test_get_health_profile(self, mock_exists, parser, mock_user_profile):
        """Test retrieving health profile"""
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_user_profile))), \
             patch('json.load', return_value=mock_user_profile):
            
            profile = parser.get_health_profile()
            
            assert profile is not None
            assert profile.user_id == "test_user_001"
    
    def test_store_sleep_data(self, parser, mock_sleep_data):
        """Test storing sleep data"""
        sleep = SleepData(
            date=mock_sleep_data["date"],
            start_time=mock_sleep_data["start_time"],
            end_time=mock_sleep_data["end_time"],
            duration_hours=mock_sleep_data["duration_hours"],
            quality=SleepQuality(mock_sleep_data["quality"]),
            source=HealthDataSource.MANUAL
        )
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump, \
             patch('core.health_parser.os.path.exists', return_value=False), \
             patch('core.health_parser.os.makedirs'):
            
            result = parser.store_sleep_data(sleep)
            
            assert "sleep_data" in result
            mock_file.assert_called()
    
    def test_store_heart_rate_data(self, parser):
        """Test storing heart rate data"""
        hr = HeartRateData(
            timestamp=datetime.now().isoformat(),
            bpm=75,
            context="rest",
            source=HealthDataSource.MANUAL
        )
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump, \
             patch('core.health_parser.os.path.exists', return_value=False), \
             patch('core.health_parser.os.makedirs'):
            
            result = parser.store_heart_rate_data(hr)
            
            assert "heart_rate_data" in result
            mock_file.assert_called()
    
    def test_get_readiness_assessment(self, parser):
        """Test workout readiness assessment"""
        
        # Mock sleep data indicating good rest
        mock_sleep = [
            {
                "date": "2024-08-26",
                "duration_hours": 8.0,
                "quality": "deep"
            }
        ]
        
        # Mock heart rate data indicating low resting HR
        mock_hr = [
            {
                "timestamp": datetime.now().isoformat(),
                "bpm": 60,
                "context": "rest"
            }
        ]
        
        with patch('core.health_parser.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('json.load', side_effect=[mock_sleep, mock_hr]):
            
            assessment = parser.get_readiness_assessment()
            
            assert "readiness_score" in assessment
            assert "recommendation" in assessment
            assert 0 <= assessment["readiness_score"] <= 100
    
    def test_sleep_analysis(self, parser):
        """Test sleep analysis functionality"""
        
        # Mock week of sleep data
        mock_sleep_week = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            mock_sleep_week.append({
                "date": date,
                "duration_hours": 7.5 + (i * 0.1),  # Varying sleep duration
                "quality": "deep" if i % 2 == 0 else "light"
            })
        
        with patch('core.health_parser.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('json.load', return_value=mock_sleep_week):
            
            analysis = parser.get_sleep_analysis(days=7)
            
            assert "average_duration" in analysis
            assert "sleep_debt" in analysis
            assert "quality_distribution" in analysis
            assert "trends" in analysis
    
    def test_export_health_data(self, parser):
        """Test health data export functionality"""
        
        with patch('core.health_parser.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('json.load', return_value={}), \
             patch('zipfile.ZipFile') as mock_zip:
            
            export_path = parser.export_health_data()
            
            assert export_path.endswith('.zip')
            mock_zip.assert_called()

class TestHealthDataIntegration:
    """Integration tests for health data system"""
    
    def test_full_health_workflow(self, mock_file_operations):
        """Test complete health data workflow"""
        parser = HealthDataParser()
        
        # Create profile
        profile = HealthProfile(
            user_id="integration_test",
            age=25,
            sex="F",
            height_cm=165.0,
            conditions=[HealthCondition.NONE],
            fitness_level="beginner",
            goals=["weight_loss"]
        )
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json_dump, \
             patch('json.load', return_value={"user_id": "integration_test"}), \
             patch('core.health_parser.os.path.exists', return_value=True), \
             patch('core.health_parser.os.makedirs'):
            
            # Create profile
            result = parser.create_health_profile(profile)
            assert result["status"] == "success"
            
            # Add sleep data
            sleep = SleepData(
                date="2024-08-26",
                start_time="23:30",
                end_time="07:30",
                duration_hours=8.0,
                quality=SleepQuality.DEEP,
                source=HealthDataSource.MANUAL
            )
            
            sleep_result = parser.store_sleep_data(sleep)
            assert "sleep_data" in sleep_result
            
            # Add heart rate data
            hr = HeartRateData(
                timestamp=datetime.now().isoformat(),
                bpm=65,
                context="rest",
                source=HealthDataSource.MANUAL
            )
            
            hr_result = parser.store_heart_rate_data(hr)
            assert "heart_rate_data" in hr_result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])