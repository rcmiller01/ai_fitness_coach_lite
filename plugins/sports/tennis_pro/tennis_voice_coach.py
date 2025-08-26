"""
Tennis Pro Voice Coaching System

Provides real-time audio coaching feedback for tennis strokes with 
technique-specific guidance and motivational coaching.
"""

import asyncio
from typing import Dict, List, Any, Optional
from enum import Enum
import random
import json
from datetime import datetime

# Import core voice system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'core'))
from voice_output import VoiceOutputService, CoachingTone

class TennisVoiceCoach:
    """Tennis-specific voice coaching system"""
    
    def __init__(self):
        self.voice_service = VoiceOutputService()
        self.coaching_phrases = self._load_tennis_phrases()
        self.last_feedback_time = 0
        self.feedback_cooldown = 3.0  # seconds between feedback
    
    def _load_tennis_phrases(self) -> Dict[str, List[str]]:
        """Load tennis-specific coaching phrases"""
        return {
            "serve_preparation": [
                "Good stance! Keep your feet shoulder-width apart.",
                "Perfect ball toss position. Now drive up through your legs.",
                "Excellent trophy position. Snap that wrist at contact!",
                "Great preparation. Trust your technique and accelerate through."
            ],
            "serve_power": [
                "Use your legs! Drive up through the serve.",
                "Snap your wrist at contact for more power.",
                "Excellent racket head speed! Keep that acceleration.",
                "Perfect! You're really driving through that serve."
            ],
            "serve_accuracy": [
                "Watch that ball toss - keep it consistent.",
                "Great follow through! Right where you're aiming.",
                "Perfect contact point. That's how you place a serve.",
                "Excellent control! Your accuracy is improving."
            ],
            "forehand_technique": [
                "Beautiful shoulder turn! Now drive through the ball.",
                "Perfect timing! You're really catching that ball in front.",
                "Excellent follow through over the shoulder.",
                "Great footwork! You're setting up perfectly for each shot."
            ],
            "forehand_power": [
                "Rotate those hips! Generate power from your core.",
                "Perfect! You're really accelerating through contact.",
                "Excellent weight transfer. That's how you hit with power.",
                "Great extension! You're really driving through that forehand."
            ],
            "forehand_topspin": [
                "Perfect low-to-high swing path for topspin.",
                "Great brushing action! That ball is really spinning.",
                "Excellent wrist snap. You're creating beautiful topspin.",
                "Perfect technique! That topspin will keep the ball in."
            ],
            "backhand_technique": [
                "Excellent preparation! Turn those shoulders early.",
                "Perfect contact point in front of your body.",
                "Great follow through! Nice and controlled.",
                "Beautiful technique! Your backhand is really improving."
            ],
            "backhand_slice": [
                "Perfect high-to-low motion for that slice.",
                "Excellent underspin! Great for approach shots.",
                "Beautiful slice technique. That ball will stay low.",
                "Perfect timing on that slice backhand."
            ],
            "volley_technique": [
                "Perfect ready position at the net!",
                "Excellent short backswing. That's net play!",
                "Great firm wrist through contact.",
                "Perfect! You're really controlling those volleys."
            ],
            "general_encouragement": [
                "Fantastic stroke! Your technique is really coming together.",
                "Excellent work! You're showing great improvement.",
                "Beautiful tennis! Keep up that consistent form.",
                "Great session! Your strokes are looking professional.",
                "Perfect! You're playing like a pro today.",
                "Wonderful technique! That's championship-level form."
            ],
            "improvement_needed": [
                "Keep practicing! Focus on the fundamentals.",
                "Good effort! Let's work on that preparation time.",
                "Nice try! Remember to watch the ball through contact.",
                "Keep working! Your improvement is showing.",
                "Good attempt! Focus on your footwork positioning."
            ],
            "timing_correction": [
                "Start your preparation a bit earlier.",
                "Perfect timing! You're really in sync with the ball.",
                "Great rhythm! That's the timing we want.",
                "Excellent anticipation! You're ready for every shot."
            ],
            "footwork_guidance": [
                "Great footwork! You're setting up perfectly.",
                "Excellent court positioning. Stay on your toes!",
                "Perfect movement! You're covering the court beautifully.",
                "Great balance! Your footwork is really solid."
            ],
            "session_start": [
                "Welcome to your tennis session! Let's work on your strokes today.",
                "Ready to play some tennis? Let's focus on technique and have fun!",
                "Great to see you on the court! Let's make every stroke count.",
                "Time for tennis! Let's work on building consistent, powerful strokes."
            ],
            "session_end": [
                "Excellent session! Your tennis is really improving.",
                "Great work today! You've made significant progress.",
                "Fantastic practice! Keep up that dedication and focus.",
                "Well done! Your stroke technique is looking much better."
            ]
        }
    
    async def provide_stroke_feedback(self, analysis_result: Dict[str, Any], 
                                    tone: CoachingTone = CoachingTone.ENCOURAGING) -> bool:
        """Provide voice feedback for tennis stroke analysis"""
        try:
            current_time = datetime.now().timestamp()
            
            # Check cooldown to avoid too frequent feedback
            if current_time - self.last_feedback_time < self.feedback_cooldown:
                return False
            
            # Extract stroke information
            stroke_type = analysis_result.get("stroke_type", "unknown")
            metrics = analysis_result.get("metrics", {})
            overall_score = metrics.get("overall_score", 0)
            
            # Generate appropriate feedback
            feedback_text = self._generate_stroke_feedback(stroke_type, metrics, overall_score)
            
            if feedback_text:
                # Provide voice feedback
                await self.voice_service.speak_coaching_cue(feedback_text, tone)
                self.last_feedback_time = current_time
                return True
            
            return False
            
        except Exception as e:
            print(f"Voice feedback error: {e}")
            return False
    
    def _generate_stroke_feedback(self, stroke_type: str, metrics: Dict[str, Any], 
                                overall_score: float) -> str:
        """Generate appropriate feedback text based on stroke analysis"""
        
        # Determine feedback category based on performance
        if overall_score >= 85:
            category = "general_encouragement"
        elif overall_score >= 70:
            category = self._get_specific_feedback_category(stroke_type, metrics)
        else:
            category = "improvement_needed"
        
        # Get phrases for the category
        phrases = self.coaching_phrases.get(category, self.coaching_phrases["general_encouragement"])
        
        # Return random phrase from category
        return random.choice(phrases)
    
    def _get_specific_feedback_category(self, stroke_type: str, metrics: Dict[str, Any]) -> str:
        """Get specific feedback category based on stroke type and weak areas"""
        
        power_score = metrics.get("power_score", 0)
        accuracy_score = metrics.get("accuracy_score", 0)
        timing_score = metrics.get("timing_score", 0)
        
        # Identify the area that needs most improvement
        scores = {
            "power": power_score,
            "accuracy": accuracy_score, 
            "timing": timing_score
        }
        
        lowest_area = min(scores.items(), key=lambda x: x[1])[0]
        
        # Map stroke type and weak area to feedback category
        feedback_map = {
            "serve": {
                "power": "serve_power",
                "accuracy": "serve_accuracy",
                "timing": "serve_preparation"
            },
            "forehand": {
                "power": "forehand_power",
                "accuracy": "forehand_technique",
                "timing": "timing_correction"
            },
            "backhand": {
                "power": "backhand_technique",
                "accuracy": "backhand_technique", 
                "timing": "timing_correction"
            },
            "volley": {
                "power": "volley_technique",
                "accuracy": "volley_technique",
                "timing": "volley_technique"
            }
        }
        
        stroke_feedback = feedback_map.get(stroke_type, {})
        return stroke_feedback.get(lowest_area, "general_encouragement")
    
    async def provide_session_feedback(self, session_summary: Dict[str, Any]) -> bool:
        """Provide voice feedback for completed tennis session"""
        try:
            # Generate session summary speech
            feedback_text = self._generate_session_summary(session_summary)
            
            if feedback_text:
                await self.voice_service.speak_coaching_cue(
                    feedback_text, CoachingTone.ENCOURAGING
                )
                return True
            
            return False
            
        except Exception as e:
            print(f"Session feedback error: {e}")
            return False
    
    def _generate_session_summary(self, session_summary: Dict[str, Any]) -> str:
        """Generate session summary feedback"""
        strokes_analyzed = session_summary.get("strokes_analyzed", 0)
        average_scores = session_summary.get("average_scores", {})
        overall_avg = average_scores.get("overall", 0)
        
        # Base feedback
        base_phrases = self.coaching_phrases["session_end"]
        base_feedback = random.choice(base_phrases)
        
        # Add specific performance feedback
        if overall_avg >= 80:
            performance_feedback = " Your stroke technique was excellent today!"
        elif overall_avg >= 65:
            performance_feedback = " You showed good consistency in your strokes."
        else:
            performance_feedback = " Keep practicing those fundamentals!"
        
        # Add stroke count feedback
        if strokes_analyzed >= 20:
            volume_feedback = f" You analyzed {strokes_analyzed} strokes - great practice volume!"
        elif strokes_analyzed >= 10:
            volume_feedback = f" Good practice with {strokes_analyzed} strokes analyzed."
        else:
            volume_feedback = " Try to practice more strokes in your next session."
        
        return base_feedback + performance_feedback + volume_feedback
    
    async def provide_technique_tip(self, stroke_type: str, tip_category: str = "general") -> bool:
        """Provide specific technique tip for stroke type"""
        try:
            # Map stroke type to tip category
            tip_categories = {
                "serve": ["serve_preparation", "serve_power", "serve_accuracy"],
                "forehand": ["forehand_technique", "forehand_power", "forehand_topspin"],
                "backhand": ["backhand_technique", "backhand_slice"],
                "volley": ["volley_technique"]
            }
            
            categories = tip_categories.get(stroke_type, ["general_encouragement"])
            
            if tip_category != "general" and tip_category in categories:
                category = tip_category
            else:
                category = random.choice(categories)
            
            phrases = self.coaching_phrases.get(category, self.coaching_phrases["general_encouragement"])
            tip_text = random.choice(phrases)
            
            await self.voice_service.speak_coaching_cue(tip_text, CoachingTone.INSTRUCTIONAL)
            return True
            
        except Exception as e:
            print(f"Technique tip error: {e}")
            return False
    
    async def announce_session_start(self) -> bool:
        """Announce the start of tennis training session"""
        try:
            phrases = self.coaching_phrases["session_start"]
            announcement = random.choice(phrases)
            
            await self.voice_service.speak_coaching_cue(announcement, CoachingTone.MOTIVATIONAL)
            return True
            
        except Exception as e:
            print(f"Session start announcement error: {e}")
            return False
    
    async def provide_drill_guidance(self, drill_name: str) -> bool:
        """Provide voice guidance for specific tennis drills"""
        try:
            drill_guidance = {
                "serve_practice": "Focus on your ball toss consistency and driving up through your legs. Take your time and find your rhythm.",
                "forehand_drill": "Remember to turn your shoulders early and make contact in front of your body. Low to high swing path for topspin.",
                "backhand_practice": "Prepare early with a shoulder turn. Keep your contact point in front and follow through across your body.",
                "volley_drill": "Stay in ready position with short preparation. Firm wrist through contact and step into the volley.",
                "movement_drill": "Keep your feet moving and stay on your toes. Good court positioning is key to setting up every shot."
            }
            
            guidance_text = drill_guidance.get(drill_name, 
                "Focus on good technique and consistency. Quality over quantity!")
            
            await self.voice_service.speak_coaching_cue(guidance_text, CoachingTone.INSTRUCTIONAL)
            return True
            
        except Exception as e:
            print(f"Drill guidance error: {e}")
            return False
    
    def set_feedback_cooldown(self, seconds: float):
        """Set the cooldown period between voice feedback"""
        self.feedback_cooldown = max(1.0, seconds)
    
    async def test_voice_system(self) -> bool:
        """Test the tennis voice coaching system"""
        try:
            test_phrases = [
                "Tennis voice coaching system is ready!",
                "Let's work on those tennis strokes today!",
                "Perfect! Your technique is looking great!"
            ]
            
            for phrase in test_phrases:
                await self.voice_service.speak_coaching_cue(phrase, CoachingTone.ENCOURAGING)
                await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"Voice system test error: {e}")
            return False

