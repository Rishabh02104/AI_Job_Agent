import os
import sys
import asyncio
from unittest.mock import MagicMock
import playwright.async_api

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Mock supabase client
import db
mock_supabase = MagicMock()
db.supabase = mock_supabase

class MockResponse:
    def __init__(self, data):
        self.data = data

html_path = os.path.abspath(os.path.join(backend_dir, "static", "dry_run_redirect_test.html"))
file_url = f"file:///{html_path.replace(os.sep, '/')}"

mock_app_data = [{
    "job_id": "dummy-job-id",
    "tailored_resume_url": "http://localhost:8000/static/resumes/dummy_resume.pdf",
    "cover_letter": "I am excited to apply for the AI Engineer role...",
    "jobs": {
        "title": "AI Engineer",
        "company": "Virtusa",
        "source": "adzuna",
        "url": file_url
    }
}]

mock_settings_data = [{
    "run_headless": False,
    "gmail_email": "rishavendrasharma9353@gmail.com",
    "gmail_app_password": "mock-password"
}]

mock_resume_data = [{
    "parsed_json": {
        "name": "Rishabh Sharma",
        "email": "rishavendrasharma9353@gmail.com",
        "phone": "+919876543210"
    }
}]

def get_table_mock(table_name):
    mock_table = MagicMock()
    
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    
    mock_eq = MagicMock()
    mock_select.eq.return_value = mock_eq
    
    mock_order = MagicMock()
    mock_select.order.return_value = mock_order
    
    mock_limit = MagicMock()
    mock_order.limit.return_value = mock_limit
    
    if table_name == "applications":
        mock_eq.execute.return_value = MockResponse(mock_app_data)
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value = MockResponse([{"status": "applied"}])
    elif table_name == "system_settings":
        mock_eq.execute.return_value = MockResponse(mock_settings_data)
    elif table_name == "resumes":
        mock_limit.execute.return_value = MockResponse(mock_resume_data)
        
    return mock_table

mock_supabase.table.side_effect = get_table_mock

# Monkey-patch BrowserContext to auto-solve page
original_new_page = playwright.async_api.BrowserContext.new_page

async def patched_new_page(self, *args, **kwargs):
    page = await original_new_page(self, *args, **kwargs)
    asyncio.create_task(auto_solve_page(page))
    return page

playwright.async_api.BrowserContext.new_page = patched_new_page

async def auto_solve_page(page):
    await asyncio.sleep(4)
    try:
        current_url = page.url
        if "dry_run_captcha_test" in current_url:
            print("\n[Test Harness] Simulated user: Clicking CAPTCHA checkbox...")
            await page.click("input[id='captcha-check']")
            await asyncio.sleep(2)
            print("[Test Harness] Simulated user: Clicking Submit Application button...")
            await page.click("button[id='submit-btn']")
    except Exception as e:
        print(f"[Test Harness] Error simulating interaction: {e}")

from utils.playwright_bot import submit_application_task

async def main():
    print("==================================================================")
    print("           PLAYWRIGHT AGGREGATOR REDIRECT DRY RUN TEST            ")
    print("==================================================================")
    print(f"Loading local Adzuna redirect landing: {file_url}")
    print("Launching Chromium browser in HEADED mode...")
    print("==================================================================")
    
    await submit_application_task("dummy-job-id")
    
    print("\nRedirection dry run completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
