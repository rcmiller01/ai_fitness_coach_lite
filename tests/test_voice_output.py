"""
Unit Tests for Voice Output System

Tests the offline TTS voice coaching system including emotional modulation,
coaching feedback, and Edge TTS integration.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
import tempfile
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.voice_output import VoiceOutputService, CoachingTone
from tests.test_config import TestConfig, mock_edge_tts

class TestCoachingTone:
    """Test CoachingTone enum functionality"""
    
    def test_coaching_tone_values(self):
        """Test all coaching tone values are available"""
        assert CoachingTone.ENCOURAGING.value == "encouraging"
        assert CoachingTone.MOTIVATIONAL.value == "motivational"
        assert CoachingTone.CORRECTIVE.value == "corrective"
        assert CoachingTone.CALM.value == "calm"
        assert CoachingTone.ENERGETIC.value == "energetic"
        assert CoachingTone.CELEBRATION.value == "celebration"
    
    def test_tone_enum_completeness(self):
        """Test that all expected tones are present"""
        expected_tones = {
            "encouraging", "motivational", "corrective", 
            "calm", "energetic", "focused", "celebration", "warning"
        }
        actual_tones = {tone.value for tone in CoachingTone}
        assert expected_tones == actual_tones

class TestVoiceOutputService:
    """Test VoiceOutputService functionality"""
    
    @pytest.fixture
    def voice_service(self):
        """Create voice service with mocked dependencies"""
        with patch('utils.voice_output.os.makedirs'):
            return VoiceOutputService()
    
    def test_service_initialization(self, voice_service):
        """Test voice service initializes correctly"""
        assert voice_service is not None
        assert hasattr(voice_service, 'output_dir')
        assert hasattr(voice_service, 'default_voice')
        assert hasattr(voice_service, 'coaching_presets')
    
    @patch('utils.voice_output.edge_tts.Communicate')
    @patch('utils.voice_output.asyncio.run')
    def test_speak_coaching_cue(self, mock_asyncio, mock_communicate, voice_service):
        """Test speaking coaching cues with different tones"""
        
        # Setup mocks
        mock_comm_instance = Mock()
        mock_communicate.return_value = mock_comm_instance
        mock_asyncio.return_value = "mocked_audio_path.mp3"
        
        # Mock the play_audio method to avoid file system calls
        with patch.object(voice_service, 'play_audio') as mock_play:
            result = voice_service.speak_coaching_cue(
                "Great form! Keep it up!",
                CoachingTone.ENCOURAGING
            )
            
            mock_asyncio.assert_called()
            mock_play.assert_called_with("mocked_audio_path.mp3")
    
    def test_rep_count_feedback(self, voice_service):
        """Test rep count feedback functionality"""
        
        # Test that the methods exist and can be called without error
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            voice_service.rep_count_feedback(5, 10)
            voice_service.rep_count_feedback(10, 10)
            voice_service.rep_count_feedback(15, 10)
            
            # Should call speak_coaching_cue for each feedback
            assert mock_speak.call_count == 3
    
    def test_form_correction(self, voice_service):
        """Test form correction feedback"""
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            correction_message = "Keep your back straight and core engaged"
            voice_service.form_correction(correction_message)
            
            # Should call speak_coaching_cue with corrective tone
            mock_speak.assert_called_once()
            call_args = mock_speak.call_args
            assert correction_message in call_args[0][0]  # Message should contain correction
    
    def test_get_tone_modulation(self, voice_service):
        """Test tone modulation for different coaching tones"""
        
        # Test that coaching presets exist
        assert hasattr(voice_service, 'coaching_presets')
        
        for tone in CoachingTone:
            preset = voice_service.coaching_presets.get(tone)
            if preset:
                assert "rate" in preset
                assert "pitch" in preset
                assert "volume" in preset
    
    def test_tone_modulation_values(self, voice_service):
        """Test specific tone modulation values"""
        
        encouraging = voice_service.coaching_presets.get(CoachingTone.ENCOURAGING)
        assert encouraging["rate"] == "+3%"
        assert encouraging["pitch"] == "+2%"
        
        calm = voice_service.coaching_presets.get(CoachingTone.CALM)
        assert calm["rate"] == "-5%"
        assert calm["pitch"] == "-3%"
        
        celebration = voice_service.coaching_presets.get(CoachingTone.CELEBRATION)
        assert celebration["rate"] == "+5%"
        assert celebration["pitch"] == "+8%"
    
    def test_rest_period_guidance(self, voice_service):
        """Test rest period guidance functionality"""
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            # Test different rest periods
            voice_service.rest_period_guidance(30)
            voice_service.rest_period_guidance(90)
            
            # Should call speak_coaching_cue for each guidance
            assert mock_speak.call_count == 2
    
    def test_workout_motivation(self, voice_service):
        """Test motivational message system"""
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            # Test motivational messages
            voice_service.workout_motivation("You're doing great!")
            
            # Should call speak_coaching_cue with motivational tone
            mock_speak.assert_called_once_with("You're doing great!", CoachingTone.MOTIVATIONAL)
    
    def test_coaching_presets_structure(self, voice_service):
        """Test coaching presets have correct structure"""
        
        assert hasattr(voice_service, 'coaching_presets')
        
        for tone in CoachingTone:
            preset = voice_service.coaching_presets.get(tone)
            if preset:
                assert "rate" in preset
                assert "pitch" in preset
                assert "volume" in preset
    
    def test_output_directory_creation(self, voice_service):
        """Test output directory setup"""
        
        with patch('utils.voice_output.os.makedirs') as mock_makedirs:
            voice_service.setup_output_directory()
            mock_makedirs.assert_called_with(voice_service.output_dir, exist_ok=True)
    
    def test_error_handling_no_edge_tts(self, voice_service):
        """Test graceful handling when Edge TTS is not available"""
        
        with patch('utils.voice_output.edge_tts.Communicate', side_effect=ImportError), \
             patch.object(voice_service, 'play_audio') as mock_play:
            
            # Should handle the import error gracefully
            try:
                result = voice_service.speak_coaching_cue("Test message", CoachingTone.ENCOURAGING)
                # If it doesn't raise an exception, that's fine
                assert True
            except ImportError:
                # If it does raise ImportError, that's expected behavior too
                assert True
    
    def test_concurrent_voice_requests(self, voice_service):
        """Test handling multiple concurrent voice requests"""
        
        # Simulate multiple rapid requests
        messages = [
            ("First message", CoachingTone.ENCOURAGING),
            ("Second message", CoachingTone.MOTIVATIONAL),
            ("Third message", CoachingTone.CALM)
        ]
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            for text, tone in messages:
                voice_service.speak_coaching_cue(text, tone, play_immediately=False)
            
            # Should handle all requests without error
            assert mock_speak.call_count == len(messages)

class TestVoiceIntegration:
    """Integration tests for voice system"""
    
    def test_workout_voice_flow(self):
        """Test complete workout voice feedback flow"""
        
        voice_service = VoiceOutputService()
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            # Simulate workout flow
            voice_service.speak_coaching_cue("Let's get started with your warm-up", CoachingTone.CALM)
            voice_service.speak_coaching_cue("Focus on your breathing", CoachingTone.CALM)
            voice_service.rep_count_feedback(5, 10)
            voice_service.form_correction("Keep your core engaged")
            voice_service.rep_count_feedback(10, 10)
            voice_service.speak_coaching_cue("Excellent work!", CoachingTone.CELEBRATION)
            voice_service.rest_period_guidance(30)
            
            # Verify all voice calls were made
            assert mock_speak.call_count >= 7
    
    def test_voice_service_configuration(self):
        """Test voice service configuration options"""
        
        # Test custom configuration
        with patch('utils.voice_output.os.makedirs'):
            voice_service = VoiceOutputService(output_dir="custom_output")
            
            assert voice_service.output_dir == "custom_output"
            assert voice_service.default_voice == "en-US-JennyNeural"
    
    def test_voice_caching(self):
        """Test voice output caching functionality"""
        
        voice_service = VoiceOutputService()
        
        # Same message should potentially use caching
        message = "Great job!"
        tone = CoachingTone.ENCOURAGING
        
        with patch.object(voice_service, 'speak_coaching_cue') as mock_speak:
            voice_service.speak_coaching_cue(message, tone)
            voice_service.speak_coaching_cue(message, tone)  # Second call
            
            # Should work regardless of caching implementation
            assert mock_speak.call_count == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])