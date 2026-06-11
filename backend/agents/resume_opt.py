import os
import json
import re
from typing import Dict, Any
from agents.base import BaseAgent, AgentResult
from db import supabase
from config import settings
from groq import Groq

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def extract_profile_from_text(raw_text: str) -> dict:
    """
    Extracts name, email, and phone from raw resume text using heuristics.
    """
    profile = {"name": "Candidate", "email": "", "phone": ""}
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    if lines:
        # First non-empty line is assumed to be the candidate name
        profile["name"] = lines[0]
        
    # Regex search for email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    if email_match:
        profile["email"] = email_match.group(0)
        
    # Regex search for phone number (placing hyphen at the end to prevent range error)
    phone_match = re.search(r'\+?\d[\d\s\(\)-]{8,15}\d', raw_text)
    if phone_match:
        profile["phone"] = phone_match.group(0)
        
    return profile

def generate_resume_pdf(resume_data: dict, output_path: str):
    """
    Generates a professionally styled resume PDF.
    """
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        rightMargin=40, 
        leftMargin=40, 
        topMargin=40, 
        bottomMargin=40
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        alignment=1, # Centered
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        alignment=1, # Centered
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        spaceAfter=4
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        fontName='Helvetica-Bold',
        spaceAfter=2
    )

    # Header Name & Contact Info
    story.append(Paragraph(resume_data.get("name", "Candidate"), title_style))
    contact = f"{resume_data.get('email', '')} | {resume_data.get('phone', '')}"
    story.append(Paragraph(contact.strip(" |"), subtitle_style))
    
    # Skills Section
    story.append(Paragraph("TECHNICAL SKILLS", heading_style))
    skills_text = ", ".join(resume_data.get("skills", []))
    story.append(Paragraph(skills_text, body_style))
    story.append(Spacer(1, 8))
    
    # Experience Section
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", heading_style))
    for exp in resume_data.get("experience", []):
        exp_header = f"<b>{exp.get('role')}</b> — {exp.get('company')} ({exp.get('duration')})"
        story.append(Paragraph(exp_header, bold_body_style))
        desc = exp.get("description", "")
        if isinstance(desc, str):
            bullets = [b.strip() for b in desc.split("\n") if b.strip()]
            for b in bullets:
                clean_b = b.lstrip("-*• ").strip()
                story.append(Paragraph(f"• {clean_b}", body_style))
        story.append(Spacer(1, 6))
        
    # Projects Section
    story.append(Paragraph("PROJECTS", heading_style))
    for proj in resume_data.get("projects", []):
        techs = ", ".join(proj.get("technologies", []))
        proj_header = f"<b>{proj.get('name')}</b> ({techs})"
        story.append(Paragraph(proj_header, bold_body_style))
        desc = proj.get("description", "")
        if isinstance(desc, str):
            bullets = [b.strip() for b in desc.split("\n") if b.strip()]
            for b in bullets:
                clean_b = b.lstrip("-*• ").strip()
                story.append(Paragraph(f"• {clean_b}", body_style))
        story.append(Spacer(1, 6))
        
    # Education Section
    story.append(Paragraph("EDUCATION", heading_style))
    for edu in resume_data.get("education", []):
        edu_text = f"<b>{edu.get('degree')}</b> — {edu.get('institution')} ({edu.get('year')})"
        story.append(Paragraph(edu_text, body_style))
        story.append(Spacer(1, 4))
        
    doc.build(story)

class ResumeOptimizerAgent(BaseAgent):
    """
    Agent 3: Resume Optimizer
    Customizes the user's base resume (JSON) for a target job description.
    Uses Groq Llama-3.3-70b to optimize skills ordering and edit experience bullets.
    Outputs a tailored JSON structure and renders a corresponding styled PDF document.
    """
    def run(self, input_data: dict) -> AgentResult:
        job_id = input_data.get("job_id")
        if not job_id:
            return AgentResult(success=False, error="Job ID must be provided in inputs.")

        # 1. Fetch the target job
        job_res = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if not job_res.data:
            return AgentResult(success=False, error=f"Job not found for ID: {job_id}")
        job = job_res.data[0]
        job_desc = job.get("description", "")

        # 2. Fetch the latest resume
        resume_res = supabase.table("resumes").select("*").order("uploaded_at", desc=True).limit(1).execute()
        if not resume_res.data:
            return AgentResult(success=False, error="Base resume not found in database.")
        resume = resume_res.data[0]
        resume_json = resume.get("parsed_json", {})
        raw_text = resume.get("raw_text", "")

        # Extract profile headers
        profile = extract_profile_from_text(raw_text)

        # 3. Call Groq to optimize the resume details
        try:
            client = Groq(api_key=settings.groq_api_key)
            optimized_json = self._optimize_resume_with_groq(client, resume_json, job_desc)
            
            # Merge candidate contact details
            optimized_json["name"] = profile["name"]
            optimized_json["email"] = profile["email"]
            optimized_json["phone"] = profile["phone"]

            # 4. Generate local PDF path
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
            os.makedirs(output_dir, exist_ok=True)
            pdf_filename = f"tailored_resume_{job_id}.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            generate_resume_pdf(optimized_json, pdf_path)

            # In Supabase production, we would upload to storage. For our V1 command line test, 
            # we will return the local file URL path.
            file_url = f"file:///{pdf_path.replace(os.sep, '/')}"

            return AgentResult(
                success=True,
                data={
                    "tailored_resume_json": optimized_json,
                    "tailored_resume_url": file_url
                }
            )

        except Exception as e:
            return AgentResult(success=False, error=f"Resume optimization failed: {str(e)}")

    def _optimize_resume_with_groq(self, client: Groq, resume_json: dict, job_desc: str) -> dict:
        prompt = f"""You are an expert technical resume writer. Your task is to customize the applicant's resume JSON to align with the target job description.
Align the skills, experience bullet points, and project descriptions. Ensure you use keywords from the job description naturally, reorder projects/skills to put the most relevant ones first, but do not fabricate any credentials or experience.

Base Resume JSON:
{json.dumps(resume_json, indent=2)}

Target Job Description:
{job_desc}

Output a valid JSON object matching the input schema exactly:
{{
  "skills": ["list of updated/reordered skills"],
  "education": [
    {{
      "institution": "university name",
      "degree": "degree details",
      "year": "years of attendance"
    }}
  ],
  "projects": [
    {{
      "name": "project title",
      "description": "updated description highlighting matching requirements",
      "technologies": ["tech used"]
    }}
  ],
  "experience": [
    {{
      "company": "company name",
      "role": "role title",
      "duration": "duration text",
      "description": "updated experience bullet points or summaries highlighting relevance"
    }}
  ]
}}
"""
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        return json.loads(content)
