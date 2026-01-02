import os
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_text_image(text, size=(1280, 720), bg_color=(30, 30, 30), text_color=(255, 255, 255)):
    """Generates an image with centered text using Pillow."""
    img = Image.new('RGB', size, color=bg_color)
    d = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        # Windows usually has arial
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()

    # Wrap text
    lines = textwrap.wrap(text, width=40) # Approx char width
    
    # Calculate text height for centering
    # Pillow 10+ uses getbbox or similar, let's use a simpler approximation if needed or try to be robust
    # Using a simple line height approach
    line_height = 80
    total_height = len(lines) * line_height
    y = (size[1] - total_height) / 2

    for line in lines:
        # d.textbbox is better but let's stick to simple center alignment logic 
        # For simple center: measure width roughly or just draw
        # d.text is reliable
        # We'll just left align with some padding or center roughly
        
        # d.textlength is available in newer Pillow
        try:
             w = d.textlength(line, font=font)
        except:
             w = len(line) * 30 # gross approximation if textlength fails
             
        x = (size[0] - w) / 2
        d.text((x, y), line, fill=text_color, font=font)
        y += line_height

    return img

def generate_simple_video(lesson_title, summary_text, output_path):
    """
    Creates a simple video:
    1. Generates TTS audio from summary.
    2. Creates a title card image.
    3. Combines them into mp4.
    """
    
    # 1. Generate Audio
    tts = gTTS(text=summary_text, lang='en')
    audio_path = output_path.replace(".mp4", ".mp3")
    tts.save(audio_path)
    
    # 2. Generate Image
    img = create_text_image(lesson_title)
    img_path = output_path.replace(".mp4", ".png")
    img.save(img_path)
    
    # 3. Combine with MoviePy
    audio_clip = AudioFileClip(audio_path)
    video_clip = ImageClip(img_path).set_duration(audio_clip.duration)
    video_clip = video_clip.set_audio(audio_clip)
    video_clip.fps = 24
    
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    
    # Cleanup temp files
    # video_clip.close() # moviepy 1.0 logic, 2.0 might be different context managed
    audio_clip.close()
    try:
        os.remove(audio_path)
        os.remove(img_path)
    except:
        pass
        
    return output_path
