"""
Whisper 转录工作线程模块
使用 Semaphore 限制并发请求数，使用 ThreadPoolExecutor 管理任务队列
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable
from pathlib import Path
from sqlalchemy.orm import Session

import config
from models import Video, SessionLocal
from transcriber import transcribe_audio

logger = logging.getLogger(__name__)


class TranscriptionWorker:
    """
    Whisper 转录工作器
    
    使用信号量限制同时发送到 Whisper 服务的请求数，
    使用线程池管理等待处理的任务队列。
    """
    
    def __init__(self, max_concurrency: int = None, pool_size: int = None):
        """
        初始化转录工作器
        
        Args:
            max_concurrency: 最大并发请求数（同时发送到 Whisper 的请求数）
            pool_size: 线程池大小（管理等待的任务数）
        """
        self.max_concurrency = max_concurrency or config.WHISPER_CONFIG.get("concurrency", 1)
        self.pool_size = pool_size or config.WHISPER_CONFIG.get("thread_pool_size", 5)
        
        # 信号量控制并发数
        self.semaphore = threading.Semaphore(self.max_concurrency)
        
        # 线程池管理任务
        self.executor = ThreadPoolExecutor(max_workers=self.pool_size)
        
        # 统计信息
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0
        }
        
        logger.info(f"TranscriptionWorker initialized: concurrency={self.max_concurrency}, pool_size={self.pool_size}")
    
    def submit_tasks(self, videos: List[Video], callback: Callable = None) -> Dict:
        """
        提交转录任务
        
        Args:
            videos: 待转录的视频列表
            callback: 完成回调函数，参数为 (video, success, result)
            
        Returns:
            统计信息
        """
        if not videos:
            logger.info("No videos to transcribe")
            return self.stats
        
        self.stats = {'total': len(videos), 'success': 0, 'failed': 0}
        
        logger.info(f"Submitting {len(videos)} transcription tasks (concurrency={self.max_concurrency})")
        
        # 提交所有任务到线程池
        future_to_video = {}
        for video in videos:
            future = self.executor.submit(self._transcribe_with_semaphore, video)
            future_to_video[future] = video
        
        # 等待所有任务完成
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            try:
                success, result = future.result()
                if success:
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                
                # 调用回调函数
                if callback:
                    callback(video, success, result)
                    
            except Exception as e:
                logger.error(f"Task for video {video.bv_id} raised exception: {e}")
                self.stats['failed'] += 1
                if callback:
                    callback(video, False, str(e))
        
        logger.info(f"All transcription tasks completed: {self.stats}")
        return self.stats
    
    def _transcribe_with_semaphore(self, video: Video) -> tuple:
        """
        使用信号量限制的转录方法
        
        Args:
            video: 视频对象
            
        Returns:
            (success: bool, result: dict or str)
        """
        bv_id = video.bv_id
        audio_path = video.audio_path
        
        logger.info(f"[Queue] Video {bv_id} waiting for semaphore (current concurrency: {self.max_concurrency - self.semaphore._value}/{self.max_concurrency})")
        
        # 获取信号量（限制并发）
        with self.semaphore:
            logger.info(f"[Start] Video {bv_id} starting transcription (current active: {self.max_concurrency - self.semaphore._value})")
            
            try:
                # 检查音频文件
                if not audio_path or not Path(audio_path).exists():
                    error_msg = f"Audio file not found: {audio_path}"
                    logger.error(f"[Error] Video {bv_id}: {error_msg}")
                    return False, error_msg
                
                # 调用 Whisper API
                result = transcribe_audio(audio_path)
                
                if result and result.get('text'):
                    logger.info(f"[Success] Video {bv_id} transcribed successfully, language: {result.get('language', 'unknown')}")
                    return True, result
                else:
                    error_msg = "Transcription returned empty result"
                    logger.error(f"[Error] Video {bv_id}: {error_msg}")
                    return False, error_msg
                    
            except Exception as e:
                error_msg = f"Transcription error: {str(e)}"
                logger.error(f"[Error] Video {bv_id}: {error_msg}")
                return False, error_msg
            finally:
                logger.info(f"[Done] Video {bv_id} transcription completed (active: {self.max_concurrency - self.semaphore._value - 1})")
    
    def shutdown(self):
        """关闭线程池"""
        logger.info("Shutting down TranscriptionWorker...")
        self.executor.shutdown(wait=True)
        logger.info("TranscriptionWorker shutdown complete")


def update_video_transcription(video: Video, success: bool, result: dict or str):
    """
    更新视频转录结果的回调函数
    
    Args:
        video: 视频对象
        success: 是否成功
        result: 转录结果或错误信息
    """
    db = SessionLocal()
    try:
        # 重新获取视频对象（因为在线程中）
        video_db = db.query(Video).filter(Video.bv_id == video.bv_id).first()
        if not video_db:
            logger.error(f"Video {video.bv_id} not found in database")
            return
        
        if success:
            video_db.raw_transcription = result.get('text', '')
            video_db.raw_language = result.get('language', 'unknown')
            video_db.procstate = 4  # TRANSCRIBE_SUCCESS
            video_db.status = 'transcribed'
            video_db.retry_count = 0  # 重置重试计数
            logger.info(f"[DB] Video {video.bv_id} updated with transcription result")
        else:
            video_db.procstate = 5  # TRANSCRIBE_FAILED
            video_db.status = 'transcribe_failed'
            video_db.retry_count += 1
            logger.warning(f"[DB] Video {video.bv_id} marked as failed (retry: {video_db.retry_count})")
        
        db.commit()
    except Exception as e:
        logger.error(f"[DB] Error updating video {video.bv_id}: {e}")
        db.rollback()
    finally:
        db.close()
