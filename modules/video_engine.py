import os
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont

class VideoEngine:
    def __init__(self):
        pass

    def _measure_text_width(self, draw, text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def _wrap_text_line(self, draw, text, font, max_width):
        if not text:
            return [""]

        tokens = text.split()
        joiner = " "
        if len(tokens) <= 1:
            tokens = list(text)
            joiner = ""

        lines = []
        current = ""
        for token in tokens:
            candidate = token if not current else f"{current}{joiner}{token}"
            if self._measure_text_width(draw, candidate, font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = token
        if current:
            lines.append(current)
        return lines

    def _wrap_text(self, draw, text, font, max_width):
        lines = []
        for raw_line in text.splitlines():
            wrapped = self._wrap_text_line(draw, raw_line.strip(), font, max_width)
            lines.extend(wrapped)
        return lines

    def _fit_text(self, draw, text, font_path, base_size, max_width, max_lines, min_size=24):
        if not font_path:
            font = ImageFont.load_default()
            lines = self._wrap_text(draw, text, font, max_width)
            return font, lines

        size = base_size
        while size >= min_size:
            if font_path:
                font = ImageFont.truetype(font_path, size)
            else:
                font = ImageFont.load_default()
            lines = self._wrap_text(draw, text, font, max_width)
            if len(lines) <= max_lines:
                return font, lines
            size -= 2
        return font, lines

    def _text_block_height(self, draw, lines, font, line_spacing):
        heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            heights.append(bbox[3] - bbox[1])
        if not heights:
            return 0
        return sum(heights) + line_spacing * (len(heights) - 1)

    def _create_text_image(self, text, sub_text, output_path, size=(1920, 1080)):
        """
        Creates an image with text using Pillow.
        """
        img = Image.new('RGB', size, color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
        
        # Load font - standard windows font or fallback
        font_path = None
        try:
            # Try Arial or Malgun Gothic for Korean support
            font_path = "malgun.ttf"
            font_main = ImageFont.truetype(font_path, 60)
            font_sub = ImageFont.truetype(font_path, 40)
        except:
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            
        # Draw Main Text (Centered)
        # Using simple basic calculations for text centering (as textbbox/textwidth availability varies by PIL version)
        # Assuming simple drawing for MVP
        
        max_width = int(size[0] * 0.8)
        font_main, lines = self._fit_text(
            draw, text, font_path, 60, max_width, max_lines=4, min_size=28
        )
        font_sub, sub_lines = self._fit_text(
            draw, sub_text or "", font_path, 40, max_width, max_lines=4, min_size=20
        )
        main_spacing = 16
        sub_spacing = 12
        total_height = self._text_block_height(draw, lines, font_main, main_spacing)
        if sub_text:
            total_height += 24
            total_height += self._text_block_height(draw, sub_lines, font_sub, sub_spacing)

        y_cursor = (size[1] - total_height) // 2

        for line in lines:
            draw.text((size[0]//2, y_cursor), line, font=font_main, fill="white", anchor="mm")
            y_cursor += self._text_block_height(draw, [line], font_main, 0) + main_spacing

        if sub_text:
            y_cursor += 12
            for line in sub_lines:
                draw.text((size[0]//2, y_cursor), line, font=font_sub, fill="yellow", anchor="mm")
                y_cursor += self._text_block_height(draw, [line], font_sub, 0) + sub_spacing
                
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
