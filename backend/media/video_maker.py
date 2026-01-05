import os
import glob
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, vfx
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from openai import OpenAI
from dotenv import load_dotenv
import requests
from io import BytesIO

import numpy as np # Needed for array manipulation in moviepy usually, but Pillow handles most.

load_dotenv()

def download_image(url, save_path):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
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
        print(f"REQUESTING SORA CLIP: {prompt[:50]}...")
        # 1. Submit Generation Request
        payload = {
            "model": "sora-2",
            "prompt": f"Realism style, high definition, cinematic lighting. {prompt}",
            "seconds": 8, # Generate 8 second clips
            "size": "1280x720"
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Sora Request Failed: {response.text}")
            return None
            
        video_id = response.json().get("id")
        print(f"Sora Task ID: {video_id}. Polling for completion...")
        
        # 2. Poll for Completion
        # Sora takes time, so we need to wait.
        status = "queued"
        video_url = None
        
        for _ in range(30): # Wait up to 5 minutes (30 * 10s)
            time.sleep(10)
            status_res = requests.get(f"{API_URL}/{video_id}", headers=headers)
            if status_res.status_code == 200:
                data = status_res.json()
                status = data.get("status")
                if status == "completed":
                    video_url = data.get("video_url") # Hypothetical field based on typical async APIs (or 'result' field)
                    # If field is different in reality, we'd need to debug, but assuming standard OpenAI 'result' or 'output'
                    if not video_url and 'result' in data:
                        video_url = data['result'].get('url')
                    break
                elif status == "failed":
                    print("Sora Generation Failed.")
                    return None
            else:
                print(f"Polling Error: {status_res.status_code}")
        
        if video_url:
            print(f"Downloading Sora Clip from {video_url[:50]}...")
            # 3. Download Video
            v_res = requests.get(video_url)
            with open(output_path, 'wb') as f:
                f.write(v_res.content)
            return output_path
            
    except Exception as e:
        print(f"Sora Error: {e}")
        return None
    return None

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates a 'Sora-Powered' Explainer Video:
    1. AI Script Rewrite (Enthusiastic)
    2. Sora v2 Video Clips (Intro + Concepts)
    3. Screenshots (Evidence)
    4. Neural Audio (Shimmer)
    """
    
    clips = []
    temp_files = []
    audio_clip = None
    final_video = None
    
    client = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("Using OpenAI for Premium Video")
        except:
            client = None

    try:
        # 1. SCRIPTING & AUDIO
        script_text = summary_text
        if client:
            script_text = generate_engaging_script(client, lesson_title, summary_text)
            script_text = clean_text_for_tts(script_text)
            
            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)
            
            print("Generating Neural Audio (Shimmer)...")
            response = client.audio.speech.create(
                model="tts-1", voice="shimmer", input=script_text[:4096]
            )
            response.stream_to_file(audio_path)
        else:
            clean = clean_text_for_tts(summary_text)
            audio_path = output_path.replace(".mp4", ".mp3")
            tts = gTTS(text=clean, lang='en')
            tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # 2. GENERATE VISUAL ASSETS
        visual_clips = []
        remaining_time = total_duration
        
        # A. Intro with Sora (Concept Art in Motion)
        # Generate a video clip instead of a static image for the title/intro
        if client:
            sora_intro_path = output_path.replace(".mp4", "_sora_intro.mp4")
            # Prompt: Professional cinematic intro
            if generate_sora_clip(client, f"Cinematic product shot of a digital training hub interface showing '{lesson_title}', glowing screens, modern tech office background, 4k", sora_intro_path):
                # We have a video!
                temp_files.append(sora_intro_path)
                # Load video clip
                from moviepy.editor import VideoFileClip
                intro_clip = VideoFileClip(sora_intro_path)
                # Cap at 4s or intro length
                intro_clip = intro_clip.subclip(0, min(intro_clip.duration, 4))
                
                # Overlay Title Text?
                # For simplicity, let's just use the Sora video as the visual and overlay text if we wanted, 
                # but let's assume the prompt handling puts text in or we just use it as background.
                # Actually, let's overlay the title using our existing logic but transparently?
                # Or just put the title slide *after*?
                # Let's use the Sora clip as the BACKGROUND for the title slide.
                
                # Create transparent title image
                title_img = create_title_slide(lesson_title) # This has solid bg currently
                # Let's just use the Sora clip alone for 4s as an "establishing shot"
                visual_clips.append(intro_clip)
                remaining_time -= intro_clip.duration
                
        if not visual_clips:
            # Fallback to static title
            title_img = create_title_slide(lesson_title)
            title_p = output_path.replace(".mp4", "_title.png")
            title_img.save(title_p)
            temp_files.append(title_p)
            clip = ImageClip(title_p).set_duration(3)
            clip = zoom_in_effect(clip, 0.05)
            visual_clips.append(clip)
            remaining_time -= 3
        
        # B. Main Content
        assets = []
        screenshots = get_screenshots()
        
        # 1. Add Screenshots
        for s in screenshots:
            assets.append({"type": "screenshot", "path": s})
            
        # 2. Add Sora Concept Clip (Middle of video)
        if client and remaining_time > 10:
            sora_concept_path = output_path.replace(".mp4", "_sora_concept.mp4")
            # Prompt based on title
            if generate_sora_clip(client, f"A realistic tutorial presenter demonstrating {lesson_title} on a laptop, over the shoulder shot, detailed screen, office environment", sora_concept_path):
                 assets.insert(1, {"type": "video", "path": sora_concept_path})
                 temp_files.append(sora_concept_path)

        # 3. Add Evidence/Text
        # ... (Same as before)

        if not assets:
             slide_img = create_text_slide("Listen closely...", title=lesson_title)
             assets.append({"type": "image", "path": "fallback"}) # logic handles generation
        
        clip_duration = remaining_time / len(assets)
        
        for asset in assets:
            if remaining_time <= 0: break
            
            dur = min(clip_duration, remaining_time)
            
            if asset["type"] == "video":
                from moviepy.editor import VideoFileClip
                v_path = asset["path"]
                clip = VideoFileClip(v_path)
                # Loop if needed or cut
                if clip.duration < dur:
                    clip = clip.loop(duration=dur)
                else:
                    clip = clip.subclip(0, dur)
                visual_clips.append(clip)
                remaining_time -= dur
                
            else:
                # Image/Screenshot logic (same as before)
                img_path = asset["path"]
                if asset["type"] == "image" and img_path == "fallback":
                     p = output_path.replace(".mp4", "_fallback.png")
                     create_text_slide(lesson_title).save(p)
                     img_path = p
                     temp_files.append(p)
                
                img = Image.open(img_path)
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                temp_p = output_path.replace(".mp4", f"_asset_{len(visual_clips)}.png")
                img.save(temp_p)
                temp_files.append(temp_p)
                
                clip = ImageClip(temp_p).set_duration(dur)
                clip = zoom_in_effect(clip, 0.04)
                visual_clips.append(clip)
                remaining_time -= dur

        # Concatenate visuals
        main_video = concatenate_videoclips(visual_clips, method="compose")
        
        if main_video.duration < total_duration:
            main_video = main_video.set_duration(total_duration)
        else:
            main_video = main_video.subclip(0, total_duration)

        final_video = main_video.set_audio(audio_clip)
        final_video.fps = 24

        print(f"Writing Sora-Enhanced Video to {output_path}...")
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
            if final_video: final_video.close()
            if audio_clip: audio_clip.close()
            # Close clips?
        except:
            pass
        # Cleanup temps
        for f in temp_files:
            try: os.remove(f)
            except: pass
            
    return output_path
