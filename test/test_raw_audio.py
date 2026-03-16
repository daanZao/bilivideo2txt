import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yt_dlp
import os

def download_audio_raw(bv_id):
    url = f"https://www.bilibili.com/video/{bv_id}"
    output_dir = "audio"
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': f'{output_dir}/{bv_id}.%(ext)s',
        'quiet': True,
    }
    
    print(f"Testing raw audio download for: {url}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            print("\n" + "=" * 60)
            print("SUCCESS! Audio downloaded successfully")
            print("=" * 60)
            print(f"Downloaded file: {filename}")
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"File size: {file_size / 1024 / 1024:.2f} MB")
                print(f"File format: {filename.split('.')[-1]}")
            
            return filename
            
    except Exception as e:
        print("\n" + "=" * 60)
        print("FAILED! Error occurred:")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return None

if __name__ == "__main__":
    bv_id = "BV12cwjzCESt"
    download_audio_raw(bv_id)
