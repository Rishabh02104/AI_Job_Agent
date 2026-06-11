import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.parser import get_embedding, parse_resume_json
from config import settings

def test_embedding():
    print("Testing local sentence-transformers embedding...")
    text = "Experienced AI Engineer with specialization in FastAPI and Next.js."
    vector = get_embedding(text)
    
    print(f"Embedding vector dimension: {len(vector)}")
    assert len(vector) == 384, f"Expected 384 dimensions, got {len(vector)}"
    assert all(isinstance(x, float) for x in vector), "All elements must be floats"
    print("Local embedding test passed!")

def test_llm_parsing():
    print("Testing resume parsing using Groq Llama-3.3-70b...")
    
    # Check if Groq API key is available
    if not settings.groq_api_key or settings.groq_api_key == "gsk_placeholder":
        print("Skipping Groq parsing test (GROQ_API_KEY is placeholder).")
        return

    sample_resume_text = """
    Rishabh Sharma
    risha@example.com
    Skills: Python, FastAPI, TypeScript, React, PostgreSQL
    
    Education:
    Bachelor of Technology in Computer Science, IIT Bombay, 2022
    
    Experience:
    Software Engineer, Tech Corp (2022 - Present)
    - Developed backend services using FastAPI and PostgreSQL
    - Built frontend dashboards using React
    
    Projects:
    Resume Tailorer
    - Created an AI tool to automatically rewrite resumes using GPT-4
    - Technologies: Python, LangChain, React
    """
    
    parsed_json = parse_resume_json(sample_resume_text)
    print(f"Parsed JSON:\n{parsed_json}")
    
    assert "skills" in parsed_json, "Parsed JSON missing skills"
    assert "education" in parsed_json, "Parsed JSON missing education"
    assert "projects" in parsed_json, "Parsed JSON missing projects"
    assert "experience" in parsed_json, "Parsed JSON missing experience"
    
    print("Groq parsing test passed!")

if __name__ == "__main__":
    test_embedding()
    try:
        test_llm_parsing()
    except Exception as e:
        print(f"Groq parsing test failed: {e}")
