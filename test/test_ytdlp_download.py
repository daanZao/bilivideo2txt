import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yt_dlp
import os

def test_single_video_download():
    bv_id = "BV12cwjzCESt"
    video_url = f"https://www.bilibili.com/video/{bv_id}"
    output_dir = "audio"
    
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/{bv_id}',
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"Testing yt-dlp download for: {video_url}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            print("\n" + "=" * 60)
            print("SUCCESS! Audio downloaded successfully")
            print("=" * 60)
            
            audio_file = os.path.join(output_dir, f"{bv_id}.mp3")
            if os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"Audio file: {audio_file}")
                print(f"File size: {file_size / 1024 / 1024:.2f} MB")
            
    except Exception as e:
        print("\n" + "=" * 60)
        print("FAILED! Error occurred:")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

if __name__ == "__main__":
    test_single_video_download()
