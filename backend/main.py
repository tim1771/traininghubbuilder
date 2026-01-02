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
from pydantic import BaseModel
import uvicorn
import os
import traceback
import json # Global import

# Import our scraper modules
from scraper.browser import BrowserManager
from scraper.auth import AuthManager
from scraper.extractor import ContentExtractor

app = FastAPI(title="Training Hub Builder API")

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
if not os.path.exists("media"):
    os.makedirs("media")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Global State
browser_manager = BrowserManager()
auth_manager = AuthManager()
extractor = ContentExtractor()

# Request Models
class LaunchRequest(BaseModel):
    headless: bool = False
    use_auth: bool = False

class NavigateRequest(BaseModel):
    url: str

@app.get("/")
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

@app.post("/api/browser/launch")
async def launch_browser(pkt: LaunchRequest):
    try:
        # If running, close first? Or allow reuse? For now, close if exists.
        if browser_manager.browser:
            await browser_manager.close()

        auth_path = auth_manager.storage_path if pkt.use_auth else None
        print(f"Launching browser (Headless: {pkt.headless}, Auth: {auth_path})")
        await browser_manager.launch(headless=pkt.headless, auth_state_path=auth_path)
        return {"status": "launched", "auth_loaded": bool(auth_path and auth_manager.exists())}
    except Exception as e:
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        print("ERROR IN LAUNCH:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/browser/navigate")
async def navigate(pkt: NavigateRequest):
    if not browser_manager.page:
        raise HTTPException(status_code=400, detail="Browser not started")
    try:
        # Ensure URL has protocol
        url = pkt.url
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
            
        print(f"Navigating to {url}")
        await browser_manager.page.goto(url, wait_until="networkidle", timeout=30000)
        return {"status": "navigated", "url": url}
    except Exception as e:
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/browser/scrape")
async def scrape_page():
    if not browser_manager.page:
        raise HTTPException(status_code=400, detail="Browser not started")
    try:
        print("Scraping page...")
        data = await extractor.extract_page(browser_manager.page)
        
        # Save data to file for AI processing
        import json
        output_path = os.path.join("scraped_data", "latest_scrape.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Scraped data saved to {output_path}")
        return {"status": "scraped", "data": data, "saved_to": output_path}
    except Exception as e:
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/browser/save-auth")
async def save_auth():
    if not browser_manager.context:
        raise HTTPException(status_code=400, detail="Browser context not available")
    try:
        path = await auth_manager.save_state(browser_manager.context)
        return {"status": "saved", "path": path}
    except Exception as e:
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/browser/close")
async def close_browser():
    await browser_manager.close()
    return {"status": "closed"}

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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/course/current")
def get_current_course():
    plan_path = os.path.join("scraped_data", "course_plan.json")
    if not os.path.exists(plan_path):
        raise HTTPException(status_code=404, detail="No course plan found")
    
    with open(plan_path, "r", encoding="utf-8") as f:
        return json.load(f)

class LessonRequest(BaseModel):
    lesson_title: str
    module_title: str

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
        raise HTTPException(status_code=500, detail=str(e))

class QuizRequest(BaseModel):
    lesson_content: str

@app.post("/api/ai/quiz")
async def generate_quiz(req: QuizRequest):
    try:
        questions = await planner.generate_quiz(req.lesson_content)
        return {"status": "generated", "questions": questions}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from media.video_maker import generate_simple_video

class VideoRequest(BaseModel):
    title: str
    text_content: str

@app.post("/api/ai/video")
async def create_lesson_video(req: VideoRequest):
    video_filename = f"video_{hash(req.title)}.mp4"
    output_path = os.path.join("media", video_filename)
    
    # Ensure media dir exists
    if not os.path.exists("media"):
        os.makedirs("media")

    try:
        # Use more content for longer videos (aim for ~3 minutes)
        # Average TTS speed is ~150 words per minute, so 450 words = 3 minutes
        # Roughly 2000-2500 characters = 400-500 words
        script = req.text_content[:2500] if len(req.text_content) > 2500 else req.text_content
        
        # Run in threadpool to avoid blocking async loop with heavy processing
        await asyncio.to_thread(generate_simple_video, req.title, script, output_path)
        
        # Return URL (we need to mount static files)
        return {"status": "created", "video_url": f"/media/{video_filename}"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # reload=False is required on Windows for Playwright to work with asyncio loop policy
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, loop="asyncio")

