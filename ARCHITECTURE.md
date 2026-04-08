# Training Hub Builder - Architecture & Overview

## What It Does

Training Hub Builder is a full-stack application that turns **any website** into a complete training course. You paste a URL, the system scrapes the site, and AI generates a structured curriculum with lessons, quizzes, practice simulations, and narrated videos — all presented in an interactive learning platform.

---

## High-Level Flow

```
User inputs URL
      |
      v
Playwright scrapes the page (text, screenshots, interactive elements)
      |
      v
Groq AI (Llama 3.3-70b) analyzes content and generates a course outline
      |
      v
User browses modules/lessons in a course viewer
      |
      v
On-demand per lesson:
  - Markdown lesson content (Groq)
  - Quiz questions (Groq)
  - AI-narrated video (OpenAI GPT-4 + TTS + DALL-E)
  - Interactive practice simulation (click-to-learn hotspots)
```

---

## Tech Stack

| Layer        | Technology                          | Purpose                                      |
|--------------|-------------------------------------|----------------------------------------------|
| Frontend     | Next.js 16.1.1, React 19, TypeScript | App shell, routing, UI                       |
| Styling      | Tailwind CSS v4                     | Utility-first CSS, dark mode                 |
| Backend      | FastAPI (Python)                    | REST API, orchestration                      |
| Browser      | Playwright (Chromium)               | Web scraping, screenshots, auth persistence  |
| AI - Text    | Groq (Llama 3.3-70b)               | Course plans, lessons, quizzes               |
| AI - Media   | OpenAI (GPT-4, DALL-E 3, TTS)      | Video scripts, presenter images, narration   |
| Video        | MoviePy 1.0.3 + Pillow             | Slide composition, Ken Burns effects, export |
| Deployment   | Railway (backend), Netlify (frontend) | Hosting & CI/CD                            |

---

## Project Structure

```
training-hub-builder/
|
+-- backend/
|   +-- main.py                  # FastAPI app, all endpoints, CORS, security
|   +-- requirements.txt         # Python dependencies
|   +-- Dockerfile               # Production container (python:3.11-slim + Chromium)
|   +-- railway.toml             # Railway deployment config
|   +-- launch.json              # VS Code debug config
|   +-- navigate.json            # Legacy example config
|   +-- refresh_snapshot.py      # Utility to refresh cached scrape data
|   |
|   +-- ai/
|   |   +-- planner.py           # CoursePlanner class: outline, lesson, quiz generation
|   |
|   +-- scraper/
|   |   +-- browser.py           # BrowserManager: Playwright lifecycle
|   |   +-- auth.py              # AuthManager: persist/load login state
|   |   +-- extractor.py         # ContentExtractor: page text, elements, screenshots
|   |
|   +-- media/
|   |   +-- video_maker.py       # Full video pipeline: script, TTS, slides, compose
|   |
|   +-- scraped_data/
|       +-- latest_scrape.json   # Most recent page extraction
|       +-- course_plan.json     # Current generated curriculum
|       +-- screenshot_*.png     # Page screenshots
|
+-- frontend/
|   +-- app/
|   |   +-- layout.tsx           # Root layout, fonts, metadata
|   |   +-- page.tsx             # Home page: status check + URL input
|   |   +-- globals.css          # CSS variables, dark mode defaults
|   |   +-- course/
|   |       +-- viewer/
|   |       |   +-- page.tsx     # Course outline viewer (modules/lessons list)
|   |       +-- lesson/
|   |           +-- view/
|   |               +-- page.tsx # Lesson viewer: theory, quiz, practice, video
|   |
|   +-- components/
|   |   +-- UrlInput.tsx         # URL entry, scrape controls, workflow buttons
|   |   +-- Simulation.tsx       # Practice sandbox: hotspot click-to-learn interface
|   |
|   +-- next.config.ts           # API proxy rewrites, 10-min proxy timeout
|   +-- package.json             # Dependencies and scripts
|   +-- tsconfig.json            # TypeScript config (strict, ES2017)
|   +-- postcss.config.mjs       # Tailwind PostCSS plugin
|
+-- netlify.toml                 # Netlify build config for frontend
```

---

## Backend API Endpoints

### Browser Control

