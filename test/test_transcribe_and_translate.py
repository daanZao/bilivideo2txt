"""
测试脚本：提取1-2条视频文本，非中文则翻译成中文
使用bilibili-api获取完整视频信息
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import re
import logging
from datetime import datetime

import requests
import openai
from bilibili_api import video, sync
from sqlalchemy.orm import Session

import config
from models import Video, init_db, SessionLocal
from feishu_uploader import FeishuUploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VideoInfoFetcher:
    """视频信息获取模块"""
    
    @staticmethod
    def get_video_info(bv_id: str) -> dict:
        """
        使用bilibili-api获取视频详细信息
        
        Returns:
            {
                'title': 视频标题,
                'description': 视频简介,
                'author': 作者名称,
                'created_at': 创建时间(datetime),
                'tags': [标签列表]
            }
        """
        try:
            logger.info(f"Fetching video info for {bv_id}...")
            v = video.Video(bvid=bv_id)
            
            # 获取视频基本信息
            info = sync(v.get_info())
            
            # 获取视频标签
            tags_data = sync(v.get_tags())
            tags = [tag.get('tag_name', '') for tag in tags_data if tag.get('tag_name')]
            
            # 解析创建时间
            created_timestamp = info.get('ctime') or info.get('pubdate')
            created_at = datetime.fromtimestamp(created_timestamp) if created_timestamp else None
            
            video_info = {
                'title': info.get('title', ''),
                'description': info.get('desc', ''),
                'author': info.get('owner', {}).get('name', ''),
                'created_at': created_at,
                'tags': tags
            }
            
            logger.info(f"Video info fetched: {video_info['title']}")
            logger.info(f"Author: {video_info['author']}")
            logger.info(f"Tags: {video_info['tags']}")
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error fetching video info for {bv_id}: {e}")
            return {
                'title': '',
                'description': '',
                'author': '',
                'created_at': None,
                'tags': []
            }


class Transcriber:
    """语音识别模块"""
    
    def __init__(self):
        self.api_url = config.WHISPER_CONFIG.get("api_url", "http://localhost:9000")
        self.model = config.WHISPER_CONFIG.get("model", "large-v3")
        self.language = config.WHISPER_CONFIG.get("language", "zh")
    
    def transcribe(self, audio_file: Path, prompt: str = "") -> tuple:
        """
        转录音频文件
        
        Returns:
            (text, detected_language) 元组
        """
        if not audio_file.exists():
            logger.error(f"Audio file not found: {audio_file}")
            return None, None
        
        logger.info(f"Transcribing: {audio_file.name}")
        
        files = {
            'audio_file': (audio_file.name, open(audio_file, 'rb'), 'audio/m4a')
        }
        
        data = {
            'model': self.model,
            'language': self.language,
        }
        
        if prompt:
            data['initial_prompt'] = prompt
        
        try:
            response = requests.post(
                f"{self.api_url}/asr",
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                text = response.text.strip()
                # 尝试从响应头或内容检测语言
                detected_lang = self._detect_language(text)
                logger.info(f"Transcription completed, detected language: {detected_lang}")
                return text, detected_lang
            else:
                logger.error(f"Transcription failed: {response.status_code}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return None, None
        finally:
            files['audio_file'][1].close()
    
    def _detect_language(self, text: str) -> str:
        """
        简单检测文本语言
        返回 'zh', 'en', 'ja', 'ko', 'other'
        """
        if not text:
            return "unknown"
        
        # 统计中文字符数量
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 统计英文字符数量
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        # 统计日文字符（平假名、片假名）
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        # 统计韩文字符
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        
        total_chars = len(text)
        if total_chars == 0:
            return "unknown"
        
        # 计算比例
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        japanese_ratio = japanese_chars / total_chars
        korean_ratio = korean_chars / total_chars
        
        # 判断语言
        if chinese_ratio > 0.3:
            return "zh"
        elif japanese_ratio > 0.1:
            return "ja"
        elif korean_ratio > 0.1:
            return "ko"
        elif english_ratio > 0.5:
            return "en"
        else:
            return "other"


class Translator:
    """翻译模块"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=config.AI_CONFIG.get("api_key", ""),
            base_url=config.AI_CONFIG.get("base_url", "https://api.openai.com/v1")
        )
        self.model = config.AI_CONFIG.get("model", "gpt-3.5-turbo")
    
    def translate_to_chinese(self, text: str, source_lang: str = "en") -> str:
        """
        将文本翻译成中文
        
        Args:
            text: 原文本
            source_lang: 源语言代码
            
        Returns:
            中文翻译
        """
        if not config.AI_CONFIG.get("api_key"):
            logger.warning("AI API key not configured, skipping translation")
            return text
        
        lang_names = {
            "en": "英语",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语",
            "other": "外语"
        }
        
        source_lang_name = lang_names.get(source_lang, "外语")
        
        prompt = f"""请将以下{source_lang_name}文本翻译成中文：

{text}

要求：
1. 保持原文的意思和语气
2. 翻译要自然流畅，符合中文表达习惯
3. 保留专有名词的原文，可在括号中注明中文
4. 如果是多人对话，保留说话人标识

请直接输出中文翻译："""
        
        try:
            logger.info(f"Translating from {source_lang} to Chinese...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的翻译，擅长将各种语言准确翻译成中文。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            translated = response.choices[0].message.content.strip()
            logger.info("Translation completed")
            return translated
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text


def translate_text(text: str, video_labels: list = None, source_lang: str = "en") -> str:
    """
    将文本翻译成中文（供外部调用的便捷函数）
    
    Args:
        text: 原文本
        video_labels: 视频标签列表（用于选择提示词）
        source_lang: 源语言代码
        
    Returns:
        中文翻译文本
    """
    if not text:
        return ""
    
    if not config.AI_CONFIG.get("api_key"):
        logger.warning("AI API key not configured, skipping translation")
        return text
    
    # 根据标签选择提示词
    prompt_template = _get_prompt_by_labels(video_labels)
    
    lang_names = {
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "ru": "俄语",
        "other": "外语"
    }
    
    source_lang_name = lang_names.get(source_lang, "外语")
    
    prompt = prompt_template.format(
        text=text,
        source_lang=source_lang_name
    )
    
    try:
        logger.info(f"Translating from {source_lang} to Chinese...")
        
        client = openai.OpenAI(
            api_key=config.AI_CONFIG.get("api_key", ""),
            base_url=config.AI_CONFIG.get("base_url", "https://api.openai.com/v1")
        )
        model = config.AI_CONFIG.get("model", "gpt-3.5-turbo")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位专业的翻译，擅长将各种语言准确翻译成中文。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        translated = response.choices[0].message.content.strip()
        logger.info("Translation completed")
        return translated
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text


def _get_prompt_by_labels(video_labels: list) -> str:
    """根据视频标签选择合适的提示词"""
    if not video_labels:
        return """请将以下{source_lang}文本翻译成中文：

{text}

要求：
1. 保持原文的意思和语气
2. 翻译要自然流畅，符合中文表达习惯
3. 保留专有名词的原文，可在括号中注明中文
4. 如果是多人对话，保留说话人标识

请直接输出中文翻译："""
    
    # 检查标签匹配
    labels_lower = [label.lower() for label in video_labels]
    
    for label in labels_lower:
        for category, tag_config in config.TAG_CONFIGS.items():
            if category.lower() in label or label in category.lower():
                process_prompt = tag_config.get("process_prompt", "")
                if process_prompt:
                    # 使用标签特定的提示词，但改为翻译任务
                    return process_prompt.replace("请对以下语音转录文本进行处理", "请将以下{source_lang}文本翻译成中文") + "\n\n原文：\n{text}\n\n请输出中文翻译："
    
    # 默认提示词
    return """请将以下{source_lang}文本翻译成中文：

{text}

要求：
1. 保持原文的意思和语气
2. 翻译要自然流畅，符合中文表达习惯
3. 保留专有名词的原文，可在括号中注明中文
4. 如果是多人对话，保留说话人标识

请直接输出中文翻译："""


def test_transcribe_and_translate(limit: int = 2):
    """
    测试转录和翻译功能
    
    Args:
        limit: 处理的视频数量限制
    """
    logger.info("=" * 60)
    logger.info("测试视频转录和翻译功能")
    logger.info("=" * 60)
    
    # 初始化数据库
    init_db()
    
    # 获取音频文件列表
    audio_dir = config.AUDIO_OUTPUT_DIR
    audio_files = list(audio_dir.glob("*.m4a"))
    
    if not audio_files:
        logger.error("No audio files found in audio directory")
        return
    
    logger.info(f"Found {len(audio_files)} audio files, will process {limit}")
    
    # 初始化模块
    info_fetcher = VideoInfoFetcher()
    transcriber = Transcriber()
    translator = Translator()
    feishu_uploader = FeishuUploader()
    
    # 处理前limit个文件
    db = SessionLocal()
    try:
        for idx, audio_file in enumerate(audio_files[:limit], 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing video {idx}/{limit}: {audio_file.name}")
            logger.info(f"{'='*60}")
            
            # 从文件名提取BV号
            bv_id = audio_file.stem
            
            # 检查数据库中是否已存在
            existing = db.query(Video).filter(Video.bv_id == bv_id).first()
            
            # 0. 获取视频信息（从Bilibili API）
            logger.info("Step 0: Fetching video info from Bilibili API...")
            video_info = info_fetcher.get_video_info(bv_id)
            
            # 1. 转录音频
            logger.info("Step 1: Transcribing audio...")
            raw_text, detected_lang = transcriber.transcribe(audio_file)
            
            if not raw_text:
                logger.error(f"Failed to transcribe {audio_file.name}")
                continue
            
            logger.info(f"Raw text preview: {raw_text[:200]}...")
            logger.info(f"Detected language: {detected_lang}")
            
            # 2. 如果不是中文，则翻译
            processed_text = raw_text
            if detected_lang != "zh":
                logger.info(f"Step 2: Language is {detected_lang}, translating to Chinese...")
                processed_text = translator.translate_to_chinese(raw_text, detected_lang)
                logger.info(f"Translated text preview: {processed_text[:200]}...")
            else:
                logger.info("Step 2: Language is Chinese, no translation needed")
            
            # 3. 保存到数据库
            logger.info("Step 3: Saving to database...")
            
            if existing:
                # 更新现有记录
                existing.title = video_info['title'] or existing.title
                existing.description = video_info['description'] or existing.description
                existing.author = video_info['author'] or existing.author
                existing.created_at = video_info['created_at'] or existing.created_at
                existing.video_labels = video_info['tags'] or existing.video_labels
                existing.raw_language = detected_lang
                existing.raw_transcription = raw_text
                existing.processed_transcription = processed_text
                existing.processed_at = datetime.now()
                existing.status = 'completed'
            else:
                # 创建新记录
                video = Video(
                    bv_id=bv_id,
                    title=video_info['title'],
                    description=video_info['description'],
                    author=video_info['author'],
                    created_at=video_info['created_at'],
                    video_labels=video_info['tags'],
                    raw_language=detected_lang,
                    raw_transcription=raw_text,
                    processed_transcription=processed_text,
                    processed_at=datetime.now(),
                    status='completed'
                )
                db.add(video)
            
            db.commit()
            logger.info(f"✅ Video {bv_id} processed successfully")
            
            # 4. 上传到飞书（如果配置了）
            if feishu_uploader.client:
                logger.info("Step 4: Uploading to Feishu...")
                video_data = {
                    "bv_id": bv_id,
                    "title": video_info['title'],
                    "author": video_info['author'],
                    "created_at": video_info['created_at'],
                    "description": video_info['description'],
                    "video_labels": video_info['tags'],
                    "raw_language": detected_lang,
                    "raw_transcription": raw_text,
                    "processed_transcription": processed_text
                }
                feishu_result = feishu_uploader.upload_video_content(video_data)
                if feishu_result.get("success"):
                    logger.info(f"✅ Uploaded to Feishu successfully")
                    if "document_url" in feishu_result:
                        logger.info(f"Cloud Doc: {feishu_result['document_url']}")
                    if "wiki_url" in feishu_result:
                        logger.info(f"Wiki: {feishu_result['wiki_url']}")
                else:
                    logger.warning(f"⚠️ Feishu upload skipped: {feishu_result.get('error')}")
            else:
                logger.info("Step 4: Feishu not configured, skipping upload")
            
            # 打印完整结果
            logger.info(f"\n{'='*60}")
            logger.info("RESULT SUMMARY:")
            logger.info(f"{'='*60}")
            logger.info(f"BV ID: {bv_id}")
            logger.info(f"Title: {video_info['title']}")
            logger.info(f"Author: {video_info['author']}")
            logger.info(f"Created At: {video_info['created_at']}")
            logger.info(f"Tags: {video_info['tags']}")
            logger.info(f"Raw Language: {detected_lang}")
            logger.info(f"Raw Text Length: {len(raw_text)} chars")
            logger.info(f"Processed Text Length: {len(processed_text)} chars")
            logger.info(f"\nRaw Text (first 300 chars):\n{raw_text[:300]}...")
            if detected_lang != "zh":
                logger.info(f"\nTranslated Text (first 300 chars):\n{processed_text[:300]}...")
            logger.info(f"{'='*60}\n")
        
        logger.info("All videos processed successfully!")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # 处理前2个视频
    test_transcribe_and_translate(limit=2)
