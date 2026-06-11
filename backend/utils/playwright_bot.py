import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, Locator
from db import supabase
from config import settings
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_ID = "00000000-0000-0000-0000-000000000000"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def answer_application_question(question: str, resume_json: dict, job_desc: str) -> str:
    """
    Uses Groq Llama-3.3-70b to answer custom/assessment application questions based on candidate resume.
    """
    logger.info(f"Answering custom question via Groq: '{question}'...")
    prompt = f"""You are an applicant applying for a job. Answer the following job application question concisely (2-3 sentences, max 100 words) based on your resume.
Write in the first-person ("I have...", "In my project..."). Do not add any greeting, signature, or surrounding explanations — just output the direct answer text.

Job Description:
{job_desc}

My Resume Profile (JSON):
{json.dumps(resume_json, indent=2)}

Question to Answer:
"{question}"
"""
    try:
        client = Groq(api_key=settings.groq_api_key)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3
        )
        answer = chat_completion.choices[0].message.content.strip()
        logger.info(f"Generated Answer: {answer}")
        return answer
    except Exception as e:
        logger.error(f"Failed to generate answer via Groq: {e}")
        return "I have relevant experience in software development and technical systems matching the job specifications."

async def find_and_select_option(select_locator: Locator, target: str):
    """
    Simplify Copilot logic: matches a target configuration value to select option texts.
    """
    try:
        options = await select_locator.locator("option").all_inner_texts()
        target_lower = target.lower()
        
        # Heuristic Matching
        matched_index = -1
        for i, opt in enumerate(options):
            opt_lower = opt.lower()
            
            # Decline/Prefer not to say
            if "decline" in target_lower or "prefer not" in target_lower or "wish not" in target_lower:
                if any(x in opt_lower for x in ["decline", "prefer not", "wish not", "choose not", "opt out", "not self"]):
                    matched_index = i
                    break
            
            # Gender
            elif target_lower in ["male", "man"]:
                if "male" in opt_lower or "man" in opt_lower:
                    if "female" not in opt_lower and "woman" not in opt_lower:
                        matched_index = i
                        break
            elif target_lower in ["female", "woman"]:
                if "female" in opt_lower or "woman" in opt_lower:
                    matched_index = i
                    break
            
            # Yes / No
            elif target_lower == "yes" or target is True:
                if opt_lower == "yes" or opt_lower.startswith("yes"):
                    matched_index = i
                    break
            elif target_lower == "no" or target is False:
                if opt_lower == "no" or opt_lower.startswith("no"):
                    matched_index = i
                    break
            
            # Direct match
            elif target_lower in opt_lower:
                matched_index = i
                break
                
        if matched_index != -1:
            option_val = await select_locator.locator("option").nth(matched_index).get_attribute("value")
            await select_locator.select_option(option_val)
            logger.info(f"Selected option '{options[matched_index]}' matching target '{target}'")
        else:
            # Fallback to last option (often "Decline to state")
            await select_locator.select_option(index=len(options)-1)
    except Exception as e:
        logger.error(f"Error selecting option for target {target}: {e}")