| Method | Endpoint                            | What It Does                                              |
|--------|-------------------------------------|-----------------------------------------------------------|
| POST   | `/api/browser/launch`               | Starts Playwright browser (headless or visible)           |
| POST   | `/api/browser/navigate`             | Navigates to URL (with SSRF validation)                   |
| POST   | `/api/browser/scrape`               | Extracts page content, screenshots, interactive elements  |
| GET    | `/api/browser/snapshot`             | Returns cached scrape data from disk                      |
| POST   | `/api/browser/save-auth`            | Saves browser cookies/session for authenticated scraping  |
| POST   | `/api/browser/close`               | Closes browser, frees resources                           |
| GET    | `/api/browser/screenshot/{file}`    | Serves a screenshot PNG (path-traversal protected)        |

### AI Content Generation

| Method | Endpoint              | What It Does                                           |
|--------|-----------------------|--------------------------------------------------------|
| POST   | `/api/ai/plan`        | Generates course curriculum from scraped content       |
| POST   | `/api/ai/lesson`      | Generates Markdown lesson for a specific topic         |
| POST   | `/api/ai/quiz`        | Generates 3 multiple-choice questions from lesson text |
| POST   | `/api/ai/video`       | Generates narrated MP4 video with AI presenter         |

### Course Data

| Method | Endpoint               | What It Does                         |
|--------|------------------------|--------------------------------------|
| GET    | `/api/course/current`  | Returns the current course plan JSON |

### Health

| Method | Endpoint   | What It Does    |
|--------|------------|-----------------|
| GET    | `/`        | Status check    |
| GET    | `/health`  | Health endpoint |

---

## Data Structures

### Scraped Page (`scraped_data/latest_scrape.json`)

```json
{
  "title": "Page Title",
  "url": "https://example.com",
  "text_content": "Full cleaned text from the page...",
  "screenshot": "scraped_data/screenshot_1712345678.png",
  "viewport": { "width": 1280, "height": 720 },
  "interactive_elements": [
    {
      "text": "Sign Up",
      "type": "button",
      "x": 450, "y": 320,
      "width": 120, "height": 40
    }
  ]
}
```

- **text_content**: HTML stripped of scripts/styles, extracted via BeautifulSoup
- **interactive_elements**: Up to 100 visible links, buttons, and inputs with bounding boxes
- **screenshot**: Full-page PNG capture

### Course Plan (`scraped_data/course_plan.json`)

```json
{
  "course_title": "Mastering Example.com",
  "description": "A comprehensive course on...",
  "modules": [
    {
      "title": "Getting Started",
      "lessons": [
        {
          "title": "Introduction to the Platform",
          "description": "Learn the basics of navigating..."
        }
      ]
    }
  ]
}
```

### Quiz Question (API response)

```json
{
  "question": "What is the primary purpose of...?",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_index": 2
}
```

---

## Core Modules — How They Work

### Scraper Pipeline (`backend/scraper/`)

**BrowserManager** (`browser.py`)
- Wraps Playwright's Chromium browser
- Viewport: 1280x720, spoofed Chrome/Windows user-agent
- Supports headless (automated) and headed (interactive login) modes

**AuthManager** (`auth.py`)
- Saves/loads browser context state (cookies, localStorage) to `auth_state.json`
- Allows scraping behind login walls — user logs in once via headed mode, sessions persist

**ContentExtractor** (`extractor.py`)
- Strips `<script>` and `<style>` tags, extracts clean text via BeautifulSoup
- Captures full-page screenshot
- Queries DOM for interactive elements (`a`, `button`, `input`, `select`, `textarea`) and records their text + bounding boxes
- Returns top 100 most visible elements (filtered by visibility and size)

### AI Pipeline (`backend/ai/`)

**CoursePlanner** (`planner.py`)
- **`generate_outline()`**: Sends first 15,000 chars of scraped text to Groq with a curriculum-design prompt. Uses JSON response mode. Returns structured modules/lessons.
- **`generate_lesson()`**: Takes a lesson title + first 8,000 chars of page context. Groq generates Markdown with headers, code blocks, lists. Post-processed to ensure all sentences end with punctuation.
- **`generate_quiz()`**: Takes lesson content (up to 4,000 chars), Groq returns 3 multiple-choice questions in JSON format.
- All three methods fall back to mock data if `GROQ_API_KEY` is missing.

