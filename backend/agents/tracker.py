import imaplib
import email
from email.header import decode_header
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from agents.base import BaseAgent, AgentResult
from db import supabase
from config import settings
from groq import Groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_ID = "00000000-0000-0000-0000-000000000000"

class TrackerAgent(BaseAgent):
    """
    Agent 6: Gmail Tracker
    Polls the user's Gmail inbox via IMAP, deduplicates processed emails,
    uses Groq (Llama-3.3-70b-versatile) to semantically classify email updates
    (interviews, rejections, offers), and advances Kanban lane positions.
    """
    def run(self, input_data: dict = None) -> AgentResult:
        logger.info("Starting Gmail Tracker Agent...")
        
        # 1. Fetch settings from DB
        try:
            settings_res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
            if not settings_res.data:
                return AgentResult(success=False, error="System settings not found in database.")
            db_settings = settings_res.data[0]
        except Exception as e:
            return AgentResult(success=False, error=f"Database settings error: {e}")

        gmail_email = db_settings.get("gmail_email")
        gmail_app_password = db_settings.get("gmail_app_password")

        if not gmail_email or not gmail_app_password or gmail_email == "" or gmail_app_password == "":
            logger.info("Gmail credentials not fully configured in settings. Skipping email tracking.")
            return AgentResult(success=True, data={"message": "Gmail credentials not configured. Skipping tracker."})

        # 2. Fetch active applications from DB (stages: applied, interview)
        try:
            active_res = supabase.table("applications").select("id, status, jobs(title, company)").or_("status.eq.applied,status.eq.interview").execute()
            active_apps = active_res.data or []
        except Exception as e:
            return AgentResult(success=False, error=f"Failed to fetch active applications: {e}")

        if not active_apps:
            logger.info("No active applications in 'applied' or 'interview' state. Skipping email polling.")
            return AgentResult(success=True, data={"message": "No active applications to track."})

        logger.info(f"Tracking updates for {len(active_apps)} active application(s)...")

        # NOTE: This Gmail IMAP tracking loop is now the SOURCE OF TRUTH for confirming
        # real applied status via the company's own confirmation email. The browser bot's
        # self-reported "applied" status is provisional until an email_events row corroborates it.
        # 3. Connect to Gmail via IMAP
        emails_parsed = []
        updates_detected = []
        errors = []

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(gmail_email, gmail_app_password)
            mail.select("inbox")
            
            # Search emails in the last 7 days to avoid processing old ones
            date_since = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{date_since}")')
            
            if status != "OK":
                return AgentResult(success=False, error="Failed to search emails via IMAP.")
                
            mail_ids = messages[0].split()
            logger.info(f"Found {len(mail_ids)} email(s) received since {date_since}.")
            
            # Connect to Groq
            client = Groq(api_key=settings.groq_api_key)

            # Process most recent emails first
            for mail_id in reversed(mail_ids):
                status, data = mail.fetch(mail_id, "(RFC822)")
                if status != "OK":
                    continue
                    
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")
                    
                # Extract sender
                sender = msg["From"] or ""
                
                # Extract date
                date_str = msg["Date"] or ""
                # Parse email date (fallback to current utc if parse fails)
                try:
                    email_date = email.utils.parsedate_to_datetime(msg["Date"])
                except Exception:
                    email_date = datetime.utcnow()
                
                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    
                body = body.strip()[:1500] # Truncate body to save token limit
                
                # 4. Check for duplicate event (has this email already been parsed?)
                # We check using subject and received_at
                evt_res = supabase.table("email_events").select("id").eq("subject", subject).eq("received_at", email_date.isoformat()).execute()
                if evt_res.data:
                    # Already processed this exact email, skip it
                    continue
                    
                emails_parsed.append({
                    "subject": subject,
                    "sender": sender,
                    "date": email_date.isoformat()
                })
                
                # 5. Call LLM to classify and match this email to active applications
                classification = self._classify_email_with_groq(
                    client=client,
                    sender=sender,
                    subject=subject,
                    body=body,
                    active_apps=active_apps
                )
                
                if classification.get("matched") and classification.get("application_id"):
                    app_id = classification["application_id"]
                    new_status = classification["status"]
                    reason = classification.get("reason", "")
                    
                    # Log event and update application
                    logger.info(f"[Tracker] Match found! Application {app_id} updated to {new_status} (Reason: {reason})")
                    
                    # Update status in applications table
                    supabase.table("applications").update({
                        "status": new_status,
                        "updated_at": "now()"
                    }).eq("id", app_id).execute()
                    
                    # Log event in email_events
                    supabase.table("email_events").insert({
                        "application_id": app_id,
                        "subject": subject,
                        "detected_status": new_status,
                        "received_at": email_date.isoformat()
                    }).execute()
                    
                    updates_detected.append({
                        "application_id": app_id,
                        "subject": subject,
                        "new_status": new_status,
                        "reason": reason
                    })
                    
            mail.logout()
            
        except Exception as e:
            logger.error(f"Error checking email tracker: {e}")
            errors.append(str(e))
            
        return AgentResult(
            success=len(errors) == 0,
            data={
                "emails_checked": len(emails_parsed),
                "updates_detected": updates_detected,
                "errors": errors
            }
        )

    def _classify_email_with_groq(self, client: Groq, sender: str, subject: str, body: str, active_apps: List[dict]) -> dict:
        """
        Sends the email content and active application metadata to Groq Llama for matching & classification.
        """
        # Format active applications list for LLM context
        apps_context = []
        for app in active_apps:
            job = app.get("jobs", {})
            apps_context.append({
                "application_id": app["id"],
                "job_title": job.get("title"),
                "company_name": job.get("company"),
                "current_status": app["status"]
            })
            
        prompt = f"""You are an email parser for an AI Job Agent tracking job application status.
Here is the list of active applications you are tracking:
{json.dumps(apps_context, indent=2)}

Analyze the following incoming email:
Sender: {sender}
Subject: {subject}
Body:
{body}

Determine:
1. Does this email correspond to one of the active applications? Focus on matching the company name or job title.
2. If it matches, classify the new status of the application based on the email content:
   - 'interview': The email invites the candidate to an interview, introductory call, coding assessment, or schedule a meet.
   - 'rejected': The email states the candidate was not selected, they are moving forward with others, the role is filled/closed, or they appreciate the interest but cannot proceed.
   - 'offer': The email mentions extending a job offer, contract proposal, or salary negotiation details.
   - 'applied': The email is just a confirmation receipt ("Thank you for applying", "We received your application").
   - 'no_change': The email is spam, an unrelated newsletter, or doesn't represent a status update.

Format your output STRICTLY as a JSON object. Do not include markdown code block tags or additional conversational text. 
Expected Keys:
{{
  "matched": true/false,
  "application_id": "matched_application_id_or_null",
  "status": "interview/rejected/offer/applied/no_change",
  "reason": "Brief reason explaining the match and status choice"
}}
"""
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            response_content = chat_completion.choices[0].message.content.strip()
            return json.loads(response_content)
        except Exception as e:
            logger.error(f"Failed to parse email with Groq: {e}")
            return {"matched": False, "application_id": None, "status": "no_change", "reason": str(e)}
