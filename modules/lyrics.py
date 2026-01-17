import re

class LyricEngine:
    def __init__(self):
        pass

    def parse_lrc(self, lrc_text):
        """
        Parses a standard LRC string into a list of dicts:
        [{'time_ms': 12000, 'text': 'Hello world'}, ...]
        """
        lines = lrc_text.splitlines()
        parsed = []
        # Regex for [mm:ss.xx]
        pattern = re.compile(r'\[(\d+):(\d+)(\.\d+)?\](.*)')
        
        for line in lines:
            match = pattern.match(line)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                fraction = float(match.group(3)) if match.group(3) else 0.0
                text = match.group(4).strip()
                
                total_ms = (minutes * 60 * 1000) + (seconds * 1000) + int(fraction * 1000)
                parsed.append({"time_ms": total_ms, "text": text})
        
        return sorted(parsed, key=lambda x: x["time_ms"])

    def process_mix_lyrics(self, tracks_lyrics, mix_log):
        """
        Combines lyrics based on the mix process.
        
        Args:
            tracks_lyrics (list): List of LRC strings corresponding to the tracks.
            mix_log (list): The metadata returned by AudioMixer.
            
        Returns:
            final_lyrics (list): List of {'start_ms': ..., 'text': ..., 'text_trans': ...}
        """
        final_timeline = []
        
        for idx, log_entry in enumerate(mix_log):
            if idx >= len(tracks_lyrics):
                continue
                
            lrc_content = tracks_lyrics[idx]
            if not lrc_content:
                continue
                
            parsed_original = self.parse_lrc(lrc_content)
            
            # Filter and Shift
            # Equation: T_new = (T_old - Source_Start) / Speed + Mix_Start
            source_start = log_entry["source_start_ms"]
            source_end = log_entry["source_end_ms"]
            mix_start = log_entry["mix_start_ms"]
            speed = log_entry["speed_rate"]
            
            for line in parsed_original:
                t_old = line["time_ms"]
                
                # Check if this line falls within the selected segment
                if source_start <= t_old <= source_end:
                    t_new = (t_old - source_start) / speed + mix_start
                    final_timeline.append({
                        "time_ms": t_new,
                        "text": line["text"]
                    })
        
        # Sort by final timeline
        return sorted(final_timeline, key=lambda x: x["time_ms"])

    def translate_lines(self, lyric_list):
        """
        Mock translation. Replace with OpenAI call in production.
        """
        for item in lyric_list:
            # TODO: Integrate real translation API here.
            item["text_trans"] = f"(Trans) {item['text']}" 
        return lyric_list

    def export_to_lrc(self, processed_lyrics):
        """Helper to debug output"""
        output = []
        for line in processed_lyrics:
            ms = int(line["time_ms"])
            m = ms // 60000
            s = (ms % 60000) // 1000
            xx = (ms % 1000) // 10
            line_str = f"[{m:02d}:{s:02d}.{xx:02d}]{line['text']}"
            output.append(line_str)
        return "\n".join(output)
