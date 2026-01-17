from moviepy import AudioFileClip, CompositeAudioClip

class AudioMixer:
    def __init__(self):
        self.tracks = [] # List of dicts: {path, start, end}

    def add_track(self, file_path, start_time_sec, end_time_sec):
        """
        Add a track configuration to the mix.
        """
        self.tracks.append({
            "path": file_path,
            "start": start_time_sec,
            "end": end_time_sec
        })

    def process_mix(self, crossfade_sec=5.0):
        """
        Simulates the 'DJ Bot' logic using MoviePy.
        
        Returns:
            mixed_audio (AudioFileClip/CompositeAudioClip): The final audio object.
            mix_log (list): Metadata for lyric synchronization.
        """
        if not self.tracks:
            return None, []

        mix_log = []
        audio_elements = []

        for i, conf in enumerate(self.tracks):
            # Load and cut
            try:
                clip = AudioFileClip(conf["path"]).subclip(conf["start"], conf["end"])
            except Exception as e:
                print(f"Error loading clip {conf['path']}: {e}")
                continue
            
            track_duration = clip.duration
            
            # Calculate start time in the mix
            if i == 0:
                mix_start = 0.0
            else:
                prev_entry = mix_log[-1]
                prev_end = prev_entry["mix_end_ms"] / 1000.0
                mix_start = max(0, prev_end - crossfade_sec)

            # Apply Crossfade
            if i > 0:
                clip = clip.audio_fadein(crossfade_sec)
            
            # Fade out previous track
            if i > 0 and audio_elements:
                 audio_elements[-1] = audio_elements[-1].audio_fadeout(crossfade_sec)

            clip = clip.set_start(mix_start)
            audio_elements.append(clip)
            
            mix_end = mix_start + track_duration
            
            mix_log.append({
                "track_index": i,
                "path": conf["path"],
                "source_start_ms": conf["start"] * 1000,
                "source_end_ms": conf["end"] * 1000,
                "mix_start_ms": mix_start * 1000,
                "mix_end_ms": mix_end * 1000,
                "speed_rate": 1.0
            })
            
        if not audio_elements:
            return None, []

        final_mix = CompositeAudioClip(audio_elements)
        return final_mix, mix_log

    def export(self, audio_clip, path):
        audio_clip.write_audiofile(path, fps=44100)
