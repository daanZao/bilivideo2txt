import yt_dlp
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time
from bilibili_api import user, video, sync
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoFetcher:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com',
            },
            'sleep_interval': 1,
            'max_sleep_interval': 3,
        }
    
    def get_user_videos(self, user_url: str) -> List[Dict]:
        logger.info(f"Fetching videos from: {user_url}")
        
        try:
            uid = self._extract_uid(user_url)
            if not uid:
                logger.error(f"Failed to extract UID from URL: {user_url}")
                return []
            
            logger.info(f"Extracted UID: {uid}")
            
            u = user.User(uid=uid)
            
            logger.info("Fetching video list from Bilibili API...")
            videos_data = sync(u.get_videos())
            
            logger.info(f"API Response type: {type(videos_data)}")
            logger.info(f"API Response keys: {videos_data.keys() if isinstance(videos_data, dict) else 'N/A'}")
            
            if 'list' not in videos_data:
                logger.warning(f"No 'list' key in response: {videos_data}")
                return []
            
            video_list = videos_data['list'].get('vlist', [])
            logger.info(f"Found {len(video_list)} videos")
            
            videos = []
            for idx, video_item in enumerate(video_list):
                logger.info(f"\n{'='*60}")
                logger.info(f"Video #{idx + 1}")
                logger.info(f"Video data keys: {video_item.keys()}")
                logger.info(f"Raw video data: {video_item}")
                
                video_info = {
                    'bv_id': video_item.get('bvid', ''),
                    'title': video_item.get('title', ''),
                    'description': video_item.get('description', ''),
                    'author': video_item.get('author', ''),
                    'created_at': self._parse_bilibili_timestamp(video_item.get('created')),
                }
                
                logger.info(f"\nParsed video info:")
                logger.info(f"  BV ID: {video_info['bv_id']}")
                logger.info(f"  Title: {video_info['title']}")
                logger.info(f"  Author: {video_info['author']}")
                logger.info(f"  Created at: {video_info['created_at']}")
                logger.info(f"  Description length: {len(video_info['description']) if video_info['description'] else 0} chars")
                logger.info(f"  Description preview: {video_info['description'][:100] if video_info['description'] else 'N/A'}...")
                
                videos.append(video_info)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Total videos found: {len(videos)}")
            return videos
            
        except Exception as e:
            logger.error(f"Error fetching videos: {e}", exc_info=True)
            return []
    
    def _extract_uid(self, user_url: str) -> Optional[int]:
        try:
            if 'space.bilibili.com' in user_url:
                parts = user_url.split('/')
                for part in parts:
                    if part.isdigit():
                        return int(part)
            return None
        except Exception as e:
            logger.error(f"Error extracting UID: {e}")
            return None
    
    def _parse_bilibili_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp)
            except:
                return None
        return None
    
    def get_video_info(self, video_url: str) -> Optional[Dict]:
        logger.info(f"Fetching video info from: {video_url}")
        
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                result = ydl.extract_info(video_url, download=False)
                
                logger.info(f"Video result keys: {result.keys()}")
                logger.info(f"Full video data: {result}")
                
                video_info = {
                    'bv_id': result.get('id', ''),
                    'title': result.get('title', ''),
                    'description': result.get('description', ''),
                    'author': result.get('uploader', ''),
                    'created_at': self._parse_timestamp(result.get('timestamp')),
                }
                
                logger.info(f"\nVideo info extracted:")
                logger.info(f"  BV ID: {video_info['bv_id']}")
                logger.info(f"  Title: {video_info['title']}")
                logger.info(f"  Author: {video_info['author']}")
                logger.info(f"  Created at: {video_info['created_at']}")
                logger.info(f"  Description length: {len(video_info['description']) if video_info['description'] else 0}")
                
                return video_info
            except Exception as e:
                logger.error(f"Error fetching video info: {e}", exc_info=True)
                return None
    
    def download_audio(self, bv_id: str) -> Optional[str]:
        video_url = f"https://www.bilibili.com/video/{bv_id}"
        output_dir = str(config.AUDIO_OUTPUT_DIR)
        
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': f'{output_dir}/{bv_id}.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info(f"Downloading audio from: {video_url}")
                info = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(info)
                logger.info(f"Audio downloaded successfully: {filename}")
                
                # 添加延迟，控制下载速度
                delay = config.FETCH_CONFIG.get("ytdlp_delay", 2.0)
                time.sleep(delay)
                
                return filename
            except Exception as e:
                logger.error(f"Error downloading audio: {e}", exc_info=True)
                return None
    
    def _parse_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp)
            except:
                return None
        return None
    
    def get_video_tags(self, bv_id: str) -> List[str]:
        """
        获取视频的标签列表
        
        Args:
            bv_id: 视频的BV号
            
        Returns:
            标签名称列表
        """
        try:
            v = video.Video(bvid=bv_id)
            tags_data = sync(v.get_tags())
            
            # 提取标签名称
            tag_names = [tag.get('tag_name', '') for tag in tags_data if tag.get('tag_name')]
            logger.info(f"Video {bv_id} tags: {tag_names}")
            
            # 添加延迟，控制抓取速度
            delay = config.FETCH_CONFIG.get("bilibili_api_delay", 1.0)
            time.sleep(delay)
            
            return tag_names
            
        except Exception as e:
            logger.error(f"Error fetching tags for video {bv_id}: {e}")
            return []
