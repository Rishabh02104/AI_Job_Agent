import json
from agents.base import BaseAgent, AgentResult
from db import supabase
from config import settings
from groq import Groq
from agents.resume_opt import extract_profile_from_text

class CoverLetterAgent(BaseAgent):
    """
    Agent 4: Cover Letter Agent
    Generates a tailored, 3-paragraph cover letter based on company details, job description, and applicant resume.
    Uses Groq Llama-3.3-70b.
    """
    def run(self, input_data: dict) -> AgentResult:
        job_id = input_data.get("job_id")
        if not job_id:
            return AgentResult(success=False, error="Job ID must be provided in inputs.")

        # 1. Fetch job details
        job_res = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if not job_res.data:
            return AgentResult(success=False, error=f"Job not found for ID: {job_id}")
        job = job_res.data[0]
        
        # 2. Fetch base resume
        resume_res = supabase.table("resumes").select("*").order("uploaded_at", desc=True).limit(1).execute()
        if not resume_res.data:
            return AgentResult(success=False, error="Base resume not found in database.")
        resume = resume_res.data[0]
        
        resume_json = resume.get("parsed_json", {})
        raw_text = resume.get("raw_text", "")
        profile = extract_profile_from_text(raw_text)
        candidate_name = profile.get("name", "Candidate")

        # 3. Call Groq to generate the cover letter
        try:
            client = Groq(api_key=settings.groq_api_key)
            cover_letter_text = self._generate_cover_letter_with_groq(
                client=client,
                candidate_name=candidate_name,
                company=job.get("company", ""),
                title=job.get("title", ""),
                job_desc=job.get("description", ""),
                resume_json=resume_json
            )
            
            return AgentResult(
                success=True,
                data={
                    "cover_letter": cover_letter_text
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=f"Cover letter generation failed: {str(e)}")

    def _generate_cover_letter_with_groq(
        self, client: Groq, candidate_name: str, company: str, title: str, job_desc: str, resume_json: dict
    ) -> str:
        prompt = f"""You are an expert executive cover letter writer. Write a tailored 3-paragraph cover letter for the following job and applicant details.
Make it professional, engaging, and highly specific. Do not include placeholders like '[Insert Date]' or '[Name]'. Use the candidate's actual name '{candidate_name}' for context, but do not write in the third person.

CRITICAL: The cover letter MUST be written in the first person (using "I", "my", "me"). Do NOT refer to the applicant in the third person (e.g., do NOT use "{candidate_name}", "He", "She", "Him", "Her", or "The candidate" in the body text).

Company Name: {company}
Role Title: {title}
Job Description:
{job_desc}

Applicant Resume Details (JSON):
{json.dumps(resume_json, indent=2)}

Format your output as a clean text containing exactly three paragraphs. Do not add salutation headers (like 'Dear Hiring Manager') or closing sign-offs (like 'Sincerely, Candidate') - only generate the three body paragraphs.
"""
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.2
        )
        
        return chat_completion.choices[0].message.content.strip()
