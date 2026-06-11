import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from datetime import datetime, date
from db import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_ID = "00000000-0000-0000-0000-000000000000"

def send_daily_digest() -> bool:
    """
    Assembles database metrics and sends a daily HTML summary email to the user.
    """
    logger.info("Assembling Daily Digest Email...")
    
    # 1. Fetch SMTP Credentials
    try:
        settings_res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
        if not settings_res.data:
            logger.warning("System settings not found in database. Skipping digest email.")
            return False
        db_settings = settings_res.data[0]
    except Exception as e:
        logger.error(f"Failed to load settings for digest email: {e}")
        return False

    gmail_email = db_settings.get("gmail_email")
    gmail_app_password = db_settings.get("gmail_app_password")

    if not gmail_email or not gmail_app_password or gmail_email == "" or gmail_app_password == "":
        logger.info("Gmail credentials not configured. Skipping daily digest dispatch.")
        return False

    # 2. Gather Stats
    try:
        # Fetch stats today
        today_str = date.today().isoformat()
        
        # Scouted today
        jobs_res = supabase.table("jobs").select("id, title, company, source, matches(score)").gte("scraped_at", today_str).execute()
        jobs_today = jobs_res.data or []
        
        # High matches today
        high_matches = []
        for j in jobs_today:
            match = j.get("matches", {})
            if isinstance(match, list) and match:
                match = match[0]
            score = match.get("score", 0.0) if match else 0.0
            if score >= 0.8:
                high_matches.append(j)

        # Applications status breakdown
        apps_res = supabase.table("applications").select("status").execute()
        apps = apps_res.data or []
        
        counts = {'reviewing': 0, 'applied': 0, 'interview': 0, 'offer': 0, 'rejected': 0}
        for app in apps:
            status = app.get("status")
            if status in counts:
                counts[status] += 1

        # Email updates today
        events_res = supabase.table("email_events").select("*, applications(jobs(company))").execute()
        events_today = []
        # Filter email events parsed today in memory to keep it simple
        for ev in (events_res.data or []):
            try:
                # Format: "2026-06-11T12:00:00+00:00"
                received_date = ev.get("received_at", "").split("T")[0]
                if received_date == today_str:
                    events_today.append(ev)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Failed to gather digest stats: {e}")
        return False

    # 3. Build HTML Body
    subject = f"AI Job Agent Daily Digest — {datetime.now().strftime('%b %d, %Y')}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background-color: #0b0f19;
                color: #e2e8f0;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 16px;
                padding: 30px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                border-bottom: 1px solid #1f2937;
                padding-bottom: 20px;
                margin-bottom: 25px;
            }}
            .header h1 {{
                font-size: 24px;
                color: #6366f1;
                margin: 0;
                font-weight: 800;
            }}
            .header p {{
                font-size: 12px;
                color: #94a3b8;
                margin: 5px 0 0 0;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 25px;
            }}
            .metric-card {{
                background-color: #030712;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
            }}
            .metric-val {{
                font-size: 22px;
                font-weight: bold;
                color: #f8fafc;
            }}
            .metric-lbl {{
                font-size: 11px;
                color: #94a3b8;
                margin-top: 5px;
            }}
            .section {{
                margin-bottom: 25px;
            }}
            .section-title {{
                font-size: 13px;
                font-weight: bold;
                color: #818cf8;
                text-transform: uppercase;
                letter-spacing: 1px;
                border-left: 3px solid #6366f1;
                padding-left: 8px;
                margin-bottom: 12px;
            }}
            .list-item {{
                background-color: #030712;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 10px 15px;
                margin-bottom: 8px;
                font-size: 13px;
            }}
            .list-item-title {{
                font-weight: bold;
                color: #f1f5f9;
            }}
            .list-item-sub {{
                font-size: 11px;
                color: #64748b;
                margin-top: 2px;
            }}
            .footer {{
                text-align: center;
                font-size: 11px;
                color: #475569;
                border-top: 1px solid #1f2937;
                padding-top: 15px;
                margin-top: 25px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AI JOB AGENT</h1>
                <p>Automated Pipeline Status Report</p>
            </div>
            
            <div class="section-title">Today's Activity Summary</div>
            <div style="margin-bottom: 20px;">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td width="48%" style="padding: 10px; background-color: #030712; border: 1px solid #1f2937; border-radius: 12px; text-align: center;">
                            <span style="font-size: 24px; font-weight: bold; color: #38bdf8;">{len(jobs_today)}</span><br>
                            <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Jobs Scraped</span>
                        </td>
                        <td width="4%"></td>
                        <td width="48%" style="padding: 10px; background-color: #030712; border: 1px solid #1f2937; border-radius: 12px; text-align: center;">
                            <span style="font-size: 24px; font-weight: bold; color: #34d399;">{len(high_matches)}</span><br>
                            <span style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Auto-staged Fit (≥80%)</span>
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">Active Job Funnel</div>
                <table width="100%" style="font-size: 13px; text-align: left; background-color: #030712; border: 1px solid #1f2937; border-radius: 12px; padding: 12px;">
                    <tr>
                        <td style="color: #cbd5e1; padding: 6px 0;">Staged for Review</td>
                        <td style="text-align: right; font-weight: bold; color: #818cf8; padding: 6px 0;">{counts['reviewing']}</td>
                    </tr>
                    <tr>
                        <td style="color: #cbd5e1; padding: 6px 0;">Applications Sent (Applied)</td>
                        <td style="text-align: right; font-weight: bold; color: #38bdf8; padding: 6px 0;">{counts['applied']}</td>
                    </tr>
                    <tr>
                        <td style="color: #cbd5e1; padding: 6px 0;">Active Interviews</td>
                        <td style="text-align: right; font-weight: bold; color: #a78bfa; padding: 6px 0;">{counts['interview']}</td>
                    </tr>
                    <tr>
                        <td style="color: #cbd5e1; padding: 6px 0;">Offers Received</td>
                        <td style="text-align: right; font-weight: bold; color: #34d399; padding: 6px 0;">{counts['offer']}</td>
                    </tr>
                    <tr>
                        <td style="color: #cbd5e1; padding: 6px 0;">Archived / Rejections</td>
                        <td style="text-align: right; font-weight: bold; color: #f43f5e; padding: 6px 0;">{counts['rejected']}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">Staged Matches Staged Today (≥80%)</div>
                {"".join([f'<div class="list-item"><div class="list-item-title">{j["title"]}</div><div class="list-item-sub">{j["company"]} • {j["source"]}</div></div>' for j in high_matches]) if high_matches else '<div style="font-size: 12px; color: #64748b; font-style: italic;">No high compatible matches discovered today.</div>'}
            </div>

            <div class="section">
                <div class="section-title">Gmail Tracker Updates Today</div>
                {"".join([f'<div class="list-item"><div class="list-item-title">Update: {ev.get("detected_status").upper()}</div><div class="list-item-sub">Subject: {ev.get("subject")}</div></div>' for ev in events_today]) if events_today else '<div style="font-size: 12px; color: #64748b; font-style: italic;">No candidate status changes detected in inbox today.</div>'}
            </div>

            <div class="footer">
                This is an automated report generated by the AI Job Agent platform.<br>
                Dashboard: <a href="http://localhost:3000" style="color: #6366f1; text-decoration: none;">http://localhost:3000</a>
            </div>
        </div>
    </body>
    </html>
    """

    # 4. Dispatch Email
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_email
        msg["To"] = gmail_email  # Sends it to himself
        msg.attach(MIMEText(html_content, "html"))

        # Setup SMTP TLS connection
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_email, gmail_app_password)
        server.sendmail(gmail_email, gmail_email, msg.as_string())
        server.quit()
        
        logger.info("[Digest] Successfully sent daily digest report.")
        return True
    except Exception as e:
        logger.error(f"[Digest] Failed to send email digest: {e}")
        return False


def send_application_success_email(job_title: str, company: str, job_url: str) -> bool:
    """
    Sends an immediate email notification when the Playwright bot successfully submits an application.
    """
    try:
        settings_res = supabase.table("system_settings").select("*").eq("id", DEFAULT_SETTINGS_ID).execute()
        if not settings_res.data:
            logger.warning("System settings not found in database. Skipping success email.")
            return False
        db_settings = settings_res.data[0]
    except Exception as e:
        logger.error(f"Failed to load settings for application success email: {e}")
        return False

    gmail_email = db_settings.get("gmail_email")
    gmail_app_password = db_settings.get("gmail_app_password")

    if not gmail_email or not gmail_app_password or gmail_email == "" or gmail_app_password == "":
        logger.info("Gmail credentials not configured. Skipping success email notification.")
        return False

    subject = f"🚀 Application Submitted Successfully: {job_title} at {company}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #0b0f19;
                color: #e2e8f0;
                padding: 20px;
                margin: 0;
            }}
            .container {{
                max-width: 600px;
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 25px;
                margin: 0 auto;
            }}
            .header {{
                border-bottom: 1px solid #1f2937;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                font-size: 20px;
                color: #34d399;
                margin: 0;
            }}
            .details {{
                background-color: #030712;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }}
            .footer {{
                text-align: center;
                font-size: 11px;
                color: #475569;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Autonomous Application Success!</h1>
            </div>
            <p>Your AI Job Agent has successfully submitted a tailored application in the background.</p>
            <div class="details">
                <p style="margin: 5px 0;"><strong>Role:</strong> {job_title}</p>
                <p style="margin: 5px 0;"><strong>Company:</strong> {company}</p>
                <p style="margin: 5px 0;"><strong>Listing URL:</strong> <a href="{job_url}" style="color: #6366f1; text-decoration: none;">View Position</a></p>
                <p style="margin: 5px 0;"><strong>Applied At:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>The application has been moved to the <strong>"Applied"</strong> lane on your Kanban Tracker board.</p>
            <div class="footer">
                Generated automatically by your AI Job Agent.<br>
                Dashboard: <a href="http://localhost:3000" style="color: #6366f1; text-decoration: none;">http://localhost:3000</a>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = gmail_email
        msg["To"] = gmail_email
        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_email, gmail_app_password)
        server.sendmail(gmail_email, gmail_email, msg.as_string())
        server.quit()
        logger.info(f"[Digest] Successfully sent application success notification for {company}.")
        return True
    except Exception as e:
        logger.error(f"[Digest] Failed to send application success email: {e}")
        return False
