import subprocess
import os
from PIL import Image, ImageDraw, ImageFont
import json
import textwrap

class FFmpegVideoGenerator:
    def __init__(self, ffmpeg_path="ffmpeg"):
        # Assume ffmpeg is in path
        self.ffmpeg_path = ffmpeg_path
        
    def _create_text_image(self, text, subtext, size=(1920, 1080), output_path="frame.png", bg_image=None):
        """
        Creates a single image frame with text.
        """
        if bg_image:
            img = bg_image.copy()
            img = img.resize(size)
        else:
            img = Image.new('RGB', size, color=(0, 0, 0))
            
        draw = ImageDraw.Draw(img)
        
        # Load Fonts (Fallback to default if not found)
        try:
            # Try loading a system font or a specific ttf
            font_main = ImageFont.truetype("arial.ttf", 60)
            font_sub = ImageFont.truetype("arial.ttf", 40)
        except:
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            
        # Draw Main Text (e.g., Korean)
        # Simple centering
        w, h = size
        
        # Helper for wrapping
        lines = textwrap.wrap(text, width=40)
        y_text = h / 2 - 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_main)
            text_w = bbox[2] - bbox[0]
            draw.text(((w - text_w) / 2, y_text), line, font=font_main, fill="white")
            y_text += 70
            
        # Draw Sub Text (e.g., English translation)
        y_text += 20
        sub_lines = textwrap.wrap(subtext, width=50)
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=font_sub)
            text_w = bbox[2] - bbox[0]
            draw.text(((w - text_w) / 2, y_text), line, font=font_sub, fill="yellow")
            y_text += 50
            
        img.save(output_path)

    def generate_video(self, audio_path, lyric_data, output_path, bg_image_path=None):
        """
        Generates video by creating image frames and using FFmpeg concat.
        
        lyric_data: List of {'time_ms': 0, 'text': '...', 'text_trans': '...'}
        """
        # Create temp dir for frames
        temp_dir = "temp_frames"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Clean temp dir
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
            
        # Load BG
        bg_img = None
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                bg_img = Image.open(bg_image_path).convert('RGB')
            except:
                pass
                
        # Prepare Concat List
        concat_entries = []
        
        # Get audio duration (using ffprobe or assumed known? user passed lyric_data which aligns with audio)
        # We need duration to fill the gaps.
        # But we can just use the next lyric start time.
        
        for i, item in enumerate(lyric_data):
            start_ms = item['time_ms']
            text = item.get('text', '')
            subtext = item.get('text_trans', '')
            
            # Duration of this frame
            if i < len(lyric_data) - 1:
                next_ms = lyric_data[i+1]['time_ms']
                duration_sec = (next_ms - start_ms) / 1000.0
            else:
                duration_sec = 5.0 # Last frame default
                
            frame_filename = f"frame_{i:04d}.png"
            frame_path = os.path.join(temp_dir, frame_filename)
            
            self._create_text_image(text, subtext, output_path=frame_path, bg_image=bg_img)
            
            # Abs path for ffmpeg safe
            abs_frame_path = os.path.abspath(frame_path).replace("\\", "/")
            
            concat_entries.append(f"file '{abs_frame_path}'")
            concat_entries.append(f"duration {duration_sec:.3f}")
            
        # Repeat last frame to prevent glitch
        if concat_entries:
            concat_entries.append(concat_entries[-2]) # repeat last file line
            
        # Write concat list
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding='utf-8') as f:
            f.write("\n".join(concat_entries))
            
        # FFmpeg Command
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", os.path.abspath(concat_list_path),
            "-i", os.path.abspath(audio_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest", # End when audio ends
            output_path
        ]
        
        print(f"Running FFmpeg: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg failed: {e}")
            return None

