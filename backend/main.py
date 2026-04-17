import sys
import asyncio

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Fix for Playwright on Windows: Force ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import os
import traceback
import json
import ipaddress
import socket
from urllib.parse import urlparse

# Import our scraper modules
from scraper.browser import BrowserManager
from scraper.auth import AuthManager
from scraper.extractor import ContentExtractor

app = FastAPI(title="Training Hub Builder API")

# Configure CORS for frontend communication
# In production, update ALLOWED_ORIGINS via environment variable
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

import mimetypes
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("audio/mpeg", ".mp3")

from fastapi.staticfiles import StaticFiles
if not os.path.exists("media"):
    os.makedirs("media")
app.mount("/media", StaticFiles(directory="media"), name="media")
# Security: scraped_data is NOT served as a public static directory.
# It contains scraped page content and course data — access it only via API endpoints.
# (Removed: app.mount("/scraped_data", ...))

# Global State
browser_manager = BrowserManager()
auth_manager = AuthManager()
extractor = ContentExtractor()

# Request Models
class LaunchRequest(BaseModel):
    headless: bool = False
    use_auth: bool = False

class NavigateRequest(BaseModel):
    # Security: cap URL length to prevent oversized inputs
    url: str = Field(..., max_length=2048)

# --- URL Validation Helper ---
def _is_private_ip(hostname: str) -> bool:
    """
    Resolves hostname to IP(s) and checks if any are private/reserved.
    Catches DNS rebinding by resolving at validation time.
    Security: prevents SSRF by blocking all RFC-1918, loopback, link-local,
    and other reserved ranges including IPv4-mapped IPv6 addresses.
    """
    try:
        # Resolve all addresses for the hostname
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            # ipaddress covers loopback, private, link-local, reserved, multicast, etc.
            if (ip.is_loopback or ip.is_private or ip.is_link_local or
                    ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return True
    except (socket.gaierror, ValueError):
        # Can't resolve — treat as invalid/blocked to fail safe
        return True
    return False


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validates a URL to prevent SSRF attacks.
    Returns (is_valid, error_message or cleaned_url)
    """
    # Add protocol if missing
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Only allow http and https schemes
    if parsed.scheme not in ('http', 'https'):
        return False, f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."

    # Block file:// style URLs that might slip through
    if not parsed.netloc:
        return False, "Invalid URL: missing host"

    hostname = parsed.hostname or ''
    if not hostname:
        return False, "Invalid URL: missing host"

    # Security: resolve hostname to actual IPs and reject private/reserved ranges.
    # This also defeats DNS rebinding — we check at request time.
    if _is_private_ip(hostname):
        return False, "Access to internal/private addresses is not allowed"

    return True, url


@app.get("/")
def read_root():
    return {
        "status": "ok", 
        "message": "Training Hub Builder Backend Live"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Browser Control Endpoints ---

async def ensure_browser(headless: bool = True, use_auth: bool = True):
    """Launches the browser lazily if nothing is up yet.

    Hosted runtimes (Render) can evict a long-lived browser subprocess between
    requests; if that happens, the explicit /launch call the frontend made
    earlier is effectively gone. This lets navigate/scrape self-heal instead
    of bubbling up "Browser not started" to the user.
    """
    if browser_manager.is_ready:
        return
    auth_path = auth_manager.storage_path if (use_auth and auth_manager.exists()) else None
    print(f"[ensure_browser] auto-launching (headless={headless}, auth={'yes' if auth_path else 'no'})")
    await browser_manager.launch(headless=headless, auth_state_path=auth_path)

@app.get("/api/browser/status")
async def browser_status():
    return {"ready": browser_manager.is_ready}

@app.post("/api/browser/launch")
async def launch_browser(pkt: LaunchRequest):
    try:
        # Always close first so we don't leak a stale browser or page reference.
        await browser_manager.close()

        auth_path = auth_manager.storage_path if pkt.use_auth else None
        print(f"Launching browser (Headless: {pkt.headless}, Auth: {auth_path})")
        await browser_manager.launch(headless=pkt.headless, auth_state_path=auth_path)
        return {"status": "launched", "auth_loaded": bool(auth_path and auth_manager.exists())}
    except Exception as e:
        with open("error.log", "a") as f:
            traceback.print_exc(file=f)
        print("ERROR IN LAUNCH:", str(e))
        traceback.print_exc()
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to launch browser")

@app.post("/api/browser/navigate")
async def navigate(pkt: NavigateRequest):
    try:
        await ensure_browser()
        # Validate URL to prevent SSRF attacks
        is_valid, result = validate_url(pkt.url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=result)

        url = result  # result contains the cleaned URL if valid
        print(f"Navigating to {url}")
        await browser_manager.page.goto(url, wait_until="networkidle", timeout=30000)
        return {"status": "navigated", "url": url}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        with open("error.log", "a") as f:
            traceback.print_exc(file=f)
        print("ERROR IN NAVIGATE:", str(e))
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Navigation failed")

@app.post("/api/browser/scrape")
async def scrape_page():
    try:
        await ensure_browser()
        print("Scraping page...")
        data = await extractor.extract_page(browser_manager.page)
        
        # Save data to file for AI processing
        output_path = os.path.join("scraped_data", "latest_scrape.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Scraped data saved to {output_path}")
        # Security: don't leak internal filesystem path in response
        return {"status": "scraped", "data": data}
    except Exception as e:
        with open("error.log", "a") as f:
            traceback.print_exc(file=f)
        print("ERROR IN SCRAPE:", str(e))
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Scrape failed")

@app.get("/api/browser/snapshot")
async def get_snapshot():
    output_path = os.path.join("scraped_data", "latest_scrape.json")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="No snapshot found")
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "loaded", "data": data}
    except Exception as e:
        print("ERROR IN SNAPSHOT:", str(e))
        traceback.print_exc()
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to load snapshot")

@app.post("/api/browser/save-auth")
async def save_auth():
    if not browser_manager.context:
        raise HTTPException(status_code=400, detail="Browser context not available")
    try:
        await auth_manager.save_state(browser_manager.context)
        # Security: don't expose server-side filesystem paths to the client
        return {"status": "saved"}
    except Exception as e:
        with open("error.log", "a") as f:
            traceback.print_exc(file=f)
        print("ERROR IN SAVE-AUTH:", str(e))
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to save session")

@app.post("/api/browser/close")
async def close_browser():
    await browser_manager.close()
    return {"status": "closed"}

@app.get("/api/browser/screenshot/{filename}")
async def get_screenshot(filename: str):
    """Serve a screenshot file with path traversal protection."""
    # Security: reject any path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    # Security: only serve .png screenshot files
    if not filename.endswith(".png") or not filename.startswith("screenshot_"):
        raise HTTPException(status_code=400, detail="Invalid screenshot filename")
    filepath = os.path.join("scraped_data", filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(filepath, media_type="image/png")

# --- AI Content Generation Endpoints ---

from ai.planner import CoursePlanner
planner = CoursePlanner()

@app.post("/api/ai/plan")
async def generate_plan():
    scrape_path = os.path.join("scraped_data", "latest_scrape.json")
    if not os.path.exists(scrape_path):
        raise HTTPException(status_code=400, detail="No scraped data found. Run scraper first.")
    
    try:
        if not os.environ.get("GROQ_API_KEY"):
             # For dev/demo without key, return mock data or raise clear error
             print("WARNING: No GROQ_API_KEY found. Using mock response.")
             # raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY")
             return {
                 "status": "planned",
                 "plan": {
                     "course_title": "Mock Generated Course",
                     "description": "This is a placeholder because no API key was found.",
                     "modules": [
                         {
                             "title": "Module 1: Getting Started",
                             "lessons": [{"title": "Welcome", "description": "Intro"}]
                         }
                     ]
                 }
             }

        plan = await planner.generate_outline(scrape_path)
        
        # Save plan
        plan_path = os.path.join("scraped_data", "course_plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        return {"status": "planned", "plan": plan}
    except Exception as e:
        traceback.print_exc()
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to generate course plan")

@app.get("/api/course/current")
def get_current_course():
    plan_path = os.path.join("scraped_data", "course_plan.json")
    if not os.path.exists(plan_path):
        raise HTTPException(status_code=404, detail="No course plan found")
    
    with open(plan_path, "r", encoding="utf-8") as f:
        return json.load(f)

class LessonRequest(BaseModel):
    # Security: enforce max lengths to prevent oversized payloads
    lesson_title: str = Field(..., max_length=500)
    module_title: str = Field(..., max_length=500)

@app.post("/api/ai/lesson")
async def generate_lesson_content(req: LessonRequest):
    # Load context from scrape
    scrape_path = os.path.join("scraped_data", "latest_scrape.json")
    if not os.path.exists(scrape_path):
        raise HTTPException(status_code=400, detail="No source data found")
        
    with open(scrape_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    text_content = data.get("text_content", "")
    
    try:
        content = await planner.generate_lesson(req.lesson_title, text_content)
        return {"status": "generated", "content": content}
    except Exception as e:
        traceback.print_exc()
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to generate lesson content")

class QuizRequest(BaseModel):
    # Security: cap content length — backend already slices to 4000 chars but validate at ingress
    lesson_content: str = Field(..., max_length=50000)

@app.post("/api/ai/quiz")
async def generate_quiz(req: QuizRequest):
    try:
        questions = await planner.generate_quiz(req.lesson_content)
        return {"status": "generated", "questions": questions}
    except Exception as e:
        traceback.print_exc()
        # Security: don't leak internal error details to client
        raise HTTPException(status_code=500, detail="Failed to generate quiz")

from media.video_maker import generate_simple_video
import re as _re
import uuid as _uuid
import threading

# In-memory video job tracker
video_jobs: dict[str, dict] = {}

class VideoRequest(BaseModel):
    # Security: enforce max lengths to prevent oversized payloads
    title: str = Field(..., max_length=500)
    text_content: str = Field(..., max_length=50000)

def _run_video_job(job_id: str, title: str, script: str, output_path: str, video_filename: str):
    """Runs video generation in a background thread and updates job status."""
    try:
        video_jobs[job_id]["status"] = "processing"
        generate_simple_video(title, script, output_path)
        video_jobs[job_id]["status"] = "complete"
        video_jobs[job_id]["video_url"] = f"/media/{video_filename}"
        print(f"[JOB {job_id}] Video complete: /media/{video_filename}")
    except Exception as e:
        print(f"[JOB {job_id}] Video failed: {e}")
        traceback.print_exc()
        raw_msg = str(e)
        if "insufficient_quota" in raw_msg or "billing_hard_limit" in raw_msg:
            detail = "OpenAI quota/billing limit reached. Check your usage at platform.openai.com/usage and try again after your limit resets."
        else:
            detail = "Video generation failed"
        video_jobs[job_id]["status"] = "failed"
        video_jobs[job_id]["detail"] = detail

@app.post("/api/ai/video")
async def create_lesson_video(req: VideoRequest):
    # Security: sanitize title for use in filename — strip non-alphanumeric chars,
    # use a UUID suffix to avoid collisions and prevent path traversal via crafted titles
    safe_slug = _re.sub(r'[^a-zA-Z0-9_-]', '_', req.title)[:40]
    job_id = _uuid.uuid4().hex[:12]
    video_filename = f"video_{safe_slug}_{job_id}.mp4"
    output_path = os.path.join("media", video_filename)

    # Ensure media dir exists
    if not os.path.exists("media"):
        os.makedirs("media")

    script = req.text_content[:2500] if len(req.text_content) > 2500 else req.text_content

    # Register job and launch in background thread
    video_jobs[job_id] = {"status": "queued", "title": req.title}
    thread = threading.Thread(target=_run_video_job, args=(job_id, req.title, script, output_path, video_filename), daemon=True)
    thread.start()

    print(f"[JOB {job_id}] Video job started for: {req.title}")
    return {"status": "accepted", "job_id": job_id}

@app.get("/api/ai/video/status/{job_id}")
async def get_video_status(job_id: str):
    # Security: validate job_id format (hex only, 12 chars)
    if not _re.fullmatch(r'[0-9a-f]{12}', job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    job = video_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Railway provides PORT env var; fallback to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    # reload=False is required on Windows for Playwright to work with asyncio loop policy
    uvicorn.run("main:app", host=host, port=port, reload=False, loop="asyncio")

