import json
import math
import logging
from typing import Dict, Any
from agents.base import BaseAgent, AgentResult
from db import supabase
from config import settings
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def calculate_cosine_similarity(v1: list, v2: list) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    sum_a2 = sum(a * a for a in v1)
    sum_b2 = sum(b * b for b in v2)
    if not sum_a2 or not sum_b2:
        return 0.0
    return dot / (math.sqrt(sum_a2) * math.sqrt(sum_b2))

def parse_vector(vector_data) -> list:
    if isinstance(vector_data, str):
        cleaned = vector_data.strip("[] \n\r")
        if not cleaned:
            return []
        return [float(x) for x in cleaned.split(",")]
    elif isinstance(vector_data, list):
        return [float(x) for x in vector_data]
    return []

class ScorerAgent(BaseAgent):
    """
    Agent 2: Scorer
    Computes cosine similarity between the latest resume vector and all unscored jobs.
    Uses Groq (Llama-3.3-70b) to extract matched/missing skills and qualitative rationale.
    If final score is >= 80% (0.80), auto-creates an application record with status 'queued'.
    """
    def run(self, input_data: dict) -> AgentResult:
        # 1. Fetch the latest resume
        resume_res = supabase.table("resumes").select("*").order("uploaded_at", desc=True).limit(1).execute()
        if not resume_res.data:
            return AgentResult(success=False, error="No base resume found in database. Please upload one first.")
        
        resume = resume_res.data[0]
        resume_vector = parse_vector(resume.get("embedding"))
        resume_json = resume.get("parsed_json")
        
        if not resume_vector:
            return AgentResult(success=False, error="Resume does not contain vector embeddings.")

        # Fetch target score threshold from settings (fallback to 0.8)
        threshold = 0.8
        try:
            settings_res = supabase.table("system_settings").select("threshold").eq("id", "00000000-0000-0000-0000-000000000000").execute()
            if settings_res.data:
                threshold = settings_res.data[0].get("threshold", 0.8)
        except Exception as settings_err:
            logger.warning(f"Could not load custom threshold from settings: {settings_err}. Falling back to 0.8")

        # 2. Get all jobs that haven't been scored
        jobs_res = supabase.table("jobs").select("*").execute()
        if not jobs_res.data:
            return AgentResult(success=True, data={"scored_count": 0, "message": "No jobs in database to score."})

        matches_res = supabase.table("matches").select("job_id").execute()
        scored_job_ids = {m["job_id"] for m in matches_res.data}
        unscored_jobs = [j for j in jobs_res.data if j["id"] not in scored_job_ids]

        if not unscored_jobs:
            return AgentResult(success=True, data={"scored_count": 0, "message": "All jobs in database are already scored."})

        # Limit scoring iterations per run to prevent excessive API calls
        limit = input_data.get("limit", 5)
        jobs_to_score = unscored_jobs[:limit]

        scored_results = []
        errors = []

        client = Groq(api_key=settings.groq_api_key)

        for idx, job in enumerate(jobs_to_score):
            job_vector = parse_vector(job.get("embedding"))
            if not job_vector:
                errors.append(f"Job {job['id']} is missing embedding vector.")
                continue

            try:
                if idx > 0:
                    import time
                    time.sleep(4)
                # Calculate base similarity
                base_score = calculate_cosine_similarity(resume_vector, job_vector)
                
                try:
                    # Fetch Groq analysis
                    analysis = self._explain_match_with_groq(client, resume_json, job["description"], base_score)
                    adjustment = analysis.get("score_adjustment", 0.0)
                    # Keep adjustment within safe limits (-0.2 to +0.2)
                    adjustment = max(-0.2, min(0.2, adjustment))
                    final_score = max(0.0, min(1.0, base_score + adjustment))
                    matched_skills = analysis.get("matched_skills", [])
                    missing_skills = analysis.get("missing_skills", [])
                    explanation = analysis.get("explanation", "Match computed successfully.")
                except Exception as groq_err:
                    logger.warning(f"Groq match explanation failed for job {job['id']}: {groq_err}. Falling back to base similarity score.")
                    final_score = base_score
                    matched_skills = []
                    missing_skills = []
                    explanation = f"Match score based on semantic similarity. (Qualitative analysis skipped: {str(groq_err)})"

                # Insert score info into 'matches'
                supabase.table("matches").insert({
                    "job_id": job["id"],
                    "score": final_score,
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "explanation": explanation
                }).execute()

                # If score >= threshold, stage job application as 'queued'
                staged = False
                if final_score >= threshold:
                    # Check if application already exists
                    app_res = supabase.table("applications").select("id").eq("job_id", job["id"]).execute()
                    if not app_res.data:
                        supabase.table("applications").insert({
                            "job_id": job["id"],
                            "status": "queued"
                        }).execute()
                        staged = True

                scored_results.append({
                    "job_id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "score": final_score,
                    "staged_in_queue": staged
                })

            except Exception as e:
                errors.append(f"Failed to score job {job['id']}: {str(e)}")

        return AgentResult(
            success=True,
            data={
                "scored_count": len(scored_results),
                "scored_jobs": scored_results,
                "errors": errors
            }
        )

    def _explain_match_with_groq(self, client: Groq, resume_json: dict, job_desc: str, base_score: float) -> Dict[str, Any]:
        prompt = f"""You are an AI job match scoring assistant. Analyze the applicant's resume details and the target job description.
Your job is to identify matched skills, missing key requirements, and write a 1-paragraph summary justification.

Applicant Resume Details (JSON):
{json.dumps(resume_json, indent=2)}

Job Description:
{job_desc}

Calculated Base Cosine Similarity Score: {base_score:.2f}

Evaluate the fit carefully. You may recommend a score adjustment (value between -0.20 and +0.20) if the mathematical cosine similarity doesn't fully capture qualitative alignment (e.g. candidate has years of experience in the exact tech stack or lacks core prerequisites).

Output a valid JSON object with the following schema:
{{
  "score_adjustment": float,
  "matched_skills": ["list", "of", "strings"],
  "missing_skills": ["list", "of", "strings"],
  "explanation": "A one-paragraph summary of the match justification"
}}
"""
        import time
        retries = 3
        backoff = 20.0
        for i in range(retries):
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                content = chat_completion.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                err_msg = str(e)
                if i < retries - 1 and ("429" in err_msg or "rate limit" in err_msg.lower()):
                    wait_time = backoff * (2 ** i)
                    logger.warning(f"Groq Rate Limit in Scorer. Retrying in {wait_time}s... (Attempt {i+1}/{retries})")
                    time.sleep(wait_time)
                else:
                    raise e