# Convenience functions for integration
async def provide_tennis_feedback(analysis_result: Dict[str, Any], 
                                tone: CoachingTone = CoachingTone.ENCOURAGING) -> bool:
    """Convenient function to provide tennis stroke feedback"""
    coach = TennisVoiceCoach()
    return await coach.provide_stroke_feedback(analysis_result, tone)

async def announce_tennis_session() -> bool:
    """Announce the start of a tennis session"""
    coach = TennisVoiceCoach()
    return await coach.announce_session_start()

if __name__ == "__main__":
    # Test the tennis voice coaching system
    async def test_tennis_voice():
        print("🎾 Testing Tennis Voice Coaching System...")
        
        coach = TennisVoiceCoach()
        
        # Test system initialization
        test_result = await coach.test_voice_system()
        if test_result:
            print("✅ Voice system test completed successfully!")
        
        # Test stroke feedback
        mock_analysis = {
            "stroke_type": "forehand",
            "metrics": {
                "overall_score": 78.5,
                "power_score": 85.0,
                "accuracy_score": 72.0,
                "timing_score": 80.0
            }
        }
        
        feedback_result = await coach.provide_stroke_feedback(mock_analysis)
        if feedback_result:
            print("✅ Stroke feedback provided successfully!")
        
        # Test session announcement
        announcement_result = await coach.announce_session_start()
        if announcement_result:
            print("✅ Session announcement completed!")
        
        print("🎾 Tennis voice coaching test completed!")
    
    # Run the test
    import asyncio
    asyncio.run(test_tennis_voice())