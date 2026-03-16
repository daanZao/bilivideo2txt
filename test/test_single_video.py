import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetcher import VideoFetcher
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_video():
    fetcher = VideoFetcher()
    
    test_urls = [
        "https://www.bilibili.com/video/BV1WE411K7bD",
        "https://www.bilibili.com/video/BV1GJ411x7h7",
    ]
    
    print("\n" + "="*60)
    print("Testing single video info extraction")
    print("="*60 + "\n")
    
    for test_url in test_urls:
        print(f"\nTesting URL: {test_url}")
        video_info = fetcher.get_video_info(test_url)
        
        if video_info:
            print("\n" + "="*60)
            print("SUCCESS! Video info extracted:")
            print("="*60)
            for key, value in video_info.items():
                if key == 'description' and value:
                    print(f"{key}: {value[:200]}...")
                else:
                    print(f"{key}: {value}")
            break
        else:
            print(f"\nFailed to extract video info from {test_url}")

if __name__ == "__main__":
    test_single_video()
