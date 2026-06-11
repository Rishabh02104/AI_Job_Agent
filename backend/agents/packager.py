from agents.base import BaseAgent, AgentResult
from db import supabase

class PackagerAgent(BaseAgent):
    """
    Agent 5: Application Packager
    Saves the tailored resume path and cover letter text into the 'applications' table
    for a specific job, changing its status to 'reviewing' so it surfaces in the Human Review Gate.
    """
    def run(self, input_data: dict) -> AgentResult:
        job_id = input_data.get("job_id")
        tailored_resume_url = input_data.get("tailored_resume_url")
        cover_letter = input_data.get("cover_letter")

        if not job_id:
            return AgentResult(success=False, error="Job ID is required.")

        try:
            # Check if an application already exists
            app_res = supabase.table("applications").select("id").eq("job_id", job_id).execute()
            
            if app_res.data:
                # Update existing application
                supabase.table("applications").update({
                    "status": "reviewing",
                    "tailored_resume_url": tailored_resume_url,
                    "cover_letter": cover_letter
                }).eq("job_id", job_id).execute()
            else:
                # Insert new application
                supabase.table("applications").insert({
                    "job_id": job_id,
                    "status": "reviewing",
                    "tailored_resume_url": tailored_resume_url,
                    "cover_letter": cover_letter
                }).execute()

            return AgentResult(
                success=True,
                data={
                    "job_id": job_id,
                    "status": "reviewing",
                    "message": "Application package assembled and staged for review."
                }
            )
        except Exception as e:
            return AgentResult(success=False, error=f"Failed to package application: {str(e)}")
