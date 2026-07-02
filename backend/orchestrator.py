import time
import logging
from typing import Dict, Any, List
from agents.scout import ScoutAgent
from agents.scorer import ScorerAgent
from agents.resume_opt import ResumeOptimizerAgent
from agents.cover_letter import CoverLetterAgent
from agents.packager import PackagerAgent
from db import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Coordinates the execution flow of the AI Job Agent backend pipeline:
    1. Job Scout Agent -> Fetch and embed new listings.
    2. Scorer Agent -> Score listings; Auto-stage high matches (>=80%) to 'queued'.
    3. Resume & Cover Letter Agents -> Tailor documents for 'queued' items.
    4. Packager Agent -> Bundle files and advance status to 'reviewing' (Human Gate).
    """
    def __init__(self):
        self.scout = ScoutAgent()
        self.scorer = ScorerAgent()
        self.optimizer = ResumeOptimizerAgent()
        self.cover_letter_agent = CoverLetterAgent()
        self.packager = PackagerAgent()

    def run_pipeline(
        self, 
        keywords: str = "software engineer", 
        location: str = "", 
        limit: int = 5,
        skip_scout: bool = False,
        skip_scorer: bool = False
    ) -> dict:
        logger.info(f"Starting pipeline run (skip_scout={skip_scout}, skip_scorer={skip_scorer})...")
        
        pipeline_status = {
            "scout": None,
            "scorer": None,
            "tailored_applications": [],
            "errors": []
        }

        # Step 1: Run Job Scout
        if not skip_scout:
            logger.info("Executing Step 1: Job Scout...")
            scout_res = self.scout.run({"keywords": keywords, "location": location, "limit": limit})
            pipeline_status["scout"] = scout_res.data
            
            if not scout_res.success:
                logger.warning(f"Scout Agent stopped: {scout_res.error}")
                pipeline_status["errors"].append(f"Scout stopped: {scout_res.error}")
                # Do not crash the pipeline; try to score whatever might be unscored in the DB from previous runs.
        else:
            logger.info("Skipping Step 1: Job Scout as requested.")
        
        # Step 2: Run Scorer
        if not skip_scorer:
            logger.info("Executing Step 2: Match Scorer...")
            scorer_res = self.scorer.run({"limit": limit})
            pipeline_status["scorer"] = scorer_res.data
            
            if not scorer_res.success:
                logger.error(f"Scorer Agent failed: {scorer_res.error}")
                pipeline_status["errors"].append(f"Scorer failed: {scorer_res.error}")
                return pipeline_status
        else:
            logger.info("Skipping Step 2: Match Scorer as requested.")

        # Step 3: Identify 'queued' applications that need tailoring
        logger.info("Checking for 'queued' applications that need tailoring...")
        try:
            queued_res = supabase.table("applications").select("job_id").eq("status", "queued").execute()
            queued_jobs = queued_res.data or []
        except Exception as e:
            logger.error(f"Failed to query queued applications: {e}")
            pipeline_status["errors"].append(f"DB query error: {str(e)}")
            return pipeline_status

        if not queued_jobs:
            logger.info("No applications are in the queue for tailoring. Pipeline execution complete.")
            return pipeline_status

        logger.info(f"Found {len(queued_jobs)} application(s) queued for tailoring. Processing...")

        # Check if auto_apply is enabled
        auto_apply = False
        try:
            settings_res = supabase.table("system_settings").select("auto_apply").eq("id", "00000000-0000-0000-0000-000000000000").execute()
            if settings_res.data:
                auto_apply = settings_res.data[0].get("auto_apply", False)
        except Exception as e:
            logger.warning(f"Could not load auto_apply setting: {e}")

        # Step 4: Tailor resume and cover letter for each queued job
        for idx, qj in enumerate(queued_jobs):
            job_id = qj["job_id"]
            logger.info(f"Processing tailoring for Job ID: {job_id}...")

            # Run Resume Optimizer (with retries for Groq rate limits)
            if idx > 0:
                logger.info("Pacing delay: waiting 20 seconds before starting next job tailoring...")
                time.sleep(20)
                
            opt_res = self._run_agent_with_retry(self.optimizer, {"job_id": job_id}, retries=4, backoff=20.0)
            if not opt_res or not opt_res.success:
                err_msg = f"Resume optimization failed for job {job_id}: {opt_res.error if opt_res else 'Timeout'}"
                logger.error(err_msg)
                pipeline_status["errors"].append(err_msg)
                continue

            tailored_resume_url = opt_res.data.get("tailored_resume_url")

            # Pacing delay: wait 20 seconds between optimizer and cover letter agent
            logger.info("Pacing delay: waiting 20 seconds before generating cover letter...")
            time.sleep(20)

            # Run Cover Letter Agent
            cl_res = self._run_agent_with_retry(self.cover_letter_agent, {"job_id": job_id}, retries=4, backoff=20.0)
            if not cl_res or not cl_res.success:
                err_msg = f"Cover letter generation failed for job {job_id}: {cl_res.error if cl_res else 'Timeout'}"
                logger.error(err_msg)
                pipeline_status["errors"].append(err_msg)
                continue

            cover_letter_text = cl_res.data.get("cover_letter")

            # Run Packager
            pkg_res = self.packager.run({
                "job_id": job_id,
                "tailored_resume_url": tailored_resume_url,
                "cover_letter": cover_letter_text
            })

            if not pkg_res.success:
                err_msg = f"Application packaging failed for job {job_id}: {pkg_res.error}"
                logger.error(err_msg)
                pipeline_status["errors"].append(err_msg)
            else:
                logger.info(f"Job ID {job_id} successfully packaged and advanced to Human Review Gate.")
                pipeline_status["tailored_applications"].append(job_id)
                
                # Check for Auto-Apply
                if auto_apply:
                    logger.info(f"Auto-Apply enabled. Launching submission for Job ID {job_id}...")
                    try:
                        from utils.playwright_bot import submit_application_task
                        import asyncio
                        
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = None
                            
                        if loop and loop.is_running():
                            loop.create_task(submit_application_task(job_id))
                        else:
                            asyncio.run(submit_application_task(job_id))
                    except Exception as apply_err:
                        logger.error(f"Failed to auto-apply for job {job_id}: {apply_err}")

        logger.info("Pipeline E2E execution finished.")
        return pipeline_status

    def _run_agent_with_retry(self, agent: Any, inputs: dict, retries: int = 4, backoff: float = 20.0) -> Any:
        """
        Executes an agent run with automatic retries for rate-limiting (HTTP 429) errors.
        """
        for i in range(retries):
            res = agent.run(inputs)
            if res.success:
                return res
            
            # If rate limited (often error code 429 or containing 'rate limit')
            if res.error and ("429" in res.error or "rate limit" in res.error.lower()):
                wait_time = backoff * (2 ** i)
                logger.warning(f"Groq Rate Limit detected. Retrying in {wait_time}s... (Attempt {i+1}/{retries})")
                time.sleep(wait_time)
            else:
                # Do not retry on other validation/logic errors
                return res
        return None