async def auto_fill_simplify_copilot_fields(page: Page, settings_dict: dict):
    """
    Simplify Copilot Form Autofiller:
    Scans the DOM for standard fields like socials, legal demographics, and work authorization.
    """
    logger.info("[Simplify Copilot] Scanning page for demographics, authorization, and social links...")
    
    # 1. Fill Social Links
    socials = [
        {"key": "github_url", "label_terms": ["github"], "names": ["github", "github_url"]},
        {"key": "linkedin_url", "label_terms": ["linkedin"], "names": ["linkedin", "linkedin_url"]},
        {"key": "portfolio_url", "label_terms": ["portfolio", "website", "personal website"], "names": ["website", "portfolio", "personal_website"]}
    ]
    
    for social in socials:
        val = settings_dict.get(social["key"], "")
        if not val:
            continue
            
        # Target by input names
        for name in social["names"]:
            input_el = page.locator(f"input[name*='{name}'], input[id*='{name}']").first
            if await input_el.is_visible():
                await input_el.fill(val)
                logger.info(f"[Simplify Copilot] Filled social link: {social['key']}")
                break
                
    # 2. Fill legal/demographics selects
    demographics = [
        {"key": "gender", "terms": ["gender", "sex"]},
        {"key": "race", "terms": ["race", "ethnicity", "heritage"]},
        {"key": "disability_status", "terms": ["disability", "disable"]},
        {"key": "veteran_status", "terms": ["veteran", "military"]}
    ]
    
    selects = await page.locator("select").all()
    for select in selects:
        name_attr = (await select.get_attribute("name") or "").lower()
        id_attr = (await select.get_attribute("id") or "").lower()
        
        # Check associated label
        label_text = ""
        if id_attr:
            label_el = page.locator(f"label[for='{id_attr}']")
            if await label_el.count() > 0:
                label_text = (await label_el.inner_text()).lower()
                
        combined_text = name_attr + " " + id_attr + " " + label_text
        
        for demo in demographics:
            if any(term in combined_text for term in demo["terms"]):
                target_val = settings_dict.get(demo["key"])
                if target_val:
                    await find_and_select_option(select, target_val)
                    break
                    
    # 3. Fill Work Authorization
    # Look for Yes/No selects related to sponsorship or work authorization
    for select in selects:
        name_attr = (await select.get_attribute("name") or "").lower()
        id_attr = (await select.get_attribute("id") or "").lower()
        label_text = ""
        if id_attr:
            label_el = page.locator(f"label[for='{id_attr}']")
            if await label_el.count() > 0:
                label_text = (await label_el.inner_text()).lower()
        combined_text = name_attr + " " + id_attr + " " + label_text
        
        # Will you require sponsorship?
        if any(term in combined_text for term in ["sponsorship", "sponsor", "require visa"]):
            target_val = "Yes" if settings_dict.get("requires_sponsorship") else "No"
            await find_and_select_option(select, target_val)
            
        # Are you authorized to work?
        elif any(term in combined_text for term in ["authorized", "eligible to work", "legal right"]):
            target_val = "Yes" if settings_dict.get("authorized_to_work") else "No"
            await find_and_select_option(select, target_val)

