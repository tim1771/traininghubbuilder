import os
import glob
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, vfx, VideoFileClip
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import textwrap
from openai import OpenAI
from dotenv import load_dotenv
import requests
from io import BytesIO

import numpy as np # Needed for array manipulation in moviepy usually, but Pillow handles most.

load_dotenv()

def download_image(url, save_path):
    # Security: enforce timeout and size cap to prevent DoS from slow/huge responses
    MAX_BYTES = 20 * 1024 * 1024  # 20 MB
    response = requests.get(url, timeout=30, stream=True)
    response.raise_for_status()
    chunks = []
    received = 0
    for chunk in response.iter_content(chunk_size=65536):
        received += len(chunk)
        if received > MAX_BYTES:
            raise ValueError(f"Image download exceeded size limit ({MAX_BYTES} bytes)")
        chunks.append(chunk)
    img = Image.open(BytesIO(b"".join(chunks)))
    img.save(save_path)
    return save_path

def generate_ai_presenter(client, output_path):
    """Generates a professional AI instructor image using DALL-E 3."""
    try:
        print("Generating AI Presenter with DALL-E 3...")
        response = client.images.generate(
            model="dall-e-3",
            prompt="A professional, friendly tech instructor looking directly at the camera, studio lighting, blurred modern office background, high quality, photorealistic, 4k, head and shoulders shot",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        return download_image(url, output_path)
    except Exception as e:
        print(f"DALL-E Generation failed: {e}")
        return None

def create_text_slide(text, size=(1280, 720), bg_color=(45, 55, 72), text_color=(255, 255, 255), title=None):
    """Generates a colorful slide with text using Pillow."""
    img = Image.new('RGB', size, color=bg_color)
    d = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        body_font = ImageFont.truetype("arial.ttf", 48)
    except IOError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    y_offset = 100
    if title:
        # Gradient header
        for i in range(150):
            alpha = int(255 * (1 - i/150))
            d.rectangle([(0, i), (size[0], i+1)], fill=(99, 102, 241, alpha))
        
        d.text((50, 50), title, fill=(255, 255, 255), font=title_font)
        y_offset += 100

    # Body text
    lines = textwrap.wrap(text, width=40)
    for line in lines[:8]:
        d.text((50, y_offset), line, fill=text_color, font=body_font)
        y_offset += 60

    return img

def create_title_slide(title, size=(1280, 720)):
    """Creates a title slide."""
    img = Image.new('RGB', size, color=(30, 30, 30))
    d = ImageDraw.Draw(img)
    
    # Simple gradient
    for y in range(size[1]):
        r = int(20 + y/20)
        d.rectangle([(0, y), (size[0], y+1)], fill=(r, 30, 50))
    
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
        
    lines = textwrap.wrap(title, width=20)
    y = (size[1] - len(lines)*100)/2
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((size[0]-w)/2, y), line, fill='white', font=font)
        y += 100
    
    return img

def get_screenshots(limit=5):
    """Return the most recently captured screenshots, newest first."""
    screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "scraped_data")
    if not os.path.exists(screenshot_dir):
        return []
    screenshots = glob.glob(os.path.join(screenshot_dir, "screenshot_*.png"))
    screenshots.sort(key=os.path.getmtime, reverse=True)
    return screenshots[:limit]


def fit_to_canvas(img, size=(1280, 720), bg_color=(15, 15, 20)):
    """Fit an image into a fixed canvas without distortion.

    Full-page webpage screenshots are typically very tall (e.g. 1920x5000+).
    We scale by width to preserve aspect; if the scaled image is still taller
    than the canvas we crop to the top viewport (the most informative region).
    Images shorter than the canvas get letterboxed on a dark background.
    """
    canvas_w, canvas_h = size
    src_w, src_h = img.size
    if src_w == 0 or src_h == 0:
        return Image.new("RGB", size, color=bg_color)

    scale = canvas_w / src_w
    new_w = canvas_w
    new_h = max(1, int(round(src_h * scale)))
    scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    if new_h >= canvas_h:
        # Crop to top viewport — that's what a human sees first on a webpage.
        scaled = scaled.crop((0, 0, canvas_w, canvas_h))
        return scaled.convert("RGB")

    canvas = Image.new("RGB", size, color=bg_color)
    y_offset = (canvas_h - new_h) // 2
    canvas.paste(scaled.convert("RGB"), (0, y_offset))
    return canvas


