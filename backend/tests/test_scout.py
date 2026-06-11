import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.scout import ScoutAgent

def test_scout():
    print("Running Scout Agent Test...")
    scout = ScoutAgent()
    
    # Run scout query
    result = scout.run({"keywords": "software engineering", "limit": 3})
    
    print(f"Scout success: {result.success}")
    if result.success:
        print(f"Scout completed. Data: {result.data}")
    else:
        print(f"Scout error: {result.error}")
        
    assert result.success is True, f"Scout failed: {result.error}"
    print("Scout Agent Test Completed Successfully!")

if __name__ == "__main__":
    test_scout()
