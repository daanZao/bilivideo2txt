import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

import config
from models import Video, init_db, SessionLocal
from fetcher import VideoFetcher
# from classifier import VideoClassifier  # AI分类功能已停用，改用标签判断

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_DIR / 'app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BiliVideoProcessor:
    def __init__(self):
        self.fetcher = VideoFetcher()
        # self.classifier = VideoClassifier()  # AI分类功能已停用
        
    def process_user(self, user_url: str, user_name: str):
        logger.info(f"Processing user: {user_name} ({user_url})")
        
        videos = self.fetcher.get_user_videos(user_url)
        
        if not videos:
            logger.warning(f"No videos found for user: {user_name}")
            return
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"Video list summary for user: {user_name}")
        logger.info(f"Total videos to process: {len(videos)}")
        logger.info(f"{'#'*60}\n")
        
        for idx, video in enumerate(videos[:5], 1):
            logger.info(f"Video #{idx}:")
            logger.info(f"  BV ID: {video.get('bv_id')}")
            logger.info(f"  Title: {video.get('title')}")
            logger.info(f"  Created: {video.get('created_at')}")
        
        if len(videos) > 5:
            logger.info(f"... and {len(videos) - 5} more videos")
        
        db = SessionLocal()
        try:
            for video_info in videos:
                self._process_video(db, video_info, user_name)
        finally:
            db.close()
    
    def _check_labels_match(self, labels: list) -> bool:
        """
        检查视频标签是否匹配配置中的目标分类
        
        Args:
            labels: 视频标签列表
            
        Returns:
            是否匹配
        """
        if not labels:
            return False
        
        # 将标签和配置的分类都转为小写进行比较
        labels_lower = [label.lower() for label in labels]
        enabled_categories_lower = [cat.lower() for cat in config.ENABLED_CATEGORIES]
        
        for label in labels_lower:
            for category in enabled_categories_lower:
                if category in label or label in category:
                    return True
        
        return False
    
    def _process_video(self, db: Session, video_info: dict, author: str):
        bv_id = video_info['bv_id']
        
        existing = db.query(Video).filter(Video.bv_id == bv_id).first()
        if existing:
            logger.info(f"Video {bv_id} already exists, skipping")
            return
        
        video_created_at = video_info.get('created_at')
        if video_created_at and video_created_at < config.START_DATE:
            logger.info(f"Video {bv_id} created at {video_created_at} is before start date {config.START_DATE}, skipping")
            return
        
        logger.info(f"Processing video: {bv_id} - {video_info['title']}")
        
        # 获取视频标签
        logger.info(f"Fetching tags for video {bv_id}...")
        video_labels = self.fetcher.get_video_tags(bv_id)
        
        # 检查标签是否匹配目标分类
        should_process = self._check_labels_match(video_labels)
        
        video = Video(
            bv_id=bv_id,
            title=video_info['title'],
            description=video_info.get('description', ''),
            author=author,
            created_at=video_info.get('created_at'),
            video_labels=video_labels,
            status='pending'
        )
        
        if not should_process:
            logger.info(f"Video {bv_id} labels {video_labels} not match enabled categories {config.ENABLED_CATEGORIES}, skipping")
            video.status = 'skipped'
            db.add(video)
            db.commit()
            return
        
        logger.info(f"Video {bv_id} labels match, will download audio")
        video.status = 'downloading'
        db.add(video)
        db.commit()
        
        audio_file = self.fetcher.download_audio(bv_id)
        
        if audio_file and os.path.exists(audio_file):
            video.audio_path = audio_file
            video.status = 'downloaded'
            logger.info(f"Audio saved to: {audio_file}")
        else:
            video.status = 'failed'
            logger.error(f"Failed to download audio for video {bv_id}")
        
        db.commit()
        logger.info(f"Video {bv_id} processing completed with status: {video.status}")
    
    def run(self):
        logger.info("=" * 50)
        logger.info("Starting Bilibili Video Processor")
        logger.info(f"Time: {datetime.now()}")
        logger.info("=" * 50)
        
        logger.info(f"\nConfiguration:")
        logger.info(f"  Users: {[u['name'] for u in config.BILIBILI_USERS]}")
        logger.info(f"  Enabled categories: {config.ENABLED_CATEGORIES}")
        logger.info(f"  Start date: {config.START_DATE}")
        logger.info(f"  Audio output dir: {config.AUDIO_OUTPUT_DIR}")
        logger.info(f"  Database: {config.DATABASE_URL}")
        
        init_db()
        
        for user in config.BILIBILI_USERS:
            try:
                self.process_user(user['url'], user['name'])
            except Exception as e:
                logger.error(f"Error processing user {user['name']}: {e}")
        
        logger.info("=" * 50)
        logger.info("Processing completed")
        logger.info("=" * 50)

def main():
    processor = BiliVideoProcessor()
    processor.run()

if __name__ == "__main__":
    main()
