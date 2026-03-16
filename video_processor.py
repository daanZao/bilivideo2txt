"""
视频处理主控制器
按状态驱动处理流程：
0 - 已获取视频信息（初始状态）
1 - 标签命中，需要后续处理
2 - 音频下载成功
3 - 音频下载失败
4 - 转录成功
5 - 转录失败
6 - 翻译成功
7 - 翻译失败
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

import config
from models import Video, init_db, SessionLocal, engine
from fetcher import VideoFetcher
from feishu_uploader import FeishuUploader
from transcriber import transcribe_audio, detect_language
from translator import translate_text
from transcription_worker import TranscriptionWorker, update_video_transcription

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_DIR / 'processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VideoState:
    """视频处理状态常量"""
    INFO_FETCHED = 0      # 已获取视频信息（初始状态）
    TAG_MATCHED = 1       # 标签命中，需要后续处理
    AUDIO_SUCCESS = 2     # 音频下载成功
    AUDIO_FAILED = 3      # 音频下载失败
    TRANSCRIBE_SUCCESS = 4  # 转录成功
    TRANSCRIBE_FAILED = 5   # 转录失败
    TRANSLATE_SUCCESS = 6   # 翻译成功
    TRANSLATE_FAILED = 7    # 翻译失败


class VideoProcessor:
    """视频处理器 - 按状态驱动"""
    
    def __init__(self, max_retries: int = 3):
        self.fetcher = VideoFetcher()
        self.feishu_uploader = FeishuUploader()
        self.max_retries = max_retries  # 最大重试次数
        self.transcription_worker = TranscriptionWorker()  # 并发转录工作器
        
    def run(self):
        """运行完整处理流程"""
        logger.info("=" * 60)
        logger.info("Starting Video Processor")
        logger.info(f"Time: {datetime.now()}")
        logger.info("=" * 60)
        
        init_db()
        
        # 第一步：获取所有用户的视频信息
        self._fetch_all_videos()
        
        # 第二步：处理标签匹配和音频下载
        self._process_audio_download()
        
        # 第三步：处理音频转录
        self._process_transcription()
        
        # 第四步：处理翻译
        self._process_translation()
        
        # 第五步：上传到飞书
        self._upload_to_feishu()
        
        logger.info("=" * 60)
        logger.info("Processing completed")
        logger.info("=" * 60)
    
    def _fetch_all_videos(self):
        """获取所有用户的视频信息，状态设为1"""
        logger.info("\n" + "#" * 60)
        logger.info("Step 1: Fetching video information from all users")
        logger.info("#" * 60)
        
        for user_config in config.USER_CONFIGS:
            user_name = user_config["name"]
            user_url = user_config["url"]
            start_date = user_config.get("start_date", config.START_DATE)
            
            logger.info(f"\nFetching videos for user: {user_name}")
            logger.info(f"URL: {user_url}")
            logger.info(f"Start date: {start_date}")
            
            videos = self.fetcher.get_user_videos(user_url)
            
            if not videos:
                logger.warning(f"No videos found for user: {user_name}")
                continue
            
            logger.info(f"Found {len(videos)} videos")
            
            db = SessionLocal()
            try:
                for video_info in videos:
                    self._save_video_info(db, video_info, user_name, start_date)
            finally:
                db.close()
        
        # 统计
        db = SessionLocal()
        try:
            count = db.query(Video).filter(Video.procstate == VideoState.INFO_FETCHED).count()
            logger.info(f"\nTotal videos with state 0 (info fetched): {count}")
        finally:
            db.close()
    
    def _save_video_info(self, db: Session, video_info: dict, author: str, start_date: datetime):
        """保存视频信息，状态设为0"""
        bv_id = video_info['bv_id']
        
        # 检查是否已存在
        existing = db.query(Video).filter(Video.bv_id == bv_id).first()
        if existing:
            logger.debug(f"Video {bv_id} already exists, skipping")
            return
        
        # 检查日期
        video_created_at = video_info.get('created_at')
        if video_created_at and video_created_at < start_date:
            logger.debug(f"Video {bv_id} created at {video_created_at} is before start date, skipping")
            return
        
        # 获取视频标签
        logger.info(f"Fetching tags for video {bv_id}...")
        video_labels = self.fetcher.get_video_tags(bv_id)
        
        # 创建视频记录，状态为0（已获取信息）
        video = Video(
            bv_id=bv_id,
            title=video_info['title'],
            description=video_info.get('description', ''),
            author=author,
            created_at=video_info.get('created_at'),
            video_labels=video_labels,
            procstate=VideoState.INFO_FETCHED,  # 状态0：已获取信息
            status='info_fetched'
        )
        
        db.add(video)
        db.commit()
        logger.info(f"Video {bv_id} saved with state 0 (info fetched), tags: {video_labels}")
    
    def _process_audio_download(self):
        """处理标签匹配和音频下载"""
        logger.info("\n" + "#" * 60)
        logger.info("Step 2: Processing tag matching and audio download")
        logger.info("#" * 60)
        
        # Step 2a: 标签匹配，将状态从0改为1
        self._match_tags()
        
        # Step 2b: 下载音频，处理状态为1的视频
        self._download_audios()
        
        # 统计
        db = SessionLocal()
        try:
            matched_count = db.query(Video).filter(Video.procstate == VideoState.TAG_MATCHED).count()
            success_count = db.query(Video).filter(Video.procstate == VideoState.AUDIO_SUCCESS).count()
            failed_count = db.query(Video).filter(Video.procstate == VideoState.AUDIO_FAILED).count()
            logger.info(f"\nAudio download - Matched: {matched_count}, Success: {success_count}, Failed: {failed_count}")
        finally:
            db.close()
    
    def _match_tags(self):
        """标签匹配：将状态从0改为1"""
        logger.info("\n--- Tag Matching ---")
        
        db = SessionLocal()
        try:
            # 获取状态为0的视频
            videos = db.query(Video).filter(Video.procstate == VideoState.INFO_FETCHED).all()
            logger.info(f"Found {len(videos)} videos with state 0 to check tags")
            
            for video in videos:
                bv_id = video.bv_id
                
                # 检查标签是否匹配
                if self._check_labels_match(video.video_labels):
                    video.procstate = VideoState.TAG_MATCHED  # 状态1：标签命中
                    video.status = 'tag_matched'
                    logger.info(f"Video {bv_id} tags matched, set state to 1")
                else:
                    logger.debug(f"Video {bv_id} labels {video.video_labels} not match enabled categories")
                
                db.commit()
        finally:
            db.close()
    
    def _download_audios(self):
        """下载音频：处理状态为1（标签命中）和状态3（下载失败需重试）的视频"""
        logger.info("\n--- Audio Download ---")
        
        db = SessionLocal()
        try:
            # 获取状态为1的视频（标签已命中）
            videos_new = db.query(Video).filter(Video.procstate == VideoState.TAG_MATCHED).all()
            
            # 获取状态为3的视频（下载失败，且未超过重试次数）
            videos_retry = db.query(Video).filter(
                Video.procstate == VideoState.AUDIO_FAILED,
                Video.retry_count < self.max_retries
            ).all()
            
            total_videos = len(videos_new) + len(videos_retry)
            logger.info(f"Found {len(videos_new)} new videos and {len(videos_retry)} retry videos to download audio")
            
            # 处理新视频
            for video in videos_new:
                self._download_audio_for_video(db, video)
            
            # 处理重试视频
            for video in videos_retry:
                logger.info(f"Retrying audio download for video {video.bv_id} (attempt {video.retry_count + 1}/{self.max_retries})")
                video.retry_count += 1
                db.commit()
                self._download_audio_for_video(db, video)
                
        finally:
            db.close()
    
    def _download_audio_for_video(self, db: Session, video: Video):
        """为视频下载音频"""
        bv_id = video.bv_id
        
        logger.info(f"Downloading audio for video {bv_id}...")
        
        try:
            audio_file = self.fetcher.download_audio(bv_id)
            
            if audio_file and os.path.exists(audio_file):
                video.audio_path = audio_file
                video.procstate = VideoState.AUDIO_SUCCESS  # 状态2：下载成功
                video.status = 'audio_downloaded'
                logger.info(f"Audio downloaded successfully: {audio_file}")
            else:
                video.procstate = VideoState.AUDIO_FAILED  # 状态3：下载失败
                video.status = 'audio_failed'
                logger.error(f"Failed to download audio for video {bv_id}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error downloading audio for {bv_id}: {e}")
            video.procstate = VideoState.AUDIO_FAILED
            video.status = 'audio_failed'
            db.commit()
    
    def _check_labels_match(self, labels: list) -> bool:
        """检查视频标签是否匹配配置中的目标分类"""
        if not labels:
            return False
        
        labels_lower = [label.lower() for label in labels]
        enabled_categories_lower = [cat.lower() for cat in config.ENABLED_CATEGORIES]
        
        for label in labels_lower:
            for category in enabled_categories_lower:
                if category in label or label in category:
                    return True
        
        return False
    
    def _process_transcription(self):
        """处理音频转录：使用并发线程池 + Semaphore 限制"""
        logger.info("\n" + "#" * 60)
        logger.info("Step 3: Processing audio transcription (Concurrent)")
        logger.info("#" * 60)
        
        db = SessionLocal()
        try:
            # 获取状态为2的视频（音频下载成功）
            videos_new = db.query(Video).filter(Video.procstate == VideoState.AUDIO_SUCCESS).all()
            
            # 获取状态为5的视频（转录失败，且未超过重试次数）
            videos_retry = db.query(Video).filter(
                Video.procstate == VideoState.TRANSCRIBE_FAILED,
                Video.retry_count < self.max_retries
            ).all()
            
            # 合并所有待转录视频
            all_videos = videos_new + videos_retry
            
            if not all_videos:
                logger.info("No videos to transcribe")
                return
            
            # 重置新视频的重试计数
            for video in videos_new:
                video.retry_count = 0
            
            # 增加重试视频的计数
            for video in videos_retry:
                video.retry_count += 1
                logger.info(f"Retrying transcription for video {video.bv_id} (attempt {video.retry_count}/{self.max_retries})")
            
            db.commit()
            
            logger.info(f"Found {len(videos_new)} new videos and {len(videos_retry)} retry videos to transcribe")
            logger.info(f"Using concurrency={config.WHISPER_CONFIG.get('concurrency', 1)}, pool_size={config.WHISPER_CONFIG.get('thread_pool_size', 5)}")
            
        finally:
            db.close()
        
        # 使用并发工作器处理转录
        stats = self.transcription_worker.submit_tasks(all_videos, callback=update_video_transcription)
        
        # 统计
        logger.info(f"\nTranscription completed - Total: {stats['total']}, Success: {stats['success']}, Failed: {stats['failed']}")
    
    def _process_translation(self):
        """处理翻译：处理状态4（转录成功）和状态7（翻译失败需重试）的视频"""
        logger.info("\n" + "#" * 60)
        logger.info("Step 4: Processing translation")
        logger.info("#" * 60)
        
        db = SessionLocal()
        try:
            # 获取状态为4的视频（转录成功）
            videos_new = db.query(Video).filter(Video.procstate == VideoState.TRANSCRIBE_SUCCESS).all()
            
            # 获取状态为7的视频（翻译失败，且未超过重试次数）
            videos_retry = db.query(Video).filter(
                Video.procstate == VideoState.TRANSLATE_FAILED,
                Video.retry_count < self.max_retries
            ).all()
            
            total_videos = len(videos_new) + len(videos_retry)
            logger.info(f"Found {len(videos_new)} new videos and {len(videos_retry)} retry videos to translate")
            
            # 处理新视频
            for video in videos_new:
                # 重置重试计数
                video.retry_count = 0
                db.commit()
                self._translate_video(db, video)
            
            # 处理重试视频
            for video in videos_retry:
                logger.info(f"Retrying translation for video {video.bv_id} (attempt {video.retry_count + 1}/{self.max_retries})")
                video.retry_count += 1
                db.commit()
                self._translate_video(db, video)
                
        finally:
            db.close()
        
        # 统计
        db = SessionLocal()
        try:
            success_count = db.query(Video).filter(Video.procstate == VideoState.TRANSLATE_SUCCESS).count()
            failed_count = db.query(Video).filter(Video.procstate == VideoState.TRANSLATE_FAILED).count()
            logger.info(f"\nTranslation - Success: {success_count}, Failed: {failed_count}")
        finally:
            db.close()
    
    def _translate_video(self, db: Session, video: Video):
        """翻译视频内容"""
        bv_id = video.bv_id
        raw_text = video.raw_transcription
        language = video.raw_language
        
        if not raw_text:
            logger.error(f"No raw transcription for video {bv_id}")
            video.procstate = VideoState.TRANSLATE_FAILED
            video.status = 'translate_failed'
            db.commit()
            return
        
        # 如果是中文，不需要翻译
        if language and language.lower() in ['zh', 'chinese', 'cmn', 'mandarin']:
            logger.info(f"Video {bv_id} is in Chinese, no translation needed")
            video.processed_transcription = raw_text
            video.procstate = VideoState.TRANSLATE_SUCCESS  # 状态6：翻译成功（无需翻译）
            video.status = 'completed'
            video.processed_at = datetime.now()
            db.commit()
            return
        
        # 如果是英文，进行翻译
        if language and language.lower() in ['en', 'english']:
            logger.info(f"Translating video {bv_id} from English to Chinese...")
            
            try:
                # 调用翻译API
                translated_text = translate_text(raw_text, video.video_labels)
                
                if translated_text:
                    video.processed_transcription = translated_text
                    video.procstate = VideoState.TRANSLATE_SUCCESS  # 状态6：翻译成功
                    video.status = 'completed'
                    video.processed_at = datetime.now()
                    logger.info(f"Translation successful for {bv_id}")
                else:
                    video.procstate = VideoState.TRANSLATE_FAILED  # 状态7：翻译失败
                    video.status = 'translate_failed'
                    logger.error(f"Translation failed for {bv_id}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error translating video {bv_id}: {e}")
                video.procstate = VideoState.TRANSLATE_FAILED
                video.status = 'translate_failed'
                db.commit()
        else:
            # 其他语言，暂时不处理
            logger.info(f"Video {bv_id} language {language} not supported for translation, keeping raw text")
            video.processed_transcription = raw_text
            video.procstate = VideoState.TRANSLATE_SUCCESS
            video.status = 'completed'
            video.processed_at = datetime.now()
            db.commit()
    
    def _upload_to_feishu(self):
        """上传到飞书"""
        logger.info("\n" + "#" * 60)
        logger.info("Step 5: Uploading to Feishu")
        logger.info("#" * 60)
        
        # 检查飞书配置
        if not config.FEISHU_CONFIG.get('app_id') or not config.FEISHU_CONFIG.get('app_secret'):
            logger.warning("Feishu config not complete, skipping upload")
            return
        
        db = SessionLocal()
        try:
            # 获取状态为6的视频（翻译成功）且未上传的
            videos = db.query(Video).filter(
                Video.procstate == VideoState.TRANSLATE_SUCCESS,
                Video.status != 'uploaded'
            ).all()
            
            logger.info(f"Found {len(videos)} videos to upload to Feishu")
            
            for video in videos:
                self._upload_video_to_feishu(db, video)
        finally:
            db.close()
    
    def _upload_video_to_feishu(self, db: Session, video: Video):
        """上传单个视频到飞书"""
        bv_id = video.bv_id
        
        logger.info(f"Uploading video {bv_id} to Feishu...")
        
        try:
            video_data = {
                'bv_id': video.bv_id,
                'title': video.title,
                'author': video.author,
                'description': video.description or '',
                'video_labels': video.video_labels or [],
                'raw_transcription': video.raw_transcription or '',
                'processed_transcription': video.processed_transcription or '',
                'created_at': video.created_at
            }
            
            result = self.feishu_uploader.upload_video_content(video_data)
            
            if result and result.get('success'):
                video.status = 'uploaded'
                db.commit()
                logger.info(f"Video {bv_id} uploaded to Feishu successfully")
                if result.get('wiki_url'):
                    logger.info(f"Wiki URL: {result['wiki_url']}")
            else:
                logger.error(f"Failed to upload video {bv_id} to Feishu")
                
        except Exception as e:
            logger.error(f"Error uploading video {bv_id} to Feishu: {e}")


def main():
    processor = VideoProcessor()
    processor.run()


if __name__ == "__main__":
    main()
