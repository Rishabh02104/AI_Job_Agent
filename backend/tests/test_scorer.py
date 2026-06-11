import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.scorer import ScorerAgent, calculate_cosine_similarity
from config import settings

def test_cosine_similarity():
    print("Testing cosine similarity helper...")
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    score = calculate_cosine_similarity(v1, v2)
    assert abs(score - 1.0) < 1e-5, f"Expected ~1.0, got {score}"

    v3 = [-1.0, -2.0, -3.0]
    score_neg = calculate_cosine_similarity(v1, v3)
    assert abs(score_neg - (-1.0)) < 1e-5, f"Expected ~-1.0, got {score_neg}"
    print("Cosine similarity test passed!")

def test_scorer_agent():
    print("Testing Scorer Agent...")
    if not settings.groq_api_key or settings.groq_api_key == "gsk_placeholder":
        print("Skipping Scorer Agent database integration test (no Groq key).")
        return
        
    scorer = ScorerAgent()
    result = scorer.run({"limit": 1})
    print(f"Scorer run success: {result.success}")
    if not result.success:
        print(f"Scorer failed with error: {result.error}")
    else:
        print(f"Scorer completed. Data: {result.data}")

if __name__ == "__main__":
    test_cosine_similarity()
    try:
        test_scorer_agent()
    except Exception as e:
        print(f"Scorer agent test failed: {e}")
