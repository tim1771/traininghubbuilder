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

def get_screenshots():
    """Get screenshots."""
    screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "scraped_data")
    if os.path.exists(screenshot_dir):
        screenshots = glob.glob(os.path.join(screenshot_dir, "*.png"))
        return screenshots[:5]
    return []

def clean_text_for_tts(text):
    import re
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text.strip()

def get_ai_presenter(client):
    """Generates a consistent AI Presenter image if it doesn't exist locally."""
    presenter_path = "media/presenter_persona.png"
    if os.path.exists(presenter_path):
        return presenter_path
    
    if not client:
        return None

    try:
        print("GENERATING CONSISTENT AI PERSONA...")
        prompt = "A professional, friendly AI tutor assistant, high-quality photorealistic portrait, diverse background, wearing business casual, neutral studio background, looking into camera with a slight smile."
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
        
        circular_path = "media/presenter_bubble.png"
        output.save(circular_path)
        return circular_path
    except Exception as e:
        print(f"Failed to generate persona: {e}")
        return None

def overlay_presenter(video_clip, presenter_path):
    """Overlays the circular AI presenter in the bottom-right corner."""
    if not presenter_path or not os.path.exists(presenter_path):
        return video_clip

    try:
        presenter = ImageClip(presenter_path).set_duration(video_clip.duration)
        # Resize to about 20% of the video height
        h = video_clip.h * 0.25
        presenter = presenter.resize(height=h)
        # Position at bottom right with padding
        presenter = presenter.set_position(("right", "bottom")).margin(right=30, bottom=30, opacity=0)
        
        return CompositeVideoClip([video_clip, presenter])
    except Exception as e:
        print(f"Overlay failed: {e}")
        return video_clip

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
    """Rewrites content into a high-energy YouTuber style script."""
    try:
        print("Rewriting script for high energy...")
        response = client.chat.completions.create(
            model="gpt-4",  # or gpt-3.5-turbo if 4 not available
            messages=[
                {"role": "system", "content": "You are an expert video scriptwriter for a high-energy tech education channel. Rewrite the provided text into a short, punchy, enthusiastic script for a spoken video. Use rhetorical questions, excitement, and clear calls to action. Keep it under 250 words. Do NOT include visual directions like [Curtain Up]. Just the spoken text."},
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

    temp_files = []
    audio_clip = None
    final_video = None

    client = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("Using OpenAI for premium audio + presenter")
        except:
            client = None

    try:
        # 1. GENERATE AUDIO
        script_text = summary_text
        if client:
            script_text = generate_engaging_script(client, lesson_title, summary_text)
            script_text = clean_text_for_tts(script_text)

            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)

            print("Generating neural audio (Shimmer)...")
            response = client.audio.speech.create(
                model="tts-1", voice="shimmer", input=script_text[:4096]
            )
            response.stream_to_file(audio_path)
        else:
            clean = clean_text_for_tts(summary_text)
            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)
            tts = gTTS(text=clean, lang='en')
            tts.save(audio_path)

        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration

        # 2. OPTIONAL PRESENTER OVERLAY
        presenter_bubble = get_ai_presenter(client)

        # 3. BUILD VISUAL SLIDES
        visual_clips = []
        remaining_time = total_duration

        # A. Title slide (3 seconds)
        title_img = create_title_slide(lesson_title)
        title_p = output_path.replace(".mp4", "_title.png")
        title_img.save(title_p)
        temp_files.append(title_p)
        title_dur = min(3, remaining_time)
        clip = ImageClip(title_p).set_duration(title_dur)
        clip = zoom_in_effect(clip, 0.05)
        visual_clips.append(clip)
        remaining_time -= title_dur

        # B. Collect content assets (screenshots + text slides)
        assets = []
        screenshots = get_screenshots()
        for s in screenshots:
            assets.append({"type": "screenshot", "path": s})

        # Add a text summary slide if we have few screenshots
        if len(assets) < 2:
            assets.append({"type": "text_slide", "text": summary_text[:300]})

        if not assets:
            assets.append({"type": "text_slide", "text": lesson_title})

        # C. Distribute remaining time across assets
        clip_duration = remaining_time / max(len(assets), 1)

        for i, asset in enumerate(assets):
            if remaining_time <= 0:
                break

            dur = min(clip_duration, remaining_time)

            if asset["type"] == "screenshot":
                img = Image.open(asset["path"])
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                temp_p = output_path.replace(".mp4", f"_slide_{i}.png")
                img.save(temp_p)
                temp_files.append(temp_p)
                clip = ImageClip(temp_p).set_duration(dur)
                clip = zoom_in_effect(clip, 0.03)
            else:
                slide_img = create_text_slide(asset["text"], title=lesson_title)
                temp_p = output_path.replace(".mp4", f"_slide_{i}.png")
                slide_img.save(temp_p)
                temp_files.append(temp_p)
                clip = ImageClip(temp_p).set_duration(dur)
                clip = zoom_in_effect(clip, 0.03)

            # Apply presenter overlay on slides
            if presenter_bubble:
                clip = overlay_presenter(clip, presenter_bubble)

            visual_clips.append(clip)
            remaining_time -= dur

        # 4. COMPOSE FINAL VIDEO
        main_video = concatenate_videoclips(visual_clips, method="compose")

        if main_video.duration < total_duration:
            main_video = main_video.set_duration(total_duration)
        else:
            main_video = main_video.subclip(0, total_duration)

        final_video = main_video.set_audio(audio_clip)
        final_video.fps = 24

        print(f"Writing video to {output_path}...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset='ultrafast',
            threads=4
        )

    except Exception as e:
        print(f"ERROR: {e}")
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