def split_tall_screenshot(img, size=(1280, 720), max_slides=5, bg_color=(15, 15, 20)):
    """Slice a full-page screenshot into a series of viewport-sized slides.

    A one-minute video over a single static frame feels dead; full-page
    screenshots are usually tall enough to show several distinct sections
    (hero, features, pricing, footer, etc). We scale by width, then sample
    evenly-spaced crops down the page so the video "walks" through the page.
    Short screenshots fall back to a single fit_to_canvas slide.
    """
    canvas_w, canvas_h = size
    src_w, src_h = img.size
    if src_w == 0 or src_h == 0:
        return [Image.new("RGB", size, color=bg_color)]

    scale = canvas_w / src_w
    new_w = canvas_w
    new_h = max(1, int(round(src_h * scale)))

    # Not tall enough to benefit from slicing — keep the simpler path.
    if new_h <= int(canvas_h * 1.3):
        return [fit_to_canvas(img, size=size, bg_color=bg_color)]

    scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGB")
    coverage = new_h / canvas_h
    n_slides = min(max_slides, max(2, int(round(coverage))))

    slides = []
    max_start = new_h - canvas_h
    for i in range(n_slides):
        y = int(round((max_start * i) / (n_slides - 1))) if n_slides > 1 else 0
        slides.append(scaled.crop((0, y, canvas_w, y + canvas_h)))
    return slides

def clean_text_for_tts(text):
    import re
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text.strip()

def get_ai_presenter(client):
    """Generates a consistent AI Presenter image if it doesn't exist locally.

    The filenames include "_female_v1" so that bumping the persona (gender,
    style, etc) invalidates the cache automatically without requiring a
    manual file delete on every host.
    """
    presenter_path = "media/presenter_persona_female_v1.png"
    circular_path = "media/presenter_bubble_female_v1.png"
    if os.path.exists(circular_path):
        return circular_path

    if not client:
        return None

    try:
        print("GENERATING CONSISTENT AI PERSONA...")
        prompt = (
            "A professional, friendly female AI tutor assistant, "
            "high-quality photorealistic portrait, wearing business casual, "
            "neutral studio background, looking into camera with a slight smile."
        )
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        # Security: enforce timeout and size cap on AI image download
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        img_data = img_resp.content
        if len(img_data) > 20 * 1024 * 1024:
            raise ValueError("Presenter image exceeded size limit")
        with open(presenter_path, 'wb') as handler:
            handler.write(img_data)

        # Make circular version for overlay
        img = Image.open(presenter_path).convert("RGBA")
        size = (512, 512)
        img = img.resize(size, Image.Resampling.LANCZOS)

        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)

        output = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)

        output.save(circular_path)
        return circular_path
    except Exception as e:
        print(f"Failed to generate persona: {e}")
        return None

def paste_presenter(slide_img, presenter_path, canvas_size=(1280, 720), padding=30):
    """Bakes the circular AI presenter onto a PIL slide.

    We composite once at PIL level rather than layering a CompositeVideoClip
    during encoding, because per-frame alpha compositing in moviepy is one of
    the slowest steps in the pipeline.
    """
    if not presenter_path or not os.path.exists(presenter_path):
        return slide_img
    try:
        canvas_w, canvas_h = canvas_size
        bubble = Image.open(presenter_path).convert("RGBA")
        target_h = int(canvas_h * 0.25)
        scale = target_h / bubble.height
        target_w = max(1, int(bubble.width * scale))
        bubble = bubble.resize((target_w, target_h), Image.Resampling.LANCZOS)

        base = slide_img if slide_img.mode == "RGBA" else slide_img.convert("RGBA")
        x = canvas_w - target_w - padding
        y = canvas_h - target_h - padding
        base.paste(bubble, (x, y), bubble)
        return base.convert("RGB")
    except Exception as e:
        print(f"Paste presenter failed: {e}")
        return slide_img

def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size
        new_size = [
            int(base_size[0] * (1 + (zoom_ratio * t))),
            int(base_size[1] * (1 + (zoom_ratio * t)))
        ]
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        x = (new_size[0] - base_size[0]) // 2
        y = (new_size[1] - base_size[1]) // 2
        img = img.crop([x, y, x + base_size[0], y + base_size[1]])
        return np.array(img)
    return clip.fl(effect)

