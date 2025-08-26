#!/usr/bin/env python3
"""Simple rep counter test"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from utils.rep_counter import create_rep_counter, ExerciseType
    from models.pose_estimator import create_pose_estimator
    import numpy as np
    
    def test_rep_counter():
        print("🏋️ Testing Rep Counter...")
        
        # Create rep counter
        counter = create_rep_counter("push_ups")
        print(f"✅ Created rep counter for {counter.exercise_type.value}")
        
        # Create pose estimator
        estimator = create_pose_estimator("placeholder")
        print("✅ Created pose estimator")
        
        # Simulate poses
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        print("Simulating push-up reps...")
        for i in range(10):
            pose = estimator.estimate_pose(test_frame)
            if pose:
                result = counter.process_pose(pose)
                print(f"Frame {i+1}: Phase={result['current_phase']}, Angle={result['primary_angle']:.1f}°")
                if result["rep_completed"]:
                    print(f"🎉 Rep {result['total_reps']} completed!")
        
        # Get session summary
        summary = counter.get_session_summary()
        print(f"\n📊 Session Summary:")
        print(f"   Exercise: {summary['exercise_type']}")
        print(f"   Total Reps: {summary['total_reps']}")
        print(f"   Average Confidence: {summary['average_confidence']:.2f}")
        print(f"   Session Duration: {summary['session_duration']:.1f}s")
        print(f"   Calibrated: {summary['is_calibrated']}")
        
        return True
        
    if test_rep_counter():
        print("✅ Rep counter test completed successfully!")
    else:
        print("❌ Rep counter test failed!")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Running from incorrect directory or missing dependencies")
except Exception as e:
    print(f"❌ Test error: {e}")