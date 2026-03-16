"""
音频转录模块
调用 faster-whisper REST API 进行音频转录
"""
import requests
import re
from pathlib import Path
import config

WHISPER_API_URL = config.WHISPER_CONFIG.get("api_url", "http://localhost:9000") + "/asr"


def transcribe_audio(audio_file: Path, language: str = None) -> dict:
    """
    转录音频文件
    
    Args:
        audio_file: 音频文件路径
        language: 语言代码（可选）
        
    Returns:
        {
            'text': 转录文本,
            'language': 检测到的语言
        }
    """
    if not isinstance(audio_file, Path):
        audio_file = Path(audio_file)
    
    if not audio_file.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_file}")
    
    files = {
        'audio_file': (audio_file.name, open(audio_file, 'rb'), 'audio/m4a')
    }
    
    data = {
        'model': config.WHISPER_CONFIG.get("model", "large-v3"),
        'output': 'json'
    }
    
    if language:
        data['language'] = language
    else:
        data['language'] = config.WHISPER_CONFIG.get("language", "zh")
    
    try:
        # 使用配置的超时时间
        timeout = config.WHISPER_CONFIG.get("timeout", 300)
        response = requests.post(
            WHISPER_API_URL,
            files=files,
            data=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result_text = response.text.strip()
            detected_lang = detect_language(result_text)
            return {
                'text': result_text,
                'language': detected_lang
            }
        else:
            raise RuntimeError(f"转录失败: HTTP {response.status_code}")
            
    finally:
        files['audio_file'][1].close()


def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 待检测文本
        
    Returns:
        语言代码: 'zh', 'en', 'ja', 'ko', 'other', 'unknown'
    """
    if not text:
        return "unknown"
    
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
    
    total_chars = len(text)
    if total_chars == 0:
        return "unknown"
    
    chinese_ratio = chinese_chars / total_chars
    english_ratio = english_chars / total_chars
    japanese_ratio = japanese_chars / total_chars
    korean_ratio = korean_chars / total_chars
    
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