### Video Pipeline (`backend/media/`)

**`generate_simple_video()`** (`video_maker.py`)

This is the most complex pipeline. It produces an MP4 with narrated slides and an AI presenter overlay:

```
Step 1: Script
  Raw lesson text --> GPT-4 rewrites into engaging narration script
  Markdown stripped, cleaned for TTS

Step 2: Audio
  Script --> OpenAI TTS (voice: "shimmer") --> MP3 file
  Fallback: gTTS if OpenAI fails

Step 3: Slides
  Title slide (gradient background, centered text, 3 sec)
  Screenshot slides (from scraped page captures)
  Text summary slides (colorful backgrounds)
  Ken Burns zoom-in effect applied to each (0.03-0.05 ratio)

Step 4: Presenter
  DALL-E 3 generates a professional presenter headshot (cached)
  Circular mask applied
  Composited bottom-right on every slide

Step 5: Compose
  Clips concatenated to match audio duration
  MoviePy composites video + audio
  Export: H.264, AAC, 24fps, ultrafast preset
  Output: /media/{sanitized_title}.mp4
```

Timeout: 10 minutes. Videos are served from the mounted `/media` directory.

---

## Frontend Pages — What Each Does

### Home Page (`/`)
- **StatusCheck**: Pings backend `/` endpoint, shows green/red connection indicator
- **UrlInput**: The main control panel
  - Text input for target URL
  - "Auto-Build Course" button: headless scrape + auto-generate (one click)
  - "Teach / Login" button: opens visible browser for manual authentication
  - "Save Session" button: persists auth cookies for future scrapes
  - "Generate Curriculum" button: appears after successful scrape
  - Redirects to `/course/viewer` when curriculum is ready

### Course Viewer (`/course/viewer`)
- Fetches course plan from `/api/course/current`
- Displays course title, description, and module/lesson tree
- Each lesson links to `/course/lesson/view?title=...&module=...`

### Lesson View (`/course/lesson/view`)
- Most feature-rich page in the app
- **Collapsible sidebar**: full course outline, current lesson highlighted, completion checkmarks
- **Two tabs**:
  - **Theory**: Markdown lesson (react-markdown), video player, quiz section
  - **Practice**: Interactive simulation with hotspot clicking
- **Video generation**: "Create Video" button triggers the full video pipeline, displays player on completion
- **Quiz**: "Generate Quiz" button fetches 3 questions, interactive answer selection, score calculation
- **Progress**: Stored in `localStorage` under key `training_hub_progress`, lessons marked complete after quiz or practice

### Simulation Component
- Renders the scraped page screenshot as a backdrop
- Overlays clickable hotspots based on extracted interactive elements
- Picks a random element as a "task" (e.g., "Click the Sign Up button")
- Detects clicks via coordinate mapping (display coords → original image coords)
- Shows success/failure animations, skip button for next task

---

## User Workflows

### Workflow 1: One-Click Course Creation (No Login Needed)

```
1. User types URL into input field
2. Clicks "Auto-Build Course"
3. Backend launches headless browser, navigates, scrapes
4. "Generate Curriculum" button appears
5. User clicks it -> Groq generates course plan
6. Redirected to Course Viewer
7. User clicks any lesson -> content generated on demand
```

### Workflow 2: Scraping Behind a Login Wall

```
1. User types URL, clicks "Teach / Login"
2. Visible Chromium window opens
3. User manually logs into the site
4. Clicks "Save Session" in the app
5. Auth cookies saved to auth_state.json
6. Now clicks "Auto-Build Course" — scrapes with saved auth
7. Proceeds as Workflow 1 from step 4
```

### Workflow 3: Lesson Consumption

```
1. User opens a lesson from the Course Viewer
2. Lesson markdown generated via Groq and rendered
3. User can:
   a. Read the theory content
   b. Click "Create Video" for AI-narrated video
   c. Click "Generate Quiz" to test knowledge
   d. Switch to Practice tab for interactive simulation
5. Completing a quiz or practice task marks the lesson done
```

---

## Security Measures

### SSRF Prevention
- All user-supplied URLs validated before navigation
- Resolves hostname to IP, blocks private/reserved ranges:
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918)
  - `127.0.0.0/8` (loopback)
  - `169.254.0.0/16` (link-local)
  - Multicast and reserved ranges
