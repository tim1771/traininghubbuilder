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

def generate_concept_art(client, prompt, output_path):
    """Generates relevant concept art using DALL-E 3."""
    try:
        print(f"Generating concept art: {prompt}...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"A high quality, vibrant, flat vector art illustration suitable for a tech video background about: {prompt}. Modern, clean, colorful.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        return download_image(url, output_path)
    except Exception as e:
        print(f"DALL-E Concept Art failed: {e}")
        return None

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates a 'High-Energy' Explainer Video:
    1. AI Script Rewrite (Enthusiastic)
    2. Mixed Visuals (Screenshots + DALL-E Concept Art)
    3. Dynamic Zoom Effects
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
            # Rewrite script for energy
            script_text = generate_engaging_script(client, lesson_title, summary_text)
            
            # Clean text just in case
            script_text = clean_text_for_tts(script_text)
            
            audio_path = output_path.replace(".mp4", ".mp3")
            temp_files.append(audio_path)
            
            print("Generating Neural Audio (Shimmer)...")
            response = client.audio.speech.create(
                model="tts-1",
                voice="shimmer", # Enthusiastic female voice
                input=script_text[:4096]
            )
            response.stream_to_file(audio_path)
        else:
            # Fallback
            clean = clean_text_for_tts(summary_text)
            audio_path = output_path.replace(".mp4", ".mp3")
            tts = gTTS(text=clean, lang='en')
            tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # 2. GENERATE VISUAL ASSETS
        visual_clips = []
        remaining_time = total_duration
        
        # A. Title Slide (3s)
        # Try to generate DALL-E background for title if possible
        title_bg_path = output_path.replace(".mp4", "_title_bg.png")
        if client:
            generate_concept_art(client, f"Abstract modern background representing {lesson_title}", title_bg_path)
        
        if os.path.exists(title_bg_path):
             # Overlay text on DALL-E image
             # For now, simple fallback to our Pillow function but we could load the image
             # Let's just use the manual title slide for reliability/speed, it looks okay.
             pass

        title_img = create_title_slide(lesson_title)
        title_p = output_path.replace(".mp4", "_title.png")
        title_img.save(title_p)
        temp_files.append(title_p)
        
        clip = ImageClip(title_p).set_duration(3)
        clip = zoom_in_effect(clip, 0.05) # Add zoom to title
        visual_clips.append(clip)
        remaining_time -= 3
        
        # B. Gather Assets (Screenshots + 1 DALL-E Concept)
        assets = []
        
        # 1. Screenshots
        screenshots = get_screenshots()
        for s in screenshots:
            assets.append({"type": "screenshot", "path": s})
            
        # 2. DALL-E Concept Art (generate 1 specific image)
        if client and remaining_time > 10:
            concept_path = output_path.replace(".mp4", "_concept.png")
            if generate_concept_art(client, lesson_title, concept_path):
                assets.insert(1, {"type": "image", "path": concept_path}) # Insert after first screenshot
                temp_files.append(concept_path)

        # 3. Text Slides (Fill gaps)
        # Reuse existing logic to generate a few key points
        sentences = script_text.split('. ')
        if len(sentences) > 3:
             # Create a text slide for the middle
             slide_img = create_text_slide("Key Insight", title=lesson_title)
             slide_p = output_path.replace(".mp4", "_text_insert.png")
             slide_img.save(slide_p)
             temp_files.append(slide_p)
             assets.insert(2, {"type": "image", "path": slide_p})

        # C. Distribute Assets across remaining time
        if not assets:
            # Fallback if no screenshots
            slide_img = create_text_slide("Listen to this...", title=lesson_title)
            assets.append({"type": "image", "path": "fallback"})
        
        # Calculate duration per clip
        clip_duration = remaining_time / len(assets)
        
        for asset in assets:
            if remaining_time <= 0: break
            
            dur = min(clip_duration, remaining_time)
            
            img_path = asset["path"]
            if asset["type"] == "image" and img_path == "fallback":
                 # Create temp fallback
                 p = output_path.replace(".mp4", "_fallback.png")
                 create_text_slide(lesson_title).save(p)
                 img_path = p
                 temp_files.append(p)
            
            # Resize logic
            img = Image.open(img_path)
            # Resize to 720p to ensure consistency
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            
            temp_p = output_path.replace(".mp4", f"_asset_{len(visual_clips)}.png")
            img.save(temp_p)
            temp_files.append(temp_p)
            
            clip = ImageClip(temp_p).set_duration(dur)
            
            # Vary the effect?
            # Zoom in
            clip = zoom_in_effect(clip, 0.04)
            
            visual_clips.append(clip)
            remaining_time -= dur

        # Concatenate visuals
        main_video = concatenate_videoclips(visual_clips, method="compose")
        
        # Ensure it matches audio exactly
        if main_video.duration < total_duration:
            main_video = main_video.set_duration(total_duration)
        else:
            main_video = main_video.subclip(0, total_duration)

        final_video = main_video.set_audio(audio_clip)
        final_video.fps = 24

        print(f"Writing High-Energy Video to {output_path}...")
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
        except:
            pass
        # Cleanup temps
        for f in temp_files:
            try: os.remove(f)
            except: pass
            
    return output_path