async def submit_application_task(job_id: str):
    """
    FastAPI Background Task to run the Playwright browser bot.
    Logs in, fills forms, uploads assets, answers custom questions, and submits.
    """
    logger.info(f"[Playwright Bot] Launching submission agent for job ID: {job_id}...")
    
    # 1. Fetch Application & Job details
    app_res = supabase.table("applications").select("*, jobs(*)").eq("job_id", job_id).execute()
    if not app_res.data:
        logger.error(f"[Playwright Bot] Application not found for job ID: {job_id}")
        return
    
    app_data = app_res.data[0]
    job_data = app_data.get("jobs", {})
    source = job_data.get("source", "").lower()
    job_url = job_data.get("url", "")
    cover_letter = app_data.get("cover_letter", "")
    tailored_resume_url = app_data.get("tailored_resume_url", "")
    
    # 2. Fetch credentials and profile from system_settings
    settings_res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
    db_settings = settings_res.data[0] if settings_res.data else {}
    
    # Resolve local path for the tailored resume file if it is a relative url
    resume_path = None
    if tailored_resume_url:
        if "/static/" in tailored_resume_url:
            relative_path = tailored_resume_url.split("/static/")[-1]
            resume_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", relative_path)
            
    # Resolve Candidate name/details from resume
    resume_res = supabase.table("resumes").select("parsed_json").order("uploaded_at", desc=True).limit(1).execute()
    resume_json = resume_res.data[0]["parsed_json"] if resume_res.data else {}
    
    candidate_name = resume_json.get("name", "Rishabh Sharma")
    candidate_email = db_settings.get("gmail_email", "risha@example.com")
    candidate_phone = "+919876543210"
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            if "internshala" in source or "internshala" in job_url:
                await run_internshala_submission(
                    page=page,
                    job_url=job_url,
                    email=db_settings.get("internshala_email"),
                    password=db_settings.get("internshala_password"),
                    cover_letter=cover_letter,
                    resume_json=resume_json,
                    job_desc=job_data.get("description", "")
                )
            elif "greenhouse" in job_url:
                await run_greenhouse_submission(
                    page=page,
                    job_url=job_url,
                    name=candidate_name,
                    email=candidate_email,
                    phone=candidate_phone,
                    resume_path=resume_path,
                    cover_letter=cover_letter,
                    settings_dict=db_settings
                )
            elif "lever" in job_url:
                await run_lever_submission(
                    page=page,
                    job_url=job_url,
                    name=candidate_name,
                    email=candidate_email,
                    phone=candidate_phone,
                    resume_path=resume_path,
                    cover_letter=cover_letter,
                    settings_dict=db_settings
                )
            else:
                # Fallback Generic form filler
                await run_generic_submission(
                    page=page,
                    job_url=job_url,
                    name=candidate_name,
                    email=candidate_email,
                    phone=candidate_phone,
                    resume_path=resume_path,
                    cover_letter=cover_letter,
                    settings_dict=db_settings
                )
                
            # Log success screenshot
            ss_path = os.path.join(SCREENSHOT_DIR, f"{job_id}_success.png")
            await page.screenshot(path=ss_path)
            logger.info(f"[Playwright Bot] Submission succeeded! Saved success screenshot to {ss_path}")
            
            # Update application status in DB
            supabase.table("applications").update({
                "status": "applied",
                "applied_at": "now()"
            }).eq("job_id", job_id).execute()
            
            # Send immediate success email notification
            try:
                from utils.digest import send_application_success_email
                send_application_success_email(
                    job_title=job_data.get("title", "Unknown Role"),
                    company=job_data.get("company", "Unknown Company"),
                    job_url=job_url
                )
            except Exception as email_err:
                logger.error(f"[Playwright Bot] Failed to trigger success email notification: {email_err}")
            
        except Exception as e:
            # Capture error state
            ss_path = os.path.join(SCREENSHOT_DIR, f"{job_id}_error.png")
            try:
                await page.screenshot(path=ss_path)
            except Exception:
                pass
            logger.error(f"[Playwright Bot] Submission failed: {e}. Saved error screenshot to {ss_path}")
            
            # Revert status
            supabase.table("applications").update({
                "status": "saved"
            }).eq("job_id", job_id).execute()
            
        finally:
            await browser.close()

async def run_internshala_submission(page: Page, job_url: str, email: str, password: str, cover_letter: str, resume_json: dict, job_desc: str):
    """
    Submits application on Internshala.
    """
    if not email or not password:
        raise ValueError("Internshala credentials not configured in settings.")
        
    logger.info("[Playwright Bot] Navigating to Internshala Login...")
    await page.goto("https://internshala.com/login/user")
    
    await page.fill("#email", email)
    await page.fill("#password", password)
    await page.click("#submit")
    await page.wait_for_timeout(3000)
    
    logger.info(f"[Playwright Bot] Navigating to Job URL: {job_url}")
    await page.goto(job_url)
    await page.wait_for_load_state("networkidle")
    
    apply_btn = page.locator("#apply_now_button")
    if await apply_btn.is_visible():
        await apply_btn.click()
        await page.wait_for_timeout(2000)
    else:
        already_applied = page.locator(".already_applied_message")
        if await already_applied.is_visible():
            logger.info("[Playwright Bot] Already applied to this Internshala listing.")
            return
        raise Exception("Could not find 'Apply Now' button on Internshala page.")
        
    textareas = await page.locator("textarea").all()
    for ta in textareas:
        placeholder = await ta.get_attribute("placeholder") or ""
        label_el = page.locator(f"label[for='{await ta.get_attribute('id')}']")
        label_text = await label_el.inner_text() if await label_el.count() > 0 else ""
        combined_text = (placeholder + " " + label_text).lower()
        
        if "why should you be hired" in combined_text or "cover letter" in combined_text or "why do you think you are suitable" in combined_text:
            await ta.fill(cover_letter)
        elif "availability" in combined_text or "available to start" in combined_text:
            await ta.fill("Yes, I am available to start immediately for the full duration of the role.")
        else:
            question_text = label_text if label_text else placeholder
            if not question_text:
                question_text = "Custom assessment question"
            logger.info("Pacing delay: waiting 4 seconds before answering custom question...")
            await asyncio.sleep(4)
            ans = answer_application_question(question_text, resume_json, job_desc)
            await ta.fill(ans)
            
    submit_btn = page.locator("input[type='submit']#submit") or page.locator("button#submit_application")
    if await submit_btn.count() == 0:
        submit_btn = page.locator("input[type='submit'], button[type='submit']").first
        
    if await submit_btn.is_visible():
        await submit_btn.scroll_into_view_if_needed()
        await submit_btn.click()
        await page.wait_for_timeout(4000)
        logger.info("[Playwright Bot] Submitted Internshala application.")
    else:
        raise Exception("Could not locate Internshala form Submit button.")

