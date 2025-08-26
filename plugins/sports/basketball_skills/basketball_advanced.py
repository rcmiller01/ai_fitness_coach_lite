"""
Basketball Dribbling and Defensive Stance Analysis

Advanced analysis for basketball dribbling techniques and defensive positioning.
Provides detailed feedback on ball control, stance, and movement efficiency.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

class DribblingStyle(Enum):
    """Types of dribbling styles"""
    STATIONARY = "stationary"
    CROSSOVER = "crossover"
    BETWEEN_LEGS = "between_legs"
    BEHIND_BACK = "behind_back"
    SPEED_DRIBBLE = "speed_dribble"
    HESITATION = "hesitation"

class DefenseType(Enum):
    """Types of defensive stances"""
    ON_BALL = "on_ball"
    HELP_DEFENSE = "help_defense"
    POST_DEFENSE = "post_defense"
    DENIAL = "denial"
    CLOSEOUT = "closeout"

@dataclass
class DribblingMetrics:
    """Detailed dribbling analysis metrics"""
    dribbling_style: DribblingStyle
    ball_height: float  # cm from ground
    dribble_frequency: float  # dribbles per second
    hand_control_score: float  # 0-100
    body_posture_score: float  # 0-100
    head_position_score: float  # 0-100
    crossover_efficiency: float  # 0-100
    ball_protection: float  # 0-100
    movement_fluidity: float  # 0-100
    overall_score: float  # 0-100
    timestamp: str

@dataclass
class DefensiveMetrics:
    """Detailed defensive stance analysis metrics"""
    defense_type: DefenseType
    stance_width: float  # cm between feet
    knee_bend_angle: float  # degrees
    back_angle: float  # degrees from vertical
    hand_activity_score: float  # 0-100
    balance_score: float  # 0-100
    reaction_readiness: float  # 0-100
    lateral_movement_score: float  # 0-100
    court_vision_score: float  # 0-100
    overall_score: float  # 0-100
    timestamp: str

class AdvancedDribblingAnalyzer:
    """Advanced basketball dribbling analysis system"""
    
    def __init__(self):
        self.initialized = False
        self.dribbling_patterns = {}
        
    def initialize(self):
        """Initialize dribbling analysis models"""
        self.dribbling_patterns = {
            DribblingStyle.STATIONARY: {
                "optimal_height": 45,  # cm
                "optimal_frequency": 1.5,  # dribbles/sec
                "key_indicators": ["consistent_height", "fingertip_control"]
            },
            DribblingStyle.CROSSOVER: {
                "optimal_height": 35,
                "optimal_frequency": 2.0,
                "key_indicators": ["quick_hand_switch", "body_protection"]
            },
            DribblingStyle.SPEED_DRIBBLE: {
                "optimal_height": 25,
                "optimal_frequency": 3.0,
                "key_indicators": ["low_dribble", "forward_momentum"]
            }
        }
        self.initialized = True
    
    def analyze_dribbling_technique(self, keypoints, movement_history: List[Dict]) -> DribblingMetrics:
        """Comprehensive dribbling technique analysis"""
        
        # Detect dribbling style
        dribbling_style = self._detect_dribbling_style(keypoints, movement_history)
        
        # Calculate ball control metrics
        ball_height = self._calculate_ball_height(keypoints)
        dribble_frequency = self._calculate_dribble_frequency(movement_history)
        
        # Analyze hand control
        hand_control_score = self._analyze_hand_control(keypoints)
        
        # Analyze body posture
        body_posture_score = self._analyze_dribbling_posture(keypoints)
        
        # Analyze head position
        head_position_score = self._analyze_head_position(keypoints)
        
        # Crossover analysis (if applicable)
        crossover_efficiency = self._analyze_crossover_efficiency(keypoints, dribbling_style)
        
        # Ball protection analysis
        ball_protection = self._analyze_ball_protection(keypoints)
        
        # Movement fluidity
        movement_fluidity = self._analyze_movement_fluidity(movement_history)
        
        # Calculate overall score
        overall_score = self._calculate_dribbling_overall_score(
            hand_control_score, body_posture_score, head_position_score,
            crossover_efficiency, ball_protection, movement_fluidity
        )
        
        return DribblingMetrics(
            dribbling_style=dribbling_style,
            ball_height=ball_height,
            dribble_frequency=dribble_frequency,
            hand_control_score=hand_control_score,
            body_posture_score=body_posture_score,
            head_position_score=head_position_score,
            crossover_efficiency=crossover_efficiency,
            ball_protection=ball_protection,
            movement_fluidity=movement_fluidity,
            overall_score=overall_score,
            timestamp=datetime.now().isoformat()
        )
    
    def _detect_dribbling_style(self, keypoints, movement_history: List[Dict]) -> DribblingStyle:
        """Detect the type of dribbling being performed"""
        # Analyze hand movement patterns
        left_wrist_x = keypoints.left_wrist[0] if keypoints.left_wrist else 0
        right_wrist_x = keypoints.right_wrist[0] if keypoints.right_wrist else 0
        
        # Simple heuristic for crossover detection
        hand_distance = abs(left_wrist_x - right_wrist_x)
        if hand_distance > 100:  # Hands are far apart
            return DribblingStyle.CROSSOVER
        
        # Check for speed dribble (low position)
        right_wrist_y = keypoints.right_wrist[1] if keypoints.right_wrist else 0
        right_hip_y = keypoints.right_hip[1] if keypoints.right_hip else 0
        
        if right_wrist_y > right_hip_y + 50:  # Hand is low
            return DribblingStyle.SPEED_DRIBBLE
        
        return DribblingStyle.STATIONARY
    
    def _calculate_ball_height(self, keypoints) -> float:
        """Calculate estimated ball height from hand position"""
        # Mock calculation based on hand position
        right_wrist_y = keypoints.right_wrist[1] if keypoints.right_wrist else 0
        right_hip_y = keypoints.right_hip[1] if keypoints.right_hip else 0
        
        # Estimate ball height (mock)
        height_diff = abs(right_wrist_y - right_hip_y)
        estimated_height = 45.0 + (height_diff / 10)  # Convert pixels to cm estimate
        
        return min(70, max(20, estimated_height))  # Clamp to realistic range
    
    def _calculate_dribble_frequency(self, movement_history: List[Dict]) -> float:
        """Calculate dribbling frequency from movement history"""
        # Mock calculation - in real implementation, analyze hand movement patterns
        return 2.2 + np.random.normal(0, 0.3)
    
    def _analyze_hand_control(self, keypoints) -> float:
        """Analyze hand control and fingertip usage"""
        # Mock analysis based on hand positioning
        base_score = 80.0
        
        # Check hand stability (mock)
        stability_bonus = np.random.normal(0, 10)
        
        return min(100, max(0, base_score + stability_bonus))
    
    def _analyze_dribbling_posture(self, keypoints) -> float:
        """Analyze body posture during dribbling"""
        # Check knee bend
        left_knee_y = keypoints.left_knee[1] if keypoints.left_knee else 0
        left_hip_y = keypoints.left_hip[1] if keypoints.left_hip else 0
        
        knee_bend_score = 85.0
        if left_knee_y > left_hip_y:  # Knees bent properly
            knee_bend_score += 10
        
        posture_score = knee_bend_score + np.random.normal(0, 8)
        return min(100, max(0, posture_score))
    
    def _analyze_head_position(self, keypoints) -> float:
        """Analyze head position (should be up for court vision)"""
        # Mock analysis - head should be up for good court vision
        base_score = 75.0
        head_position_bonus = np.random.normal(0, 12)
        
        return min(100, max(0, base_score + head_position_bonus))
    
    def _analyze_crossover_efficiency(self, keypoints, dribbling_style: DribblingStyle) -> float:
        """Analyze crossover dribble efficiency"""
        if dribbling_style != DribblingStyle.CROSSOVER:
            return 0.0
        
        # Mock crossover analysis
        efficiency = 78.0 + np.random.normal(0, 15)
        return min(100, max(0, efficiency))
    
    def _analyze_ball_protection(self, keypoints) -> float:
        """Analyze how well the ball is protected"""
        # Mock analysis based on body positioning
        protection_score = 82.0 + np.random.normal(0, 10)
        return min(100, max(0, protection_score))
    
    def _analyze_movement_fluidity(self, movement_history: List[Dict]) -> float:
        """Analyze fluidity of movement"""
        # Mock fluidity analysis
        fluidity_score = 79.0 + np.random.normal(0, 12)
        return min(100, max(0, fluidity_score))
    
    def _calculate_dribbling_overall_score(self, hand_control: float, posture: float, 
                                         head_position: float, crossover: float,
                                         protection: float, fluidity: float) -> float:
        """Calculate overall dribbling score"""
        # Weight different aspects
        weights = {
            'hand_control': 0.25,
            'posture': 0.20,
            'head_position': 0.15,
            'protection': 0.20,
            'fluidity': 0.20
        }
        
        overall = (hand_control * weights['hand_control'] +
                  posture * weights['posture'] +
                  head_position * weights['head_position'] +
                  protection * weights['protection'] +
                  fluidity * weights['fluidity'])
        
        # Add crossover bonus if applicable
        if crossover > 0:
            overall = (overall * 0.9) + (crossover * 0.1)
        
        return round(overall, 1)

class AdvancedDefenseAnalyzer:
    """Advanced basketball defensive stance analysis system"""
    
    def __init__(self):
        self.initialized = False
        self.defense_standards = {}
    
    def initialize(self):
        """Initialize defensive analysis models"""
        self.defense_standards = {
            DefenseType.ON_BALL: {
                "optimal_stance_width": 65,  # cm
                "optimal_knee_angle": 110,   # degrees
                "key_indicators": ["low_stance", "active_hands", "balance"]
            },
            DefenseType.HELP_DEFENSE: {
                "optimal_stance_width": 60,
                "optimal_knee_angle": 120,
                "key_indicators": ["court_vision", "ready_position"]
            }
        }
        self.initialized = True
    
    def analyze_defensive_stance(self, keypoints, context: Dict = None) -> DefensiveMetrics:
        """Comprehensive defensive stance analysis"""
        
        # Detect defense type
        defense_type = self._detect_defense_type(keypoints, context)
        
        # Calculate stance metrics
        stance_width = self._calculate_stance_width(keypoints)
        knee_bend_angle = self._calculate_knee_bend_angle(keypoints)
        back_angle = self._calculate_back_angle(keypoints)
        
        # Analyze defensive qualities
        hand_activity_score = self._analyze_hand_activity(keypoints)
        balance_score = self._analyze_defensive_balance(keypoints)
        reaction_readiness = self._analyze_reaction_readiness(keypoints)
        lateral_movement_score = self._analyze_lateral_movement_readiness(keypoints)
        court_vision_score = self._analyze_court_vision(keypoints)
        
        # Calculate overall score
        overall_score = self._calculate_defensive_overall_score(
            hand_activity_score, balance_score, reaction_readiness,
            lateral_movement_score, court_vision_score
        )
        
        return DefensiveMetrics(
            defense_type=defense_type,
            stance_width=stance_width,
            knee_bend_angle=knee_bend_angle,
            back_angle=back_angle,
            hand_activity_score=hand_activity_score,
            balance_score=balance_score,
            reaction_readiness=reaction_readiness,
            lateral_movement_score=lateral_movement_score,
            court_vision_score=court_vision_score,
            overall_score=overall_score,
            timestamp=datetime.now().isoformat()
        )
    
    def _detect_defense_type(self, keypoints, context: Dict = None) -> DefenseType:
        """Detect the type of defense being played"""
        # Simple detection based on stance
        left_ankle_x = keypoints.left_ankle[0] if keypoints.left_ankle else 0
        right_ankle_x = keypoints.right_ankle[0] if keypoints.right_ankle else 0
        
        stance_width = abs(left_ankle_x - right_ankle_x)
        
        if stance_width > 80:  # Wide stance indicates on-ball defense
            return DefenseType.ON_BALL
        else:
            return DefenseType.HELP_DEFENSE
    
    def _calculate_stance_width(self, keypoints) -> float:
        """Calculate defensive stance width"""
        left_ankle_x = keypoints.left_ankle[0] if keypoints.left_ankle else 0
        right_ankle_x = keypoints.right_ankle[0] if keypoints.right_ankle else 0
        
        # Convert pixel distance to cm estimate
        pixel_width = abs(left_ankle_x - right_ankle_x)
        estimated_width = pixel_width * 0.5  # Mock conversion factor
        
        return min(100, max(30, estimated_width))
    
    def _calculate_knee_bend_angle(self, keypoints) -> float:
        """Calculate knee bend angle"""
        # Mock calculation - in real implementation, use joint angle calculation
        base_angle = 110.0
        variation = np.random.normal(0, 15)
        
        return min(140, max(90, base_angle + variation))
    
    def _calculate_back_angle(self, keypoints) -> float:
        """Calculate back angle from vertical"""
        # Mock calculation
        base_angle = 10.0  # Slight forward lean is good
        variation = np.random.normal(0, 5)
        
        return max(0, base_angle + variation)
    
    def _analyze_hand_activity(self, keypoints) -> float:
        """Analyze hand activity and positioning"""
        # Check if hands are at appropriate height
        left_wrist_y = keypoints.left_wrist[1] if keypoints.left_wrist else 0
        right_wrist_y = keypoints.right_wrist[1] if keypoints.right_wrist else 0
        shoulder_y = keypoints.left_shoulder[1] if keypoints.left_shoulder else 0
        
        hand_activity = 80.0
        
        # Bonus for hands at shoulder level
        if abs(left_wrist_y - shoulder_y) < 50 and abs(right_wrist_y - shoulder_y) < 50:
            hand_activity += 10
        
        activity_score = hand_activity + np.random.normal(0, 8)
        return min(100, max(0, activity_score))
    
    def _analyze_defensive_balance(self, keypoints) -> float:
        """Analyze defensive balance"""
        # Mock balance analysis based on stance
        balance_score = 83.0 + np.random.normal(0, 10)
        return min(100, max(0, balance_score))
    
    def _analyze_reaction_readiness(self, keypoints) -> float:
        """Analyze readiness to react"""
        # Check if player is on balls of feet (mock)
        readiness_score = 78.0 + np.random.normal(0, 12)
        return min(100, max(0, readiness_score))
    
    def _analyze_lateral_movement_readiness(self, keypoints) -> float:
        """Analyze readiness for lateral movement"""
        # Mock lateral movement analysis
        movement_score = 81.0 + np.random.normal(0, 10)
        return min(100, max(0, movement_score))
    
    def _analyze_court_vision(self, keypoints) -> float:
        """Analyze court vision (head position)"""
        # Head should be up for good court vision
        vision_score = 76.0 + np.random.normal(0, 12)
        return min(100, max(0, vision_score))
    
    def _calculate_defensive_overall_score(self, hand_activity: float, balance: float,
                                         reaction_readiness: float, lateral_movement: float,
                                         court_vision: float) -> float:
        """Calculate overall defensive score"""
        weights = {
            'hand_activity': 0.20,
            'balance': 0.25,
            'reaction_readiness': 0.20,
            'lateral_movement': 0.20,
            'court_vision': 0.15
        }
        
        overall = (hand_activity * weights['hand_activity'] +
                  balance * weights['balance'] +
                  reaction_readiness * weights['reaction_readiness'] +
                  lateral_movement * weights['lateral_movement'] +
                  court_vision * weights['court_vision'])
        
        return round(overall, 1)

class BasketballMovementCoach:
    """Coaching system for dribbling and defense"""
    
    def __init__(self):
        self.coaching_tips = {}
    
    def initialize(self):
        """Initialize coaching tips database"""
        self.coaching_tips = {
            "dribbling": {
                "ball_control": [
                    "Keep the ball low and use fingertips for better control",
                    "Dribble with purpose - every dribble should have a reason",
                    "Practice dribbling without looking at the ball"
                ],
                "posture": [
                    "Stay in athletic stance with knees bent",
                    "Keep your head up to see the court",
                    "Protect the ball with your body and off-arm"
                ],
                "technique": [
                    "Use your fingertips, not your palm",
                    "Keep dribbles below waist level",
                    "Practice equally with both hands"
                ]
            },
            "defense": {
                "stance": [
                    "Keep feet wider than shoulder-width apart",
                    "Bend your knees and stay low",
                    "Keep your back straight and head up"
                ],
                "positioning": [
                    "Stay between your opponent and the basket",
                    "Keep active hands at shoulder height",
                    "Stay on the balls of your feet for quick movement"
                ],
                "movement": [
                    "Use lateral shuffle steps, don't cross your feet",
                    "Maintain proper distance - close enough to contest, far enough to react",
                    "Keep your eyes on your opponent's midsection"
                ]
            }
        }
    
    def generate_dribbling_tips(self, metrics: DribblingMetrics) -> List[str]:
        """Generate dribbling improvement tips"""
        tips = []
        
        if metrics.ball_height > 60:
            tips.append("Keep your dribble lower for better ball control")
        
        if metrics.hand_control_score < 75:
            tips.extend(self.coaching_tips["dribbling"]["technique"][:1])
        
        if metrics.body_posture_score < 75:
            tips.extend(self.coaching_tips["dribbling"]["posture"][:1])
        
        if metrics.head_position_score < 70:
            tips.append("Keep your head up to see the court and teammates")
        
        if metrics.overall_score > 85:
            tips.append("Excellent dribbling! Work on game-speed scenarios")
        
        return tips[:4]  # Limit to 4 tips
    
    def generate_defense_tips(self, metrics: DefensiveMetrics) -> List[str]:
        """Generate defensive improvement tips"""
        tips = []
        
        if metrics.stance_width < 55:
            tips.append("Widen your stance for better lateral movement")
        
        if metrics.knee_bend_angle > 130:
            tips.append("Bend your knees more to lower your center of gravity")
        
        if metrics.hand_activity_score < 75:
            tips.extend(self.coaching_tips["defense"]["positioning"][:1])
        
        if metrics.reaction_readiness < 75:
            tips.append("Stay on the balls of your feet, ready to move")
        
        if metrics.overall_score > 85:
            tips.append("Great defensive stance! Practice movement drills")
        
        return tips[:4]  # Limit to 4 tips

# Test functions
def test_dribbling_analyzer():
    """Test the dribbling analyzer"""
    analyzer = AdvancedDribblingAnalyzer()
    analyzer.initialize()
    
    # Mock keypoints
    from collections import namedtuple
    Keypoints = namedtuple('Keypoints', ['left_wrist', 'right_wrist', 'left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle'])
    
    keypoints = Keypoints(
        left_wrist=(80, 200),
        right_wrist=(250, 180),
        left_hip=(120, 300),
        right_hip=(180, 300),
        left_knee=(110, 350),
        right_knee=(190, 350),
        left_ankle=(100, 400),
        right_ankle=(200, 400)
    )
    
    movement_history = [{"timestamp": "2024-01-01", "action": "dribble"}]
    
    metrics = analyzer.analyze_dribbling_technique(keypoints, movement_history)
    print(f"🏀 Dribbling Analysis:")
    print(f"   Style: {metrics.dribbling_style.value}")
    print(f"   Ball Height: {metrics.ball_height:.1f} cm")
    print(f"   Overall Score: {metrics.overall_score:.1f}")
    
    return metrics

def test_defense_analyzer():
    """Test the defense analyzer"""
    analyzer = AdvancedDefenseAnalyzer()
    analyzer.initialize()
    
    # Mock keypoints  
    from collections import namedtuple
    Keypoints = namedtuple('Keypoints', ['left_wrist', 'right_wrist', 'left_shoulder', 'left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle'])
    
    keypoints = Keypoints(
        left_wrist=(70, 180),
        right_wrist=(270, 180),
        left_shoulder=(100, 150),
        left_hip=(120, 300),
        right_hip=(180, 300),
        left_knee=(110, 350),
        right_knee=(190, 350),
        left_ankle=(90, 400),
        right_ankle=(210, 400)
    )
    
    metrics = analyzer.analyze_defensive_stance(keypoints)
    print(f"🛡️ Defense Analysis:")
    print(f"   Type: {metrics.defense_type.value}")
    print(f"   Stance Width: {metrics.stance_width:.1f} cm")
    print(f"   Overall Score: {metrics.overall_score:.1f}")
    
    return metrics

if __name__ == "__main__":
    print("🏀 Testing Advanced Basketball Analysis...")
    
    # Test dribbling analyzer
    dribbling_metrics = test_dribbling_analyzer()
    
    # Test defense analyzer  
    defense_metrics = test_defense_analyzer()
    
    # Test coaching system
    coach = BasketballMovementCoach()
    coach.initialize()
    
    dribbling_tips = coach.generate_dribbling_tips(dribbling_metrics)
    defense_tips = coach.generate_defense_tips(defense_metrics)
    
    print(f"\n🏀 Coaching Tips:")
    print(f"   Dribbling: {len(dribbling_tips)} tips")
    print(f"   Defense: {len(defense_tips)} tips")
    
    print("✅ Advanced basketball analysis test completed!")