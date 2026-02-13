import yt_dlp
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import quote_plus

class MusicDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        # Setup headers for Genie scrubbing
        self.genie_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_genie(self, keyword):
        """
        Searches Genie Music for tracks matching the keyword.
        """
        search_url = f"https://www.genie.co.kr/search/searchMain?query={quote_plus(keyword)}"
        try:
            resp = requests.get(search_url, headers=self.genie_headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            song_list = soup.select('table.list-wrap > tbody > tr.list')
            
            for tr in song_list[:10]: # Top 10
                try:
                    song_id = tr['songid']
                    title = tr.select_one('a.title').get_text(strip=True)
                    artist = tr.select_one('a.artist').get_text(strip=True)
                    results.append({
                        "id": song_id,
                        "title": title,
                        "artist": artist
                    })
                except Exception:
                    continue
            return results
        except Exception as e:
            print(f"Genie Search Error: {e}")
            return []

    def get_genie_lyrics(self, song_id):
        """
        Fetches lyrics for a specific song ID from Genie.
        """
        url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        try:
            resp = requests.get(url, headers=self.genie_headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            lyric_container = soup.select_one('#pLyrics > p')
            if not lyric_container:
                lyric_container = soup.select_one('#pLyrics')
                
            if not lyric_container:
                return None
                
            # Replace <br> with newlines
            text = lyric_container.get_text(separator="\n").strip()
            
            if "가사가 없습니다" in text:
                return None
                
            return text
            
        except Exception as e:
            print(f"Genie Lyric Fetch Error: {e}")
            return None

    def download_audio_from_youtube(self, query_or_url):
        """
        Searches YouTube string (or takes URL) and downloads MP3.
        Returns the filename.
        """
        if not query_or_url.startswith("http"):
             query_or_url = f"ytsearch:{query_or_url}"

        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '192K',
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query_or_url, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                final_filename = base + ".mp3"
                
                return final_filename, info.get('title', 'Unknown')
        except Exception as e:
            print(f"YT Download Error: {e}")
            return None, None
