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
        img = img.resize(new_size, Image.LANCZOS)
        x = (new_size[0] - base_size[0]) // 2
        y = (new_size[1] - base_size[1]) // 2
        img = img.crop([x, y, x + base_size[0], y + base_size[1]])
        return np.array(img)
    return clip.fl(effect)

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates a 'Screen Recording' style video:
    1. AI Instructor (Picture-in-Picture)
    2. Dynamic Slides/Screenshots (Main content)
    """
    
    clips = []
    temp_files = []
    audio_clip = None
    final_video = None
    presenter_img_path = None
    
    client = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("Using OpenAI for Premium Video")
        except:
            client = None

    try:
        # CLEAN TEXT
        clean_summary = clean_text_for_tts(summary_text)
        audio_path = output_path.replace(".mp4", ".mp3")
        temp_files.append(audio_path)

        # 1. AUDIO GENERATION
        if client:
            print("Generating Neural Audio...")
            response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=clean_summary[:4096]
            )
            response.stream_to_file(audio_path)
        else:
            tts = gTTS(text=clean_summary, lang='en')
            tts.save(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration

        # 2. GENERATE PRESENTER (One time per video)
        if client:
            presenter_path = output_path.replace(".mp4", "_presenter.png")
            # Check if we already have a generic presenter cached to save credits/time? 
            # For now, generate new one to be safe.
            if not os.path.exists("media/cached_presenter.png"):
                 generate_ai_presenter(client, "media/cached_presenter.png")
            
            if os.path.exists("media/cached_presenter.png"):
                presenter_img_path = "media/cached_presenter.png"

        # 3. BUILD CONTENT VISUALS
        visual_clips = []
        
        # A. Title Slide
        title_img = create_title_slide(lesson_title)
        title_p = output_path.replace(".mp4", "_title.png")
        title_img.save(title_p)
        temp_files.append(title_p)
        visual_clips.append(ImageClip(title_p).set_duration(3))
        
        remaining_time = total_duration - 3
        
        # B. Screenshots & Content
        screenshots = get_screenshots()
        chunks = summary_text.split('. ') # Split by sentence roughly
        
        # Strategy: Alternate between screenshots and text points
        # If we have screenshots, show them for longer.
        
        if screenshots:
            # Show screenshots with simple zoom
            shot_duration = remaining_time / len(screenshots) if len(screenshots) > 0 else 4
            for shot in screenshots:
                if remaining_time <= 0: break
                
                # Resize and Add Effect
                img = Image.open(shot).resize((1280, 720), Image.Resampling.LANCZOS)
                shot_p = output_path.replace(".mp4", f"_shot_{len(visual_clips)}.png")
                img.save(shot_p)
                temp_files.append(shot_p)
                
                dur = min(shot_duration, remaining_time)
                # Create clip
                clip = ImageClip(shot_p).set_duration(dur)
                
                # Use custom Zoom Effect (Ken Burns)
                # We avoid clip.resize() because it uses deprecated PIL.Image.ANTIALIAS
                clip = zoom_in_effect(clip, zoom_ratio=0.04)
                
                visual_clips.append(clip)
                remaining_time -= dur
        else:
            # Fallback to Text Slides
            chunk_dur = remaining_time / 4
            for i in range(4):
                if remaining_time <= 0: break
                slide = create_text_slide("Learn More in the Course...", title=lesson_title)
                slide_p = output_path.replace(".mp4", f"_slide_{i}.png")
                slide.save(slide_p)
                temp_files.append(slide_p)
                
                # Simple static slide for fallback
                visual_clips.append(ImageClip(slide_p).set_duration(chunk_dur))
                remaining_time -= chunk_dur

        # Concatenate visuals
        main_video = concatenate_videoclips(visual_clips, method="compose")
        # Ensure it matches audio exactly
        if main_video.duration < total_duration:
            # Extend last frame
            main_video = main_video.set_duration(total_duration)
        else:
            main_video = main_video.subclip(0, total_duration)
            
        final_layers = [main_video]

        # 4. ADD PRESENTER OVERLAY (Picture in Picture)
        if presenter_img_path:
            # Load presenter
            p_clip = ImageClip(presenter_img_path).set_duration(total_duration)
            # Resize presenter safely (scaling down usually doesn't trigger the ANTIALIAS crash in same way, strictly speaking resizing creates a new clip but let's be careful)
            # We will use resize by value which might be safe, or just use our custom resize if needed.
            # MoviePy's resize with a float/function triggers the issue. Resize with tuple/int might be safer or just rely on ImageClip loading it.
            
            # Use Pillow to resize presenter image upfront to avoid MoviePy resize issues
            p_img = Image.open(presenter_img_path)
            # Target height 250, keep aspect ratio
            aspect = p_img.width / p_img.height
            new_w = int(250 * aspect)
            p_img = p_img.resize((new_w, 250), Image.Resampling.LANCZOS)
            
            p_resized_path = output_path.replace(".mp4", "_presenter_small.png")
            p_img.save(p_resized_path)
            temp_files.append(p_resized_path)
            
            p_clip = ImageClip(p_resized_path).set_duration(total_duration)
            
            # Position bottom right
            p_clip = p_clip.set_position(("right", "bottom"))
            
            final_layers.append(p_clip)

        final_video = CompositeVideoClip(final_layers).set_audio(audio_clip)
        final_video.fps = 24

        print(f"Writing Premium Video to {output_path}...")
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