- Only `http://` and `https://` schemes allowed
- Max URL length: 2048 characters

### Path Traversal Protection
- Screenshot filenames must match pattern: starts with `screenshot_`, ends with `.png`
- Characters `..`, `/`, `\` rejected in filenames

### Input Size Limits
- Lesson title: max 500 characters
- Module title: max 500 characters
- Lesson content (for quiz/video): max 50KB
- Enforced via Pydantic `Field` validators

### Error Handling
- Internal paths and tracebacks never exposed to the client
- Errors logged server-side (`error.log`)
- Generic messages returned to frontend
- OpenAI quota errors surfaced with billing context

### CORS
- Allowed origins configurable via `ALLOWED_ORIGINS` env var
- Defaults to `http://localhost:3000` for local dev

---

## Environment Variables

### Backend

| Variable          | Required | Purpose                                        |
|-------------------|----------|------------------------------------------------|
| `GROQ_API_KEY`    | Yes*     | Groq API for course plans, lessons, quizzes    |
| `OPENAI_API_KEY`  | No**     | OpenAI for video scripts, TTS, DALL-E presenter |
| `ALLOWED_ORIGINS` | No       | CORS origins (default: `http://localhost:3000`) |
| `PORT`            | No       | Server port (default: `8000`, set by Railway)  |

\* Falls back to mock data if missing  
\*\* Video generation disabled if missing

### Frontend

| Variable                  | Required | Purpose                                      |
|---------------------------|----------|----------------------------------------------|
| `NEXT_PUBLIC_BACKEND_URL` | No       | Backend URL (default: `http://127.0.0.1:8000`) |

---

## Deployment

### Backend (Railway)

- **Dockerfile**: `python:3.11-slim` base, installs Chromium deps, Playwright, Python packages
- **Health check**: `GET /health` (30s timeout)
- **Restart policy**: on failure, max 3 retries
- Requires `GROQ_API_KEY` and `OPENAI_API_KEY` set in Railway dashboard

### Frontend (Netlify)

- **Build**: `npm run build` from `frontend/` directory
- **Plugin**: `@netlify/plugin-nextjs` for SSR support
- **Publish**: `.next/` directory
- Requires `NEXT_PUBLIC_BACKEND_URL` pointed at Railway backend URL

### Local Development

```bash
# Terminal 1 — Backend
cd backend
source venv/Scripts/activate   # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
# Opens at http://localhost:3000
```

---

## Dependencies

### Backend (`requirements.txt`)

| Package           | Purpose                        |
|-------------------|--------------------------------|
| fastapi           | Web framework                  |
| uvicorn           | ASGI server                    |
| playwright        | Browser automation             |
| moviepy 1.0.3     | Video composition              |
| beautifulsoup4    | HTML parsing                   |
| requests          | HTTP client                    |
| python-multipart  | Form data handling             |
| jinja2            | Templating                     |
| python-dotenv     | .env file loading              |
| openai            | OpenAI API (GPT-4, DALL-E, TTS)|
| groq              | Groq API (Llama 3.3-70b)      |

### Frontend (`package.json`)

| Package          | Purpose                     |
|------------------|-----------------------------|
| next 16.1.1      | React framework (App Router)|
| react 19.2.3     | UI library                  |
| react-dom 19.2.3 | DOM rendering               |
| react-markdown   | Markdown rendering          |
| tailwindcss v4   | Utility CSS                 |
| typescript 5     | Type safety                 |

---

## Current Status & Roadmap

### Implemented
- Web scraping with headless and interactive modes
- Authentication persistence for login-walled sites
- AI course outline generation
- Markdown lesson generation with punctuation cleanup
- 3-question quiz generation per lesson
- AI video generation (script + TTS + slides + presenter + Ken Burns)
- Interactive practice simulation with hotspot detection
- Progress tracking via localStorage
- Dark mode UI
- SSRF protection and input validation
- Docker + Railway + Netlify deployment

### Planned / In Progress
- Sora v2 video clip integration (framework exists in `video_maker.py`)
- Course JSON export/download
- SCORM compliance for LMS import
- Human review workflow for generated content
- Progress analytics and engagement tracking
- Multi-language support
- Adaptive learning paths based on quiz scores
- LMS platform integrations
- Custom branding per course
- Collaborative course editing
