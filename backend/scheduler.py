import asyncio
import logging
from db import supabase
from orchestrator import Orchestrator
from agents.tracker import TrackerAgent
from utils.digest import send_daily_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_ID = "00000000-0000-0000-0000-000000000000"

async def scheduler_loop():
    logger.info("[Scheduler] Initializing periodic task scheduler...")
    
    # Wait for FastAPI server to boot up
    await asyncio.sleep(5)
    
    orchestrator = Orchestrator()
    tracker = TrackerAgent()
    
    # Initialize timers (run after initial delay, then periodically)
    scout_timer = 30
    tracker_timer = 60
    digest_timer = 1800
    
    while True:
        try:
            # 1. Fetch current settings from DB
            res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
            settings = res.data[0] if res.data else None
        except Exception as e:
            err_msg = str(e)
            if "relation" in err_msg and "does not exist" in err_msg:
                logger.warning("[Scheduler] 'system_settings' table does not exist. Skipping schedule check.")
            else:
                logger.error(f"[Scheduler] Failed to load settings from DB: {e}")
            settings = None
            
        if settings and settings.get("is_schedule_enabled", True):
            interval_hours = settings.get("schedule_interval_hours", 12)
            interval_seconds = interval_hours * 3600
            
            # Check if it's time to run Job Scout/Scorer
            if scout_timer <= 0:
                logger.info(f"[Scheduler] Triggering periodic Job Scout & Scorer pipeline (Interval: {interval_hours}h)...")
                kw = settings.get("keywords", "AI Engineer")
                limit = settings.get("limit_count", 5)
                try:
                    # Run in thread executor to avoid blocking FastAPI
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, orchestrator.run_pipeline, kw, "", limit)
                    logger.info("[Scheduler] Periodic scouting pipeline completed.")
                except Exception as e:
                    logger.error(f"[Scheduler] Periodic scouting failed: {e}")
                scout_timer = interval_seconds
                
            # Check if it's time to run Gmail Tracker (Every 1 hour)
            if tracker_timer <= 0:
                logger.info("[Scheduler] Triggering periodic Gmail Tracker check...")
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, tracker.run)
                    logger.info("[Scheduler] Periodic Gmail Tracker completed.")
                except Exception as e:
                    logger.error(f"[Scheduler] Periodic Gmail Tracker failed: {e}")
                tracker_timer = 3600
                
            # Check if it's time to send Daily Digest Email (Every 24 hours)
            if digest_timer <= 0:
                logger.info("[Scheduler] Triggering Daily Digest Email report...")
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, send_daily_digest)
                    logger.info("[Scheduler] Daily Digest completed.")
                except Exception as e:
                    logger.error(f"[Scheduler] Daily Digest failed: {e}")
                digest_timer = 86400
                
        else:
            # Scheduling is either disabled or table is missing
            # Reset timers so they trigger immediately once enabled
            scout_timer = 0
            tracker_timer = 0
            digest_timer = 0
            
        # Sleep 60 seconds before next tick
        await asyncio.sleep(60)
        
        if settings and settings.get("is_schedule_enabled", True):
            scout_timer -= 60
            tracker_timer -= 60
            digest_timer -= 60