async def run_greenhouse_submission(page: Page, job_url: str, name: str, email: str, phone: str, resume_path: Optional[str], cover_letter: str, settings_dict: dict):
    """
    Submits application on Greenhouse.
    """
    logger.info(f"[Playwright Bot] Navigating to Greenhouse Job URL: {job_url}")
    await page.goto(job_url)
    await page.wait_for_load_state("networkidle")
    
    names = name.split(" ")
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else names[0]
    
    # Fill personal info
    await page.fill("input[name='job_application[first_name]']", first_name)
    await page.fill("input[name='job_application[last_name]']", last_name)
    await page.fill("input[name='job_application[email]']", email)
    await page.fill("input[name='job_application[phone]']", phone)
    
    # Simplify Copilot: Demographics, Socials, Work Auth
    await auto_fill_simplify_copilot_fields(page, settings_dict)
    
    # Resume Upload
    if resume_path and os.path.exists(resume_path):
        logger.info(f"[Playwright Bot] Uploading tailored resume PDF from {resume_path}...")
        file_input = page.locator("input[type='file'][accept*='pdf']").first or page.locator("input#resume_file")
        await file_input.set_input_files(resume_path)
        await page.wait_for_timeout(1000)
        
    # Cover Letter textarea
    cl_area = page.locator("textarea[name='job_application[cover_letter]']") or page.locator("textarea#cover_letter")
    if await cl_area.is_visible():
        await cl_area.fill(cover_letter)
        
    # Click Submit Application
    submit_btn = page.locator("input[type='submit']#submit_app") or page.locator("#submit_app")
    await submit_btn.scroll_into_view_if_needed()
    await submit_btn.click()
    await page.wait_for_timeout(4000)
    logger.info("[Playwright Bot] Submitted Greenhouse application.")

async def run_lever_submission(page: Page, job_url: str, name: str, email: str, phone: str, resume_path: Optional[str], cover_letter: str, settings_dict: dict):
    """
    Submits application on Lever.
    """
    logger.info(f"[Playwright Bot] Navigating to Lever Job URL: {job_url}")
    apply_url = job_url if job_url.endswith("/apply") else f"{job_url}/apply"
    await page.goto(apply_url)
    await page.wait_for_load_state("networkidle")
    
    # Resume Upload
    if resume_path and os.path.exists(resume_path):
        logger.info(f"[Playwright Bot] Uploading tailored resume PDF from {resume_path}...")
        file_input = page.locator("input[type='file'][id='resume-upload-input']")
        await file_input.set_input_files(resume_path)
        await page.wait_for_timeout(2000)
        
    # Fill personal info
    await page.fill("input[name='name']", name)
    await page.fill("input[name='email']", email)
    await page.fill("input[name='phone']", phone)
    
    # Simplify Copilot Autofill
    await auto_fill_simplify_copilot_fields(page, settings_dict)
    
    # Cover Letter
    cl_area = page.locator("textarea[name='comments']")
    if await cl_area.is_visible():
        await cl_area.fill(cover_letter)
        
    submit_btn = page.locator("button[type='submit']#submit-application") or page.locator(".template-btn-submit")
    await submit_btn.scroll_into_view_if_needed()
    await submit_btn.click()
    await page.wait_for_timeout(4000)
    logger.info("[Playwright Bot] Submitted Lever application.")

