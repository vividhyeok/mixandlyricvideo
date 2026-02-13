import os
import re
import uuid
import streamlit as st
from moviepy import AudioFileClip

from modules.downloader import MusicDownloader
from modules.lyrics import LyricEngine
from modules.mixer import AudioMixer
from modules.video_engine import VideoEngine

st.set_page_config(page_title="Mixset Lyric Video Generator", layout="wide")
st.title("🎬 Mixset Lyric Video Generator")
st.caption("곡 검색 → 구간/가사 설정 → 믹싱/영상 생성까지 한 번에 처리합니다.")

# Initialize downloader
DOWNLOADER = MusicDownloader(output_dir="downloads")

if "queue" not in st.session_state:
    st.session_state.queue = []
if "last_output" not in st.session_state:
    st.session_state.last_output = {}


def infer_lyrics_mode(lyrics_text: str) -> str:
    if not lyrics_text:
        return "plain"
    return "lrc" if re.search(r"\[\d+:\d+(\.\d+)?\]", lyrics_text) else "plain"


def get_audio_duration(audio_path: str) -> float:
    try:
        clip = AudioFileClip(audio_path)
        duration = float(clip.duration)
        clip.close()
        return max(duration, 1.0)
    except Exception:
        return 180.0


def queue_item(title: str, audio_path: str, lyrics: str) -> dict:
    duration = get_audio_duration(audio_path)
    return {
        "title": title,
        "audio_path": audio_path,
        "lyrics_raw": lyrics,
        "lyrics_mode": infer_lyrics_mode(lyrics),
        "duration": duration,
        "start": 0.0,
        "end": duration,
    }


def validate_queue(items: list[dict]) -> list[str]:
    errors = []
    if not items:
        errors.append("Queue가 비어 있습니다.")
        return errors

    for idx, item in enumerate(items, start=1):
        if not os.path.exists(item.get("audio_path", "")):
            errors.append(f"{idx}번 트랙 오디오 파일을 찾을 수 없습니다: {item.get('title', 'Unknown')}")
        if item["end"] <= item["start"]:
            errors.append(f"{idx}번 트랙의 종료 시점은 시작 시점보다 커야 합니다.")
    return errors


def generate_mix_and_video() -> None:
    validation_errors = validate_queue(st.session_state.queue)
    if validation_errors:
        for msg in validation_errors:
            st.error(msg)
        return

    status = st.empty()
    progress = st.progress(0)

    mixer = AudioMixer()
    lyric_engine = LyricEngine()
    video_engine = VideoEngine()

    # 1) Mix audio
    status.text("Step 1/3: 오디오 믹싱 중...")
    progress.progress(10)

    lrc_payloads = []
    for item in st.session_state.queue:
        mixer.add_track(item["audio_path"], item["start"], item["end"])
        lrc_payloads.append({"text": item["lyrics_raw"], "mode": item.get("lyrics_mode", "plain")})

    mixed_audio, mix_log = mixer.process_mix(crossfade_sec=4.0)
    if not mixed_audio:
        st.error("믹싱에 실패했습니다. 선택한 구간/오디오 파일을 확인해주세요.")
        return

    run_id = uuid.uuid4().hex[:8]
    mix_output = f"final_mix_{run_id}.mp3"
    video_output = f"final_result_{run_id}.mp4"

    try:
        mixer.export(mixed_audio, mix_output)
    finally:
        try:
            mixed_audio.close()
        except Exception:
            pass

    st.audio(mix_output)
    progress.progress(45)

    # 2) Process lyrics
    status.text("Step 2/3: 가사 타이밍 처리 중...")
    processed_lyrics = lyric_engine.process_mix_lyrics(lrc_payloads, mix_log)
    translated_lyrics = lyric_engine.translate_lines(processed_lyrics)
    progress.progress(70)

    # 3) Render video
    status.text("Step 3/3: 영상 렌더링 중...")
    try:
        video_engine.create_video(mix_output, translated_lyrics, video_output)
        progress.progress(100)
        status.text("완료!")

        st.session_state.last_output = {"audio": mix_output, "video": video_output}
        st.success("영상 생성이 완료되었습니다.")
        st.video(video_output)
    except Exception as exc:
        st.error(f"렌더링 실패: {exc}")


# Tabs
search_tab, config_tab, generate_tab = st.tabs(["1) 검색/큐", "2) 구간/가사 설정", "3) 생성"])

