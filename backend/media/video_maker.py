import os
import glob
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

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
    
    # Draw title if provided
    if title:
        # Add gradient background for title
        for i in range(150):
            alpha = int(255 * (1 - i/150))
            d.rectangle([(0, i), (size[0], i+1)], fill=(99, 102, 241, alpha))
        
        title_lines = textwrap.wrap(title, width=25)
        for line in title_lines:
            try:
                w = d.textlength(line, font=title_font)
            except:
                w = len(line) * 40
            x = (size[0] - w) / 2
            # Shadow effect
            d.text((x+3, y_offset+3), line, fill=(0, 0, 0, 128), font=title_font)
            d.text((x, y_offset), line, fill=(255, 255, 255), font=title_font)
            y_offset += 90
        
        y_offset += 50

    # Wrap and draw body text
    lines = textwrap.wrap(text, width=35)
    for line in lines[:8]:  # Limit to 8 lines
        try:
            w = d.textlength(line, font=body_font)
        except:
            w = len(line) * 25
        x = (size[0] - w) / 2
        d.text((x, y_offset), line, fill=text_color, font=body_font)
        y_offset += 60

    return img

def create_title_slide(title, size=(1280, 720)):
    """Creates an attractive title slide with gradient background."""
    img = Image.new('RGB', size, color=(30, 30, 30))
    d = ImageDraw.Draw(img)
    
    # Create gradient background
    for y in range(size[1]):
        r = int(99 + (139 - 99) * y / size[1])
        g = int(102 + (92 - 102) * y / size[1])
        b = int(241 + (246 - 241) * y / size[1])
        d.rectangle([(0, y), (size[0], y+1)], fill=(r, g, b))
    
    try:
        font = ImageFont.truetype("arial.ttf", 96)
    except IOError:
        font = ImageFont.load_default()
    
    # Wrap title
    lines = textwrap.wrap(title, width=20)
    y = (size[1] - len(lines) * 120) / 2
    
    for line in lines:
        try:
            w = d.textlength(line, font=font)
        except:
            w = len(line) * 50
        x = (size[0] - w) / 2
        # Shadow
        d.text((x+4, y+4), line, fill=(0, 0, 0, 180), font=font)
        # Main text
        d.text((x, y), line, fill=(255, 255, 255), font=font)
        y += 120
    
    return img

def get_screenshots():
    """Get all screenshots from scraped_data folder."""
    screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "scraped_data")
    if os.path.exists(screenshot_dir):
        screenshots = glob.glob(os.path.join(screenshot_dir, "*.png"))
        return screenshots[:5]  # Limit to 5 screenshots
    return []

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates an engaging video with:
    1. Title slide
    2. Screenshots from scraped website (if available)
    3. Text content slides
    4. TTS audio narration
    """
    
    clips = []
    temp_files = []
    
    try:
        # 1. Generate TTS Audio
        tts = gTTS(text=summary_text, lang='en', slow=False)
        audio_path = output_path.replace(".mp4", ".mp3")
        tts.save(audio_path)
        temp_files.append(audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # 2. Create Title Slide (3 seconds)
        title_img = create_title_slide(lesson_title)
        title_path = output_path.replace(".mp4", "_title.png")
        title_img.save(title_path)
        temp_files.append(title_path)
        
        title_clip = ImageClip(title_path).set_duration(3)
        clips.append(title_clip)
        
        remaining_duration = total_duration - 3
        
        # 3. Get screenshots and create clips
        screenshots = get_screenshots()
        
        if screenshots:
            # Use screenshots with text overlays
            screenshot_duration = min(4, remaining_duration / max(len(screenshots), 1))
            
            for screenshot in screenshots:
                if remaining_duration <= 0:
                    break
                    
                try:
                    # Resize screenshot to fit
                    img = Image.open(screenshot)
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                    
                    # Add semi-transparent overlay
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 100))
                    img = img.convert('RGBA')
                    img = Image.alpha_composite(img, overlay)
                    
                    temp_screenshot = output_path.replace(".mp4", f"_screenshot_{len(clips)}.png")
                    img.convert('RGB').save(temp_screenshot)
                    temp_files.append(temp_screenshot)
                    
                    clip_duration = min(screenshot_duration, remaining_duration)
                    screenshot_clip = ImageClip(temp_screenshot).set_duration(clip_duration)
                    clips.append(screenshot_clip)
                    remaining_duration -= clip_duration
                    
                except Exception as e:
                    print(f"Error processing screenshot {screenshot}: {e}")
                    continue
        
        # 4. Create text content slides for remaining time
        if remaining_duration > 0:
            # Split summary into chunks
            words = summary_text.split()
            chunk_size = 50
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            
            slide_duration = remaining_duration / max(len(chunks), 1)
            
            for i, chunk in enumerate(chunks):
                if remaining_duration <= 0:
                    break
                    
                slide_img = create_text_slide(
                    chunk, 
                    bg_color=(45, 55, 72),
                    text_color=(255, 255, 255),
                    title=f"Key Point {i+1}" if i > 0 else None
                )
                slide_path = output_path.replace(".mp4", f"_slide_{i}.png")
                slide_img.save(slide_path)
                temp_files.append(slide_path)
                
                clip_duration = min(slide_duration, remaining_duration)
                slide_clip = ImageClip(slide_path).set_duration(clip_duration)
                clips.append(slide_clip)
                remaining_duration -= clip_duration
        
        # 5. Concatenate all clips
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)
        final_video.fps = 24
        
        # 6. Write video file
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            fps=24,
            preset='ultrafast'
        )
        
        # Cleanup
        final_video.close()
        audio_clip.close()
        
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    return output_path
