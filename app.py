import streamlit as st
import os
import shutil
import re
from modules.mixer import AudioMixer
from modules.lyrics import LyricEngine
from modules.video_engine import VideoEngine
from modules.downloader import MusicDownloader

st.set_page_config(page_title="Mixset Lyric Video Generator", layout="wide")
st.title("Queue-Based Mixset Generator")

# Initialize Downloader
downloader = MusicDownloader(output_dir="downloads")

# Session State
if "queue" not in st.session_state:
    st.session_state.queue = [] # List of {title, url/id, audio_path, lyric_text, start, end}

def infer_lyrics_mode(lyrics_text):
    if not lyrics_text:
        return "plain"
    if re.search(r'\[\d+:\d+(\.\d+)?\]', lyrics_text):
        return "lrc"
    return "plain"

# Tabs
tab_search, tab_config, tab_generate = st.tabs(["1. Search & Queue", "2. Configure Segments", "3. Generate"])

### 1. SEARCH & QUEUE ###
with tab_search:
    st.header("Search and Add to Queue")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search Genie & YouTube", placeholder="Artist - Title")
    with col2:
        search_btn = st.button("Search", type="primary")

    if search_btn and search_query:
        st.info(f"Searching for '{search_query}'...")
        
        # 1. Search Genie for Metadata/Lyrics
        genie_results = downloader.search_genie(search_query)
        
        if genie_results:
            st.success(f"Found {len(genie_results)} results on Genie.")
            for item in genie_results:
                with st.expander(f"{item['artist']} - {item['title']}"):
                    missing_lyrics = False
                    if st.button("Add This Track", key=f"add_{item['id']}"):
                        with st.spinner("Downloading Audio & Lyrics..."):
                            # 1. Fetch Lyrics
                            lyrics = downloader.get_genie_lyrics(item['id'])
                            if not lyrics:
                                lyrics = ""
                                missing_lyrics = True
                            
                            # 2. Download from YouTube (using Title Artist)
                            query = f"{item['artist']} - {item['title']}"
                            audio_path, yt_title = downloader.download_audio_from_youtube(query)
                            
                            if audio_path:
                                # Add to Queue
                                # Get duration for init
                                try:
                                    from moviepy import AudioFileClip
                                    af = AudioFileClip(audio_path)
                                    dur = af.duration
                                    af.close()
                                except:
                                    dur = 180.0 # Fallback
                                
                                st.session_state.queue.append({
                                    "title": f"{item['artist']} - {item['title']}",
                                    "audio_path": audio_path,
                                    "lyrics_raw": lyrics,
                                    "lyrics_mode": infer_lyrics_mode(lyrics),
                                    "duration": dur,
                                    "start": 0.0,
                                    "end": dur
                                })
                                st.success(f"Added '{item['title']}' to Queue!")
                                if missing_lyrics:
                                    st.warning("No Genie lyrics found. You can paste only the needed segment lines or skip lyrics in the Configure tab.")
                            else:
                                st.error("Failed to download audio.")
        else:
            st.warning("No results found on Genie Music. Try a different keyword.")

### 2. CONFIGURE SEGMENTS ###
with tab_config:
    st.header("Configure Queue")
    
    if not st.session_state.queue:
        st.info("Queue is empty. Go to Search tab.")
    
    indices_to_remove = []
    for i, item in enumerate(st.session_state.queue):
        with st.expander(f"{i+1}. {item['title']}", expanded=True):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.audio(item['audio_path'])
                range_val = st.slider(
                    f"Select Range (Total: {item['duration']:.1f}s)", 
                    0.0, item['duration'], (item['start'], item['end']), 
                    step=1.0, key=f"range_{i}"
                )
                st.session_state.queue[i]['start'] = range_val[0]
                st.session_state.queue[i]['end'] = range_val[1]
                
                if st.button("Remove", key=f"rem_{i}"):
                    indices_to_remove.append(i)
            with c2:
                st.caption("Tip: You can paste only the lyrics for the selected segment to save time.")
                mode = st.selectbox(
                    "Lyrics Mode",
                    options=["Timed LRC", "Plain text (auto distribute)", "Skip lyrics"],
                    index=0 if item.get("lyrics_mode") == "lrc" else 1 if item.get("lyrics_mode") == "plain" else 2,
                    key=f"mode_{i}"
                )
                mode_value = "lrc" if mode.startswith("Timed") else "plain" if mode.startswith("Plain") else "skip"
                st.session_state.queue[i]["lyrics_mode"] = mode_value
                new_lyrics = st.text_area("Lyrics (LRC or Text)", item['lyrics_raw'], height=150, key=f"lrc_{i}")
                st.session_state.queue[i]['lyrics_raw'] = new_lyrics
                if mode_value == "lrc" and new_lyrics and not infer_lyrics_mode(new_lyrics) == "lrc":
                    st.warning("No timestamps detected. Switch to plain text mode or add [mm:ss.xx] tags.")

    if indices_to_remove:
        for idx in sorted(indices_to_remove, reverse=True):
            del st.session_state.queue[idx]
        st.rerun()

### 3. GENERATE ###
with tab_generate:
    st.header("Generate Mix Video")
    
    if st.button("Start Processing", type="primary"):
        if not st.session_state.queue:
            st.error("Queue is empty!")
        else:
            status = st.empty()
            progress = st.progress(0)
            
            # Init Engines
            mixer = AudioMixer()
            lyric_engine = LyricEngine()
            video_engine = VideoEngine()
            
            # 1. Prepare Mix
            status.text("Step 1/3: Mixing Audio...")
            progress.progress(10)
            
            lrc_list = []
            for item in st.session_state.queue:
                mixer.add_track(item['audio_path'], item['start'], item['end'])
                lrc_list.append({"text": item['lyrics_raw'], "mode": item.get("lyrics_mode", "lrc")})
            
            mixed_audio, mix_log = mixer.process_mix()
            
            if not mixed_audio:
                st.error("Mixing failed.")
                st.stop()
                
            mix_output = "final_mix.mp3"
            mixer.export(mixed_audio, mix_output)
            st.audio(mix_output)
            
            progress.progress(50)
            
            # 2. Process Lyrics
            status.text("Step 2/3: Syncing Lyrics...")
            processed_lyrics = lyric_engine.process_mix_lyrics(lrc_list, mix_log)
            # Translate (Mock)
            translated_lyrics = lyric_engine.translate_lines(processed_lyrics)
            
            progress.progress(70)
            
            # 3. Render Video
            status.text("Step 3/3: Rendering Video with FFmpeg...")
            video_output = "final_result.mp4"
            try:
                video_engine.create_video(mix_output, translated_lyrics, video_output)
                progress.progress(100)
                status.text("Done!")
                
                st.success("Video Generated Successfully!")
                st.video(video_output)
            except Exception as e:
                st.error(f"Rendering failed: {e}")