def generate_engaging_script(client, title, raw_text):
    """Rewrites content into a punchy narration script."""
    try:
        print("Rewriting script for high energy...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a video scriptwriter for a tech education channel. Rewrite the provided text into a punchy, clear spoken script. Keep it under 150 words. Do NOT include visual directions like [Curtain Up]. Just the spoken text."},
                {"role": "user", "content": f"Topic: {title}\n\nContent: {raw_text[:2000]}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Script generation failed: {e}")
        return raw_text

def generate_sora_clip(client, prompt, output_path):
    """Generates a 4-8s video clip using OpenAI Sora v2."""
    import time
    import requests
    
    API_URL = "https://api.openai.com/v1/videos"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    try:
        with open("sora_trace.log", "w") as log:
            log.write(f"Starting Sora Request for: {prompt[:30]}...\n")
            
            print(f"REQUESTING SORA CLIP: {prompt[:50]}...")
            # 1. Submit Generation Request
            payload = {
                "model": "sora-2",
                "prompt": f"Realism style, high definition, cinematic lighting. {prompt}",
                "seconds": "8", # Generate 8 second clips
                "size": "1280x720"
            }
            
            log.write(f"Payload: {payload}\n")
            
            response = requests.post(API_URL, headers=headers, json=payload)
            log.write(f"Response Status: {response.status_code}\n")
            
            if response.status_code != 200:
                print(f"Sora Request Failed: {response.text}")
                log.write(f"Error Body: {response.text}\n")
                return None
                
            video_id = response.json().get("id")
            print(f"Sora Task ID: {video_id}. Polling for completion...")
            log.write(f"Task ID: {video_id}\n")
            
            # 2. Poll for Completion
            # Sora takes time, so we need to wait.
            status = "queued"
            video_url = None
            
            for i in range(30): # Wait up to 5 minutes (30 * 10s)
                time.sleep(10)
                status_res = requests.get(f"{API_URL}/{video_id}", headers=headers)
                log.write(f"Poll {i}: {status_res.status_code} - ")
                
                if status_res.status_code == 200:
                    data = status_res.json()
                    status = data.get("status")
                    log.write(f"Status: {status}\n")
                    
                    if status == "completed":
                        log.write(f"COMPLETION DATA: {data}\n")
                        video_url = data.get("video_url")
                        
                        if not video_url: video_url = data.get("url")
                        if not video_url and 'result' in data: video_url = data['result'].get('url')
                        
                        # Handle OpenAI Standard 'data' list format
                        if not video_url and 'data' in data:
                             if isinstance(data['data'], list) and len(data['data']) > 0:
                                 video_url = data['data'][0].get('url')
                        
                        log.write(f"Video URL found: {video_url}\n")
                        break
                    elif status == "failed":
                        print("Sora Generation Failed.")
                        log.write(f"FAILED. Error details: {data}\n")
                        return None
                else:
                    log.write(f"Polling Error Body: {status_res.text}\n")
            
            if video_url:
                print(f"Downloading Sora Clip from {video_url[:50]}...")
                # 3. Download Video
                v_res = requests.get(video_url)
                with open(output_path, 'wb') as f:
                    f.write(v_res.content)
                log.write("Download complete.\n")
                return output_path
            else:
                log.write("Timed out or no URL.\n")
            
    except Exception as e:
        print(f"Sora Error: {e}")
        with open("sora_trace.log", "a") as log:
             log.write(f"Exception: {e}\n")
        return None
    return None

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates an AI-narrated slideshow video:
    1. AI script rewrite + TTS audio (OpenAI Shimmer or gTTS fallback)
    2. Title slide + screenshot slides + content slides
    3. Optional presenter overlay via DALL-E
    """
    print(f"[VIDEO] === Starting video generation ===")
    print(f"[VIDEO] Title: {lesson_title}")
    print(f"[VIDEO] Output: {output_path}")
    print(f"[VIDEO] Text length: {len(summary_text)} chars")

    temp_files = []
    audio_clip = None
    final_video = None

    client = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("[VIDEO] OpenAI client initialized for premium audio + presenter")
        except Exception as e:
            print(f"[VIDEO] OpenAI client init failed: {e}")
            client = None
    else:
        print("[VIDEO] No OPENAI_API_KEY found, using gTTS fallback")

    try:
        # 1. GENERATE AUDIO
        print("[VIDEO] Step 1: Generating audio...")
        script_text = summary_text
        if client:
            print("[VIDEO] Rewriting script via GPT-4...")
            script_text = generate_engaging_script(client, lesson_title, summary_text)
            script_text = clean_text_for_tts(script_text)
            print(f"[VIDEO] Script ready ({len(script_text)} chars)")

            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)

            print("[VIDEO] Generating TTS audio (Nova)...")
            response = client.audio.speech.create(
                model="tts-1", voice="nova", input=script_text[:4096]
            )
            response.stream_to_file(audio_path)
            print(f"[VIDEO] TTS audio saved to {audio_path}")
        else:
            clean = clean_text_for_tts(summary_text)
            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)
            print("[VIDEO] Generating gTTS audio...")
            tts = gTTS(text=clean, lang='en')
            tts.save(audio_path)
            print(f"[VIDEO] gTTS audio saved to {audio_path}")

        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        print(f"[VIDEO] Audio duration: {total_duration:.1f}s")

        # 2. OPTIONAL PRESENTER OVERLAY
        print("[VIDEO] Step 2: Getting AI presenter...")
        presenter_bubble = get_ai_presenter(client)
        print(f"[VIDEO] Presenter: {'ready' if presenter_bubble else 'skipped'}")

        # 3. BUILD VISUAL SLIDES
        print("[VIDEO] Step 3: Building visual slides...")
        visual_clips = []
        remaining_time = total_duration

        # A. Title slide (3 seconds, no presenter bubble)
        title_img = create_title_slide(lesson_title)
        title_p = output_path.replace(".mp4", "_title.png")
        title_img.save(title_p)
        temp_files.append(title_p)
        title_dur = min(3, remaining_time)
        visual_clips.append(ImageClip(title_p).set_duration(title_dur))
        remaining_time -= title_dur

        # B. Expand assets into PIL slides. A tall full-page screenshot
        # becomes several viewport-height slides so the video "walks"
        # down the page instead of sitting on a single static frame.
        slide_images = []
        screenshots = get_screenshots()
        # Share the 5-slide budget across however many screenshots we have
        # so more screenshots -> fewer slices each, keeping total pace sane.
        per_screenshot_cap = max(2, 5 // max(1, len(screenshots)))
        for s in screenshots:
            try:
                with Image.open(s) as raw:
                    slide_images.extend(split_tall_screenshot(
                        raw, size=(1280, 720), max_slides=per_screenshot_cap
                    ))
            except Exception as e:
                print(f"[VIDEO] Skipping unreadable screenshot {s}: {e}")

        if len(slide_images) < 2:
            slide_images.append(create_text_slide(summary_text[:300], title=lesson_title))

        if not slide_images:
            slide_images.append(create_text_slide(lesson_title, title=lesson_title))

        # C. Distribute remaining time evenly across all slides.
        slide_duration = remaining_time / max(len(slide_images), 1)

        for i, slide_img in enumerate(slide_images):
            if remaining_time <= 0:
                break

            dur = min(slide_duration, remaining_time)

            # Bake the presenter bubble into the slide once (PIL) rather than
            # overlaying a CompositeVideoClip during encoding.
            if presenter_bubble:
                slide_img = paste_presenter(slide_img, presenter_bubble, canvas_size=(1280, 720))

            temp_p = output_path.replace(".mp4", f"_slide_{i}.png")
            slide_img.save(temp_p)
            temp_files.append(temp_p)
            visual_clips.append(ImageClip(temp_p).set_duration(dur))
            remaining_time -= dur

        # 4. COMPOSE FINAL VIDEO — method="chain" is much faster than "compose"
        # when all clips share the same size, which is the case after fit_to_canvas.
        print(f"[VIDEO] Step 4: Composing final video ({len(visual_clips)} clips)...")
        main_video = concatenate_videoclips(visual_clips, method="chain")

        if main_video.duration < total_duration:
            main_video = main_video.set_duration(total_duration)
        else:
            main_video = main_video.subclip(0, total_duration)

        final_video = main_video.set_audio(audio_clip)
        final_video.fps = 24

        print(f"[VIDEO] Writing video to {output_path}...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset='ultrafast',
            threads=4
        )
        print(f"[VIDEO] === Video generation complete ===")

    except Exception as e:
        print(f"[VIDEO] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        try:
            if final_video:
                final_video.close()
            if audio_clip:
                audio_clip.close()
        except:
            pass
        for f in temp_files:
            try:
                os.remove(f)
            except:
                pass

    return output_path
