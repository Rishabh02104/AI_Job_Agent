import os
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from db import supabase
from config import settings
from utils.parser import extract_text_from_file, get_embedding, parse_resume_json
from orchestrator import Orchestrator
from utils.playwright_bot import submit_application_task


app = FastAPI(title="AI Job Agent API", version="1.0.0")

# Setup CORS middleware to allow Next.js frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory to serve generated resume PDFs
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize pipeline orchestrator
orchestrator = Orchestrator()

# Helper status list to check standard ENUM values
VALID_STATUSES = ['saved', 'queued', 'reviewing', 'applied', 'interview', 'rejected', 'offer']

# Models for request validation
class SystemSettingsUpdate(BaseModel):
    keywords: Optional[str] = None
    location: Optional[str] = None
    limit_count: Optional[int] = None
    threshold: Optional[float] = None
    internshala_email: Optional[str] = None
    internshala_password: Optional[str] = None
    gmail_email: Optional[str] = None
    gmail_app_password: Optional[str] = None
    schedule_interval_hours: Optional[int] = None
    is_schedule_enabled: Optional[bool] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    requires_sponsorship: Optional[bool] = None
    authorized_to_work: Optional[bool] = None
    notice_period_days: Optional[int] = None
    salary_expectations: Optional[str] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    disability_status: Optional[str] = None
    veteran_status: Optional[str] = None

class ApplicationStatusUpdate(BaseModel):
    status: str

class ApplicationEdit(BaseModel):
    cover_letter: str

# Endpoints
DEFAULT_SETTINGS_ID = "00000000-0000-0000-0000-000000000000"

@app.get("/api/settings")
def get_settings():
    try:
        res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
        if res.data:
            row = res.data[0]
            if "github_url" not in row:
                row["copilot_migration_pending"] = True
            return row
        # Seed it if missing
        default_row = {
            "id": DEFAULT_SETTINGS_ID,
            "keywords": "AI Engineer",
            "location": "",
            "limit_count": 5,
            "threshold": 0.8,
            "internshala_email": "",
            "internshala_password": "",
            "gmail_email": "",
            "gmail_app_password": "",
            "schedule_interval_hours": 12,
            "is_schedule_enabled": True,
            "github_url": "",
            "linkedin_url": "",
            "portfolio_url": "",
            "requires_sponsorship": False,
            "authorized_to_work": True,
            "notice_period_days": 0,
            "salary_expectations": "",
            "gender": "Decline to self-identify",
            "race": "Decline to self-identify",
            "disability_status": "Decline to self-identify",
            "veteran_status": "Decline to self-identify"
        }
        try:
            supabase.table("system_settings").insert(default_row).execute()
            return default_row
        except Exception as insert_err:
            insert_err_msg = str(insert_err)
            if "column" in insert_err_msg and "does not exist" in insert_err_msg:
                # Seed legacy columns only
                legacy_row = {
                    "id": DEFAULT_SETTINGS_ID,
                    "keywords": "AI Engineer",
                    "location": "",
                    "limit_count": 5,
                    "threshold": 0.8,
                    "internshala_email": "",
                    "internshala_password": "",
                    "gmail_email": "",
                    "gmail_app_password": "",
                    "schedule_interval_hours": 12,
                    "is_schedule_enabled": True
                }
                supabase.table("system_settings").insert(legacy_row).execute()
                legacy_row["copilot_migration_pending"] = True
                return legacy_row
            else:
                raise insert_err
    except Exception as e:
        err_msg = str(e)
        if "relation" in err_msg and "does not exist" in err_msg:
            return {
                "keywords": "AI Engineer",
                "location": "",
                "limit_count": 5,
                "threshold": 0.8,
                "internshala_email": "",
                "internshala_password": "",
                "gmail_email": "",
                "gmail_app_password": "",
                "schedule_interval_hours": 12,
                "is_schedule_enabled": True,
                "github_url": "",
                "linkedin_url": "",
                "portfolio_url": "",
                "requires_sponsorship": False,
                "authorized_to_work": True,
                "notice_period_days": 0,
                "salary_expectations": "",
                "gender": "Decline to self-identify",
                "race": "Decline to self-identify",
                "disability_status": "Decline to self-identify",
                "veteran_status": "Decline to self-identify",
                "migration_pending": True
            }
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/settings")
def update_settings(payload: SystemSettingsUpdate):
    try:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update.")
            
        res = supabase.table("system_settings").update(update_data).eq("id", DEFAULT_SETTINGS_ID).execute()
        if not res.data:
            default_row = {
                "id": DEFAULT_SETTINGS_ID,
                "keywords": "AI Engineer",
                "location": "",
                "limit_count": 5,
                "threshold": 0.8,
                "internshala_email": "",
                "internshala_password": "",
                "gmail_email": "",
                "gmail_app_password": "",
                "schedule_interval_hours": 12,
                "is_schedule_enabled": True,
                "github_url": "",
                "linkedin_url": "",
                "portfolio_url": "",
                "requires_sponsorship": False,
                "authorized_to_work": True,
                "notice_period_days": 0,
                "salary_expectations": "",
                "gender": "Decline to self-identify",
                "race": "Decline to self-identify",
                "disability_status": "Decline to self-identify",
                "veteran_status": "Decline to self-identify"
            }
            default_row.update(update_data)
            try:
                supabase.table("system_settings").insert(default_row).execute()
            except Exception as insert_err:
                insert_err_msg = str(insert_err)
                if "column" in insert_err_msg and "does not exist" in insert_err_msg:
                    legacy_keys = ["id", "keywords", "location", "limit_count", "threshold", "internshala_email", "internshala_password", "gmail_email", "gmail_app_password", "schedule_interval_hours", "is_schedule_enabled"]
                    legacy_insert_data = {k: v for k, v in default_row.items() if k in legacy_keys}
                    res_legacy = supabase.table("system_settings").insert(legacy_insert_data).execute()
                    row = res_legacy.data[0]
                    row["copilot_migration_pending"] = True
                    return row
                else:
                    raise insert_err
            return default_row
            
        row = res.data[0]
        if "github_url" not in row:
            row["copilot_migration_pending"] = True
        return row
    except Exception as e:
        err_msg = str(e)
        if "relation" in err_msg and "does not exist" in err_msg:
            raise HTTPException(
                status_code=400, 
                detail="The 'system_settings' table does not exist. Please run migrations first."
            )
        elif "column" in err_msg and "does not exist" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="The database schema is missing the new copilot columns. Please execute '20260611000200_add_copilot_fields.sql' migration in your Supabase SQL Editor."
            )
        raise HTTPException(status_code=500, detail=str(e))



