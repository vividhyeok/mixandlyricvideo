# Mixset Lyric Video MVP

This project allows you to create a DJ mixset from selected parts of MP3 files and automatically generates a lyric video with synchronized and translated lyrics.

## Features
- **High Freedom Selection:** Choose exact start/end times for each track.
- **Auto Mixing:** Automatically crossfades selected segments.
- **Lyric Sync:** Automatically shifts and cuts LRC lyrics to match the new mix.
- **Video Generation:** Creates an MP4 with lyrics overlaid.

## Prerequisites
1. **Python 3.8+**
2. **FFmpeg**: Must be installed and added to system PATH.
3. **ImageMagick**: Required for video text creation.
   - Download: https://imagemagick.org/script/download.php#windows
   - **Important:** During installation, check "Install legacy utilities (e.g. convert)" or ensure `magick` is in PATH.
   - You might need to edit `moviepy` config if it can't find ImageMagick.

## Installation

```bash
pip install -r requirements.txt
```

## How to Run

```bash
streamlit run app.py
```

## Usage
1. Upload MP3 files using the sidebar.
2. For each track in the main view:
   - Listen and select the start/end time using the slider.
   - Paste the LRC format lyrics into the text area.
3. Click "Generate Mix & Video".
4. Download the result or view it in the browser.