async def run_generic_submission(page: Page, job_url: str, name: str, email: str, phone: str, resume_path: Optional[str], cover_letter: str, settings_dict: dict):
    """
    Fallback generic form filler for other career portals.
    """
    logger.info(f"[Playwright Bot] Navigating to Generic Job URL: {job_url}")
    await page.goto(job_url)
    await page.wait_for_load_state("networkidle")
    
    # Indeed external redirect handling
    if "indeed.com" in job_url:
        logger.info("[Playwright Bot] Indeed URL detected. Looking for redirect or easy apply buttons...")
        apply_selectors = [
            "a:has-text('Apply on company site')", 
            "button:has-text('Apply on company site')",
            "a:has-text('Apply now')", 
            "button:has-text('Apply now')",
            "#indeedApplyButton",
            ".css-ia3gsu"
        ]
        
        btn = None
        for sel in apply_selectors:
            el = page.locator(sel).first
            if await el.is_visible():
                btn = el
                break
                
        if btn:
            logger.info("[Playwright Bot] Found Indeed apply button. Clicking...")
            try:
                async with page.expect_popup(timeout=5000) as popup_info:
                    await btn.click()
                page = await popup_info.value
                await page.wait_for_load_state("networkidle")
                logger.info(f"[Playwright Bot] Redirected page URL: {page.url}")
                
                # Check for specialised handoffs
                new_url = page.url
                if "greenhouse" in new_url:
                    await run_greenhouse_submission(page, new_url, name, email, phone, resume_path, cover_letter, settings_dict)
                    return
                elif "lever" in new_url:
                    await run_lever_submission(page, new_url, name, email, phone, resume_path, cover_letter, settings_dict)
                    return
            except Exception as click_err:
                logger.warning(f"[Playwright Bot] Indeed click redirect failed: {click_err}, continuing on current page...")
                await btn.click()
                await page.wait_for_timeout(4000)
                
    apply_links = ["apply", "submit application", "apply now", "join us"]
    for link_text in apply_links:
        btn = page.locator(f"text={link_text}").first
        if await btn.is_visible():
            await btn.click()
            await page.wait_for_timeout(2000)
            break
            
    name_inputs = await page.locator("input[name*='name'], input[id*='name']").all()
    for inp in name_inputs:
        placeholder = (await inp.get_attribute("placeholder") or "").lower()
        name_attr = (await inp.get_attribute("name") or "").lower()
        if "first" in placeholder or "first" in name_attr:
            await inp.fill(name.split(" ")[0])
        elif "last" in placeholder or "last" in name_attr:
            await inp.fill(name.split(" ")[-1])
        else:
            await inp.fill(name)
            
    email_inputs = await page.locator("input[type='email'], input[name*='email']").all()
    for inp in email_inputs:
        await inp.fill(email)
        
    phone_inputs = await page.locator("input[type='tel'], input[name*='phone']").all()
    for inp in phone_inputs:
        await inp.fill(phone)
        
    # Simplify Copilot Autofill
    await auto_fill_simplify_copilot_fields(page, settings_dict)
    
    if resume_path and os.path.exists(resume_path):
        file_inputs = await page.locator("input[type='file']").all()
        for fi in file_inputs:
            accept = await fi.get_attribute("accept") or ""
            if "pdf" in accept or "document" in accept or fi == file_inputs[0]:
                await fi.set_input_files(resume_path)
                await page.wait_for_timeout(1000)
                break
                
    submits = await page.locator("input[type='submit'], button[type='submit']").all()
    for btn in submits:
        btn_text = (await btn.inner_text() or await btn.get_attribute("value") or "").lower()
        if "submit" in btn_text or "apply" in btn_text or btn == submits[0]:
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(4000)
            logger.info("[Playwright Bot] Clicked generic submit button.")
            break
