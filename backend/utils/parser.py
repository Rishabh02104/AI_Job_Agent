import os
import json
import pdfplumber
import docx
from sentence_transformers import SentenceTransformer
from groq import Groq
from config import settings

# Initialize SentenceTransformer locally (all-MiniLM-L6-v2 generates 384-d vectors)
# This model is lightweight (~90MB) and fast.
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # Avoid loading model on module import, load lazily on first call
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts plain text from PDF or DOCX files.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return "\n".join(text).strip()

def get_embedding(text: str) -> list:
    """
    Generates a 384-dimensional vector embedding for the input text.
    """
    model = get_embedding_model()
    # Ensure text is not empty
    if not text.strip():
        text = "empty description"
    embedding = model.encode(text)
    return embedding.tolist()

def parse_resume_json(raw_text: str) -> dict:
    """
    Uses Groq Llama-3.3-70b to parse raw resume text into structured JSON.
    """
    if not settings.groq_api_key or settings.groq_api_key == "gsk_placeholder":
        raise ValueError("Groq API key is not configured. Please set GROQ_API_KEY in .env.")

    client = Groq(api_key=settings.groq_api_key)
    
    prompt = f"""You are an expert resume parser. Analyze the following resume text and extract the details into a valid JSON object.
Do not include any commentary, markdown wrapping, or extra text. Output ONLY the raw JSON.

Schema:
{{
  "skills": ["list of skills as strings"],
  "education": [
    {{
      "institution": "university/college name",
      "degree": "degree obtained",
      "year": "graduation year or range"
    }}
  ],
  "projects": [
    {{
      "name": "project title",
      "description": "description of the project",
      "technologies": ["list of technologies used"]
    }}
  ],
  "experience": [
    {{
      "company": "company name",
      "role": "job title",
      "duration": "duration of employment",
      "description": "responsibilities and achievements"
    }}
  ]
}}

Resume Text:
{raw_text}
"""
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    content = chat_completion.choices[0].message.content
    return json.loads(content)
