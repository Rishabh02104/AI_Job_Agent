import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from agents.base import BaseAgent, AgentResult
from utils.parser import get_embedding
from db import supabase
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ScoutAgent(BaseAgent):
    """
    Agent 1: Job Scout
    Searches Adzuna (free tier API) and Internshala (scrapes search page + detail descriptions)
    Deduplicates listings by URL, computes local 384-d vector embeddings,
    and inserts them into the Supabase 'jobs' table.
    """
    def run(self, input_data: dict) -> AgentResult:
        keywords = input_data.get("keywords", "software engineer")
        location = input_data.get("location", "")
        limit = input_data.get("limit", 10)
        
        jobs_fetched = []
        errors = []

        # 1. Fetch from Adzuna if credentials exist
        if settings.adzuna_app_id and settings.adzuna_app_id != "placeholder":
            try:
                adzuna_jobs = self._fetch_adzuna(keywords, location, limit)
                jobs_fetched.extend(adzuna_jobs)
            except Exception as e:
                errors.append(f"Adzuna error: {str(e)}")
        else:
            errors.append("Adzuna not configured, skipping.")

        # 2. Fetch from Internshala
        try:
            internshala_jobs = self._fetch_internshala(keywords, limit)
            jobs_fetched.extend(internshala_jobs)
        except Exception as e:
            errors.append(f"Internshala error: {str(e)}")

        # 3. Fetch from Indeed
        try:
            indeed_jobs = self._fetch_indeed(keywords, limit)
            jobs_fetched.extend(indeed_jobs)
        except Exception as e:
            errors.append(f"Indeed error: {str(e)}")


        if not jobs_fetched:
            return AgentResult(
                success=False,
                data=[],
                error=f"No jobs found. Errors: {'; '.join(errors)}"
            )

        # 3. Deduplicate, generate embeddings, and save to Supabase
        saved_count = 0
        skipped_count = 0

        for job in jobs_fetched:
            url = job["url"]
            # Check deduplication
            res = supabase.table("jobs").select("id").eq("url", url).execute()
            if res.data:
                skipped_count += 1
                continue

            try:
                # Generate embedding for the description
                embedding = get_embedding(job["description"])
                
                # Insert into Supabase
                supabase.table("jobs").insert({
                    "title": job["title"],
                    "company": job["company"],
                    "description": job["description"],
                    "location": job["location"],
                    "source": job["source"],
                    "url": job["url"],
                    "embedding": embedding
                }).execute()
                saved_count += 1
            except Exception as e:
                errors.append(f"DB insert error for {url}: {str(e)}")

        return AgentResult(
            success=True,
            data={
                "fetched": len(jobs_fetched),
                "saved": saved_count,
                "skipped_duplicates": skipped_count,
                "errors": errors
            }
        )

    def _fetch_adzuna(self, keywords: str, location: str, limit: int) -> List[Dict[str, Any]]:
        # Adzuna API URL (defaults to India 'in' search)
        country = "in"
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_api_key,
            "results_per_page": limit,
            "what": keywords,
            "content-type": "application/json"
        }
        if location:
            params["where"] = location

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for result in data.get("results", []):
            jobs.append({
                "title": result.get("title", "").strip(),
                "company": result.get("company", {}).get("display_name", "").strip(),
                "description": BeautifulSoup(result.get("description", ""), "html.parser").get_text().strip(),
                "location": result.get("location", {}).get("display_name", "").strip(),
                "source": "Adzuna",
                "url": result.get("redirect_url", "").strip()
            })
        return jobs

    def _fetch_internshala(self, keywords: str, limit: int) -> List[Dict[str, Any]]:
        # Map keywords to Internshala slugs
        # Example: 'software engineer' -> 'software-development'
        kw_slug = keywords.lower().replace(" ", "-")
        search_url = f"https://internshala.com/jobs/keywords-{kw_slug}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            # Fallback to main jobs page if search page is not found
            search_url = "https://internshala.com/jobs"
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="individual_internship")
        
        jobs = []
        for card in cards[:limit]:
            title_el = card.find("div", class_="heading_3_5") or card.find("h3", class_="job-internship-name")
            if not title_el:
                continue
            
            # Find the link tag inside title element
            link_tag = title_el.find("a")
            if not link_tag:
                continue
            
            title = link_tag.get_text().strip()
            detail_path = link_tag.get("href", "")
            detail_url = f"https://internshala.com{detail_path}" if detail_path.startswith("/") else detail_path
            
            company_el = card.find("div", class_="company_name") or card.find("p", class_="company-name")
            company = company_el.get_text().strip() if company_el else "Unknown Company"
            
            location_el = card.find("a", class_="location_link") or card.find("span", class_="location")
            location = location_el.get_text().strip() if location_el else "Remote/India"
            
            # Fetch details from individual page to get actual description
            description = self._fetch_internshala_detail(detail_url, headers)
            if not description:
                # Fallback description if detail fetch fails
                description = f"Job listing for {title} at {company} located in {location}. URL: {detail_url}"
                
            jobs.append({
                "title": title,
                "company": company,
                "description": description,
                "location": location,
                "source": "Internshala",
                "url": detail_url
            })
            
        return jobs

    def _fetch_internshala_detail(self, url: str, headers: dict) -> str:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                detail_soup = BeautifulSoup(res.text, "html.parser")
                # Extract main description
                desc_container = detail_soup.find("div", class_="text-container") or detail_soup.find("div", class_="job_description")
                if desc_container:
                    # Clean tags but keep readable spacing
                    return desc_container.get_text("\n").strip()
        except Exception:
            pass
        return ""

    def _fetch_indeed(self, keywords: str, limit: int) -> List[Dict[str, Any]]:
        from playwright.sync_api import sync_playwright
        logger.info(f"[Scout] Fetching Indeed jobs via Playwright for: '{keywords}'...")
        
        jobs = []
        query_slug = keywords.replace(" ", "+")
        indeed_url = f"https://in.indeed.com/jobs?q={query_slug}"
        
        with sync_playwright() as p:
            # Run browser headless to prevent popping window
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            try:
                page.goto(indeed_url, timeout=30000)
                page.wait_for_timeout(3000)
                
                # Check for Cloudflare challenge
                if "cloudflare" in page.content().lower():
                    logger.warning("[Scout] Indeed Cloudflare detected, waiting for challenge...")
                    page.wait_for_timeout(5000)
                    
                # Locate job beacons
                cards = page.locator(".job_seen_beacon").all()
                logger.info(f"[Scout] Found {len(cards)} job card(s) on Indeed.")
                
                for card in cards[:limit]:
                    try:
                        timeout_ms = 1500
                        
                        # Title
                        title = "Unknown Title"
                        for sel in ["h2.jobTitle span", "h2.jobTitle a", "a.jcs-JobTitle"]:
                            try:
                                title = card.locator(sel).first.inner_text(timeout=timeout_ms).strip()
                                if title:
                                    break
                            except Exception:
                                continue
                                
                        # Company
                        company = "Unknown Company"
                        for sel in ["[data-testid='company-name']", ".companyName", ".company_location .companyName"]:
                            try:
                                company = card.locator(sel).first.inner_text(timeout=timeout_ms).strip()
                                if company:
                                    break
                            except Exception:
                                continue
                                
                        # Location
                        location = "Remote/India"
                        for sel in ["[data-testid='text-location']", ".companyLocation", ".company_location .companyLocation"]:
                            try:
                                location = card.locator(sel).first.inner_text(timeout=timeout_ms).strip()
                                if location:
                                    break
                            except Exception:
                                continue
                        
                        # Find link and job id
                        job_id_attr = None
                        link_el = None
                        for sel in ["h2.jobTitle a", "a.jcs-JobTitle"]:
                            try:
                                el = card.locator(sel).first
                                job_id_attr = el.get_attribute("data-jk", timeout=timeout_ms)
                                if job_id_attr:
                                    link_el = el
                                    break
                            except Exception:
                                continue
                        
                        if not job_id_attr:
                            # Try general links inside the card
                            links = card.locator("a").all()
                            for l in links:
                                try:
                                    href = l.get_attribute("href", timeout=timeout_ms) or ""
                                    if "jk=" in href:
                                        job_id_attr = href.split("jk=")[-1].split("&")[0]
                                        link_el = l
                                        break
                                    jk_val = l.get_attribute("data-jk", timeout=timeout_ms)
                                    if jk_val:
                                        job_id_attr = jk_val
                                        link_el = l
                                        break
                                except Exception:
                                    continue
                                    
                        if job_id_attr:
                            url = f"https://in.indeed.com/viewjob?jk={job_id_attr}"
                        elif link_el:
                            try:
                                href = link_el.get_attribute("href", timeout=timeout_ms) or ""
                                url = f"https://in.indeed.com{href}" if href.startswith("/") else href
                            except Exception:
                                url = f"https://in.indeed.com/jobs?q={keywords}"
                        else:
                            url = f"https://in.indeed.com/jobs?q={keywords}"
                            
                        snippet = ""
                        for sel in [".job-snippet", "[data-testid='snippet']", ".summary"]:
                            try:
                                snippet = card.locator(sel).first.inner_text(timeout=timeout_ms).strip()
                                if snippet:
                                    break
                            except Exception:
                                continue
                        
                        description = f"Job Title: {title}\nCompany: {company}\nLocation: {location}\nSummary Details:\n{snippet}"
                        
                        jobs.append({
                            "title": title,
                            "company": company,
                            "description": description,
                            "location": location,
                            "source": "Indeed",
                            "url": url
                        })
                    except Exception as card_err:
                        logger.error(f"[Scout] Error parsing Indeed card: {card_err}")
                        continue
            except Exception as e:
                logger.error(f"[Scout] Failed to fetch Indeed listings: {e}")
            finally:
                browser.close()
                
        return jobs