with search_tab:
    st.subheader("트랙 검색 및 큐 추가")
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        search_query = st.text_input("Genie + YouTube 검색어", placeholder="Artist - Title")
    with col2:
        search_btn = st.button("검색", type="primary", use_container_width=True)
    with col3:
        clear_btn = st.button("큐 비우기", use_container_width=True)

    if clear_btn:
        st.session_state.queue = []
        st.toast("Queue를 비웠습니다.")
        st.rerun()

    if search_btn:
        if not search_query.strip():
            st.warning("검색어를 입력해주세요.")
        else:
            with st.spinner(f"'{search_query}' 검색 중..."):
                genie_results = DOWNLOADER.search_genie(search_query)

            if not genie_results:
                st.warning("검색 결과가 없습니다. 키워드를 바꿔보세요.")
            else:
                st.success(f"{len(genie_results)}개 결과를 찾았습니다.")
                for item in genie_results:
                    label = f"{item['artist']} - {item['title']}"
                    with st.expander(label):
                        if st.button("이 곡 큐에 추가", key=f"add_{item['id']}"):
                            with st.spinner("오디오/가사 수집 중..."):
                                lyrics = DOWNLOADER.get_genie_lyrics(item["id"]) or ""
                                audio_path, _ = DOWNLOADER.download_audio_from_youtube(label)

                            if not audio_path:
                                st.error("유튜브 오디오 다운로드에 실패했습니다.")
                            else:
                                st.session_state.queue.append(queue_item(label, audio_path, lyrics))
                                st.success(f"'{label}' 추가 완료")
                                if not lyrics:
                                    st.info("가사를 찾지 못했습니다. 다음 탭에서 직접 입력하거나 스킵할 수 있습니다.")

with config_tab:
    st.subheader("큐 설정")

    if not st.session_state.queue:
        st.info("큐가 비어 있습니다. 먼저 곡을 추가해주세요.")
    else:
        total_selected = sum(max(0.0, i["end"] - i["start"]) for i in st.session_state.queue)
        st.metric("예상 총 길이", f"{total_selected:.1f}초")

    remove_indices = []
    for i, item in enumerate(st.session_state.queue):
        with st.expander(f"{i+1}. {item['title']}", expanded=True):
            c1, c2 = st.columns([1, 1])

            with c1:
                st.audio(item["audio_path"])
                start, end = st.slider(
                    "사용 구간",
                    min_value=0.0,
                    max_value=float(item["duration"]),
                    value=(float(item["start"]), float(item["end"])),
                    step=0.5,
                    key=f"range_{i}",
                )
                st.session_state.queue[i]["start"] = start
                st.session_state.queue[i]["end"] = end

                if end <= start:
                    st.error("종료 시점은 시작보다 커야 합니다.")

                if st.button("이 항목 제거", key=f"remove_{i}"):
                    remove_indices.append(i)

            with c2:
                mode = st.selectbox(
                    "가사 모드",
                    ["Timed LRC", "Plain text (auto distribute)", "Skip lyrics"],
                    index=0 if item.get("lyrics_mode") == "lrc" else 1 if item.get("lyrics_mode") == "plain" else 2,
                    key=f"mode_{i}",
                )
                mode_val = "lrc" if mode.startswith("Timed") else "plain" if mode.startswith("Plain") else "skip"
                st.session_state.queue[i]["lyrics_mode"] = mode_val

                raw = st.text_area("가사 입력", value=item["lyrics_raw"], height=180, key=f"lyrics_{i}")
                st.session_state.queue[i]["lyrics_raw"] = raw

                if mode_val == "lrc" and raw and infer_lyrics_mode(raw) != "lrc":
                    st.warning("LRC 타임스탬프([mm:ss.xx])가 없어 보입니다. Plain 모드 사용을 권장합니다.")

    if remove_indices:
        for idx in sorted(remove_indices, reverse=True):
            del st.session_state.queue[idx]
        st.rerun()

with generate_tab:
    st.subheader("최종 생성")
    st.write("모든 설정을 마친 뒤 아래 버튼을 눌러 믹스 오디오와 가사 영상을 생성하세요.")

    if st.button("생성 시작", type="primary"):
        generate_mix_and_video()

    if st.session_state.last_output:
        st.markdown("---")
        st.write("최근 생성 결과")
        audio_file = st.session_state.last_output.get("audio")
        video_file = st.session_state.last_output.get("video")
        if audio_file and os.path.exists(audio_file):
            st.audio(audio_file)
        if video_file and os.path.exists(video_file):
            st.video(video_file)
