"""
Voice Output Service for AI Fitness Coach

Provides offline-capable text-to-speech with emotional modulation
for fitness coaching, motivation, and form correction feedback.
"""

import edge_tts
import asyncio
import os
from typing import Optional, Dict, Any
from enum import Enum

class CoachingTone(Enum):
    """Different coaching tones for various fitness scenarios"""
    MOTIVATIONAL = "motivational"
    ENCOURAGING = "encouraging"
    CORRECTIVE = "corrective"
    CALM = "calm"
    ENERGETIC = "energetic"
    FOCUSED = "focused"
    CELEBRATION = "celebration"
    WARNING = "warning"

class VoiceOutputService:
    """
    Fitness-focused voice output service with emotional modulation
    """
    
    def __init__(self, output_dir: str = "audio_output"):
        self.output_dir = output_dir
        self.default_voice = "en-US-JennyNeural"
        self.setup_output_directory()
        
        # Fitness-specific voice presets optimized for coaching
        self.coaching_presets = {
            CoachingTone.MOTIVATIONAL: {
                "rate": "+8%", "pitch": "+5%", "volume": "+10%"
            },
            CoachingTone.ENCOURAGING: {
                "rate": "+3%", "pitch": "+2%", "volume": "+5%"
            },
            CoachingTone.CORRECTIVE: {
                "rate": "-2%", "pitch": "-1%", "volume": "0%"
            },
            CoachingTone.CALM: {
                "rate": "-5%", "pitch": "-3%", "volume": "-5%"
            },
            CoachingTone.ENERGETIC: {
                "rate": "+10%", "pitch": "+7%", "volume": "+15%"
            },
            CoachingTone.FOCUSED: {
                "rate": "0%", "pitch": "0%", "volume": "0%"
            },
            CoachingTone.CELEBRATION: {
                "rate": "+5%", "pitch": "+8%", "volume": "+20%"
            },
            CoachingTone.WARNING: {
                "rate": "-3%", "pitch": "-2%", "volume": "+10%"
            }
        }
    
    def setup_output_directory(self):
        """Create output directory if it doesn't exist"""
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def generate_speech(
        self, 
        text: str, 
        tone: CoachingTone = CoachingTone.ENCOURAGING,
        voice: str = None,
        filename: str = None
    ) -> str:
        """
        Generate speech file with specified coaching tone
        
        Args:
            text: Text to convert to speech
            tone: Coaching tone to apply
            voice: Voice to use (defaults to self.default_voice)
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to generated audio file
        """
        if voice is None:
            voice = self.default_voice
            
        if filename is None:
            filename = f"coach_output_{tone.value}.mp3"
            
        output_path = os.path.join(self.output_dir, filename)
        preset = self.coaching_presets.get(tone, self.coaching_presets[CoachingTone.ENCOURAGING])
        
        # For now, use simple text with voice modulation
        # TODO: Implement SSML when edge-tts supports it properly
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        return output_path
    
    def speak_coaching_cue(
        self, 
        text: str, 
        tone: CoachingTone = CoachingTone.ENCOURAGING,
        play_immediately: bool = True
    ) -> str:
        """
        Synchronous wrapper for coaching cues during workouts
        
        Args:
            text: Coaching text to speak
            tone: Coaching tone
            play_immediately: Whether to play audio immediately
            
        Returns:
            Path to generated audio file
        """
        audio_path = asyncio.run(self.generate_speech(text, tone))
        
        if play_immediately:
            self.play_audio(audio_path)
            
        return audio_path
    
    def play_audio(self, audio_path: str):
        """Play generated audio file"""
        if os.path.exists(audio_path):
            if os.name == "nt":  # Windows
                os.system(f'start "" "{audio_path}"')
            else:  # macOS/Linux
                os.system(f'xdg-open "{audio_path}"')
    
    # Fitness-specific coaching methods
    def rep_count_feedback(self, current_reps: int, target_reps: int):
        """Provide rep count feedback"""
        if current_reps == target_reps:
            self.speak_coaching_cue(
                f"Perfect! {current_reps} reps completed!", 
                CoachingTone.CELEBRATION
            )
        elif current_reps > target_reps * 0.8:
            self.speak_coaching_cue(
                f"Great work! {current_reps} down, {target_reps - current_reps} to go!", 
                CoachingTone.ENCOURAGING
            )
        else:
            self.speak_coaching_cue(
                f"Keep pushing! {current_reps} reps done!", 
                CoachingTone.MOTIVATIONAL
            )
    
    def form_correction(self, correction_message: str):
        """Provide form correction feedback"""
        self.speak_coaching_cue(
            f"Form check: {correction_message}", 
            CoachingTone.CORRECTIVE
        )
    
    def rest_period_guidance(self, rest_seconds: int):
        """Guide through rest periods"""
        if rest_seconds > 60:
            self.speak_coaching_cue(
                f"Take {rest_seconds} seconds to recover. Breathe deeply.", 
                CoachingTone.CALM
            )
        else:
            self.speak_coaching_cue(
                f"Quick {rest_seconds} second rest. Stay focused!", 
                CoachingTone.FOCUSED
            )
    
    def workout_motivation(self, message: str):
        """Provide motivational messages"""
        self.speak_coaching_cue(message, CoachingTone.MOTIVATIONAL)
    
    def safety_warning(self, warning_message: str):
        """Provide safety warnings"""
        self.speak_coaching_cue(
            f"Safety alert: {warning_message}", 
            CoachingTone.WARNING
        )
    
    def workout_complete(self):
        """Celebrate workout completion"""
        self.speak_coaching_cue(
            "Outstanding work! Workout complete. You crushed it today!", 
            CoachingTone.CELEBRATION
        )

# Convenience function for quick coaching cues
def quick_coach_speak(text: str, tone: CoachingTone = CoachingTone.ENCOURAGING):
    """Quick function for immediate coaching feedback"""
    service = VoiceOutputService()
    return service.speak_coaching_cue(text, tone)

# Example usage and testing
if __name__ == "__main__":
    # Test the voice service
    coach = VoiceOutputService()
    
    # Test different coaching scenarios
    coach.rep_count_feedback(8, 10)
    coach.form_correction("Keep your back straight and core engaged")
    coach.rest_period_guidance(90)
    coach.workout_motivation("You're stronger than you think! Push through!")
    coach.safety_warning("Weight is too heavy, reduce load")
    coach.workout_complete()