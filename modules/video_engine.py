import os
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont

class VideoEngine:
    def __init__(self):
        pass

    def _create_text_image(self, text, sub_text, output_path, size=(1920, 1080)):
        """
        Creates an image with text using Pillow.
        """
        img = Image.new('RGB', size, color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        
        # Load font - standard windows font or fallback
        try:
            # Try Arial or Malgun Gothic for Korean support
            font_main = ImageFont.truetype("malgun.ttf", 60)
            font_sub = ImageFont.truetype("malgun.ttf", 40)
        except:
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            
        # Draw Main Text (Centered)
        # Using simple basic calculations for text centering (as textbbox/textwidth availability varies by PIL version)
        # Assuming simple drawing for MVP
        
        # We will just split lines and draw in center
        lines = text.split('\n')
        y_cursor = size[1] // 2 - 100
        
        for line in lines:
            draw.text((size[0]//2, y_cursor), line, font=font_main, fill="white", anchor="mm")
            y_cursor += 80
            
        # Draw Sub Text
        y_cursor += 20
        if sub_text:
            sub_lines = sub_text.split('\n')
            for line in sub_lines:
                draw.text((size[0]//2, y_cursor), line, font=font_sub, fill="yellow", anchor="mm")
                y_cursor += 60
                
        img.save(output_path)

    def create_video(self, audio_path, lyric_data, output_path, bg_image_path=None):
        """
        Generates a video using FFmpeg concat method.
        """
        # 1. Create temporary directory for frames
        temp_dir = "temp_frames"
        os.makedirs(temp_dir, exist_ok=True)
        
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        audio_duration = 0 # We rely on MP3 duration provided by external or calculate it
        
        # We need precise duration for each frame.
        # lyric_data is [{'time_ms': ..., 'text': ...}, ...]
        
        concat_entries = []
        
        for i, item in enumerate(lyric_data):
            start_ms = item["time_ms"]
            
            # Determine duration
            if i < len(lyric_data) - 1:
                next_ms = lyric_data[i+1]["time_ms"]
                duration_sec = (next_ms - start_ms) / 1000.0
            else:
                duration_sec = 5.0 # Extend last frame
                
            frame_filename = f"frame_{i:04d}.png"
            frame_path = os.path.join(temp_dir, frame_filename)
            
            self._create_text_image(item['text'], item.get('text_trans', ''), frame_path)
            
            # Escape path for ffmpeg concat file
            # Windows path handling for FFmpeg concat: forward slashes work best
            safe_path = os.path.abspath(frame_path).replace('\\', '/')
            
            concat_entries.append(f"file '{safe_path}'")
            concat_entries.append(f"duration {duration_sec:.3f}")
            
        # Write concat file
        with open(concat_list_path, "w", encoding="utf-8") as f:
            f.write("\n".join(concat_entries))
            
        # 2. Run FFmpeg
        # ffmpeg -f concat -safe 0 -i list.txt -i audio.mp3 -vf "format=yuv420p" -c:v libx264 -c:a aac -shortest out.mp4
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-i", audio_path,
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest", 
            output_path
        ]
        
        print(f"Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            raise Exception("FFmpeg failed to render video.")
            
        return output_path