# Endpoints

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "AI Job Agent FastAPI Server is running."}

@app.get("/api/stats")
def get_stats():
    """
    Computes dashboard metrics: jobs found today, applications active, and match distributions.
    """
    try:
        # Fetch applications
        apps_res = supabase.table("applications").select("status").execute()
        apps = apps_res.data or []
        
        # Count statuses
        counts = {status: 0 for status in VALID_STATUSES}
        for app in apps:
            status = app.get("status")
            if status in counts:
                counts[status] += 1

        # Match score distribution
        matches_res = supabase.table("matches").select("score").execute()
        scores = [m.get("score", 0.0) for m in (matches_res.data or [])]
        
        distribution = {
            "low": len([s for s in scores if s < 0.5]),
            "medium": len([s for s in scores if 0.5 <= s < 0.8]),
            "high": len([s for s in scores if s >= 0.8])
        }

        # Jobs found today
        jobs_res = supabase.table("jobs").select("id").execute()
        total_jobs = len(jobs_res.data or [])

        return {
            "jobs_found": total_jobs,
            "application_counts": counts,
            "match_distribution": distribution
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
def get_jobs(score_min: Optional[float] = None):
    """
    Fetches job listings with match scores.
    """
    try:
        query = supabase.table("jobs").select("*, matches(score, matched_skills, missing_skills, explanation)")
        res = query.execute()
        jobs = res.data or []
        
        # Flatten and filter by min score if provided
        formatted_jobs = []
        for j in jobs:
            match_data = j.get("matches", {})
            if isinstance(match_data, list) and match_data:
                # Handle single relation return structures
                match_data = match_data[0]
            
            score = match_data.get("score") if match_data else None
            
            if score_min is not None and (score is None or score < score_min):
                continue
                
            formatted_jobs.append({
                "id": j.get("id"),
                "title": j.get("title"),
                "company": j.get("company"),
                "description": j.get("description"),
                "location": j.get("location"),
                "source": j.get("source"),
                "url": j.get("url"),
                "scraped_at": j.get("scraped_at"),
                "match": {
                    "score": score,
                    "matched_skills": match_data.get("matched_skills", []) if match_data else [],
                    "missing_skills": match_data.get("missing_skills", []) if match_data else [],
                    "explanation": match_data.get("explanation", "") if match_data else ""
                }
            })
            
        # Sort by match score descending (unscored items at the bottom)
        formatted_jobs.sort(key=lambda x: x["match"]["score"] if x["match"]["score"] is not None else -1, reverse=True)
        return formatted_jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/applications")
def get_applications():
    """
    Fetches application records (e.g., for Kanban drag-and-drop feed).
    """
    try:
        res = supabase.table("applications").select("*, jobs(*, matches(score))").execute()
        apps = res.data or []
        
        formatted_apps = []
        for app in apps:
            job = app.get("jobs", {}) or {}
            match_data = job.get("matches", [])
            if isinstance(match_data, list) and match_data:
                match_data = match_data[0]
            elif not isinstance(match_data, dict):
                match_data = {}
            score = match_data.get("score") if match_data else None
            
            formatted_apps.append({
                "id": app.get("id"),
                "job_id": app.get("job_id"),
                "status": app.get("status"),
                "tailored_resume_url": app.get("tailored_resume_url"),
                "cover_letter": app.get("cover_letter"),
                "applied_at": app.get("applied_at"),
                "updated_at": app.get("updated_at"),
                "job": {
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "description": job.get("description"),
                    "url": job.get("url")
                },
                "score": score
            })
        return formatted_apps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/applications/{job_id}/approve")
def approve_application(job_id: str, background_tasks: BackgroundTasks):
    """
    Human Review Gate approval: launches browser bot to submit application in the background.
    """
    try:
        # Verify application exists
        res = supabase.table("applications").select("id").eq("job_id", job_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Application record not found.")
            
        # Add Playwright submission background task
        background_tasks.add_task(submit_application_task, job_id=job_id)
        
        return {
            "success": True, 
            "message": "Application approved. Submitting application autonomously via browser bot in the background."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/applications/{job_id}/reject")
def reject_application(job_id: str):
    """
    Human Review Gate rejection: archives application to 'rejected'.
    """
    try:
        res = supabase.table("applications").select("id").eq("job_id", job_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Application record not found.")
            
        supabase.table("applications").update({
            "status": "rejected"
        }).eq("job_id", job_id).execute()
        
        return {"success": True, "message": "Application rejected and archived."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/applications/{job_id}")
def edit_application(job_id: str, payload: ApplicationEdit):
    """
    Allows inline editing of cover letter details in Review Gate.
    """
    try:
        res = supabase.table("applications").select("id").eq("job_id", job_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Application record not found.")
            
        supabase.table("applications").update({
            "cover_letter": payload.cover_letter
        }).eq("job_id", job_id).execute()
        
        return {"success": True, "message": "Application details updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/applications/{job_id}/status")
def update_application_status(job_id: str, payload: ApplicationStatusUpdate):
    """
    Updates status details directly (e.g. dragging across Kanban board lanes).
    """
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid application status.")
        
    try:
        res = supabase.table("applications").select("id").eq("job_id", job_id).execute()
        if not res.data:
            # Create application if dragged from Scored Job Feed
            supabase.table("applications").insert({
                "job_id": job_id,
                "status": payload.status
            }).execute()
        else:
            supabase.table("applications").update({
                "status": payload.status
            }).eq("job_id", job_id).execute()
            
        return {"success": True, "status": payload.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload base resume document, parse structure via Groq, embed, and store in resumes table.
    """
    temp_path = os.path.join(STATIC_DIR, file.filename)
    try:
        # Save upload temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse text and JSON content
        raw_text = extract_text_from_file(temp_path)
        parsed_json = parse_resume_json(raw_text)
        
        # Generate embedding vector
        resume_embedding = get_embedding(raw_text)
        
        # Save to database
        supabase.table("resumes").insert({
            "raw_text": raw_text,
            "parsed_json": parsed_json,
            "embedding": resume_embedding
        }).execute()
        
        return {"success": True, "filename": file.filename, "parsed": parsed_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume uploading failed: {str(e)}")
    finally:
        # Clean temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/resume")
def get_resume():
    """
    Fetches latest uploaded base resume content.
    """
    try:
        res = supabase.table("resumes").select("*").order("uploaded_at", desc=True).limit(1).execute()
        if not res.data:
            return None
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/resume")
def update_resume_json(payload: dict):
    """
    Allows user to edit their parsed base resume JSON directly on settings page.
    """
    try:
        # Fetch latest resume
        res = supabase.table("resumes").select("id, raw_text").order("uploaded_at", desc=True).limit(1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="No resume uploaded to update.")
        
        resume_id = res.data[0]["id"]
        raw_text = res.data[0]["raw_text"]
        
        # Compute new embedding if skills/projects text might have changed (for V1 we simply re-embed raw text, 
        # but storing updated JSON is the primary action).
        supabase.table("resumes").update({
            "parsed_json": payload
        }).eq("id", resume_id).execute()
        
        return {"success": True, "message": "Base resume details updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/run")
def trigger_pipeline(
    background_tasks: BackgroundTasks, 
    keywords: str = "AI Engineer", 
    limit: int = 5,
    skip_scout: bool = False,
    skip_scorer: bool = False
):
    """
    Runs the orchestrator E2E pipeline as a background task.
    """
    background_tasks.add_task(
        orchestrator.run_pipeline, 
        keywords=keywords, 
        limit=limit,
        skip_scout=skip_scout,
        skip_scorer=skip_scorer
    )
    return {"success": True, "message": "Pipeline run started in background."}

@app.on_event("startup")
async def startup_event():
    import asyncio
    from scheduler import scheduler_loop
    asyncio.create_task(scheduler_loop())

