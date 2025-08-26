#!/usr/bin/env python3
"""Simple voice system test"""

from utils.voice_output import VoiceOutputService, CoachingTone

def test_voice():
    print("🔊 Testing Voice System...")
    
    try:
        # Create voice service
        voice_service = VoiceOutputService()
        
        # Test basic speech generation
        audio_path = voice_service.speak_coaching_cue(
            "Great job! Keep pushing through!",
            CoachingTone.MOTIVATIONAL,
            play_immediately=False
        )
        
        print(f"✅ Voice file generated: {audio_path}")
        
        # Test different coaching scenarios
        voice_service.rep_count_feedback(8, 10)
        print("✅ Rep count feedback generated")
        
        voice_service.form_correction("Keep your core engaged")
        print("✅ Form correction feedback generated")
        
        voice_service.workout_complete()
        print("✅ Workout completion celebration generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Voice test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_voice()
    if success:
        print("🎉 Voice system is working!")
    else:
        print("⚠️  Voice system needs attention")