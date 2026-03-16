"""
测试 faster-whisper REST API
API文档: http://localhost:9000/docs#/Endpoints/asr_asr_post
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import config

# API配置
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
    if not audio_file.exists():
        print(f"错误: 音频文件不存在: {audio_file}")
        return None
    
    print(f"转录音频: {audio_file}")
    
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
        response = requests.post(
            WHISPER_API_URL,
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result_text = response.text.strip()
            # 检测语言
            detected_lang = _detect_language(result_text)
            return {
                'text': result_text,
                'language': detected_lang
            }
        else:
            print(f"转录失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"转录错误: {e}")
        return None
    finally:
        files['audio_file'][1].close()


def _detect_language(text: str) -> str:
    """简单检测文本语言"""
    import re
    
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


# 向后兼容：保留原有的测试配置
AUDIO_FILE = Path("audio/BV1ZewVzWE5s.m4a")

def test_whisper_api():
    """测试Whisper ASR API"""
    print("=" * 60)
    print("测试 Faster-Whisper API")
    print("=" * 60)
    
    # 检查音频文件是否存在
    if not AUDIO_FILE.exists():
        print(f"错误: 音频文件不存在: {AUDIO_FILE}")
        return
    
    print(f"音频文件: {AUDIO_FILE}")
    print(f"文件大小: {AUDIO_FILE.stat().st_size / 1024:.2f} KB")
    print(f"API地址: {WHISPER_API_URL}")
    print("-" * 60)
    
    # 准备请求参数
    files = {
        'audio_file': (AUDIO_FILE.name, open(AUDIO_FILE, 'rb'), 'audio/m4a')
    }
    
    data = {
        'model': 'large-v3',  # 或其他可用模型
        'language': 'zh',     # 中文
        'output': 'json'      # 输出格式
    }
    
    try:
        print("正在发送请求...")
        response = requests.post(
            WHISPER_API_URL,
            files=files,
            data=data,
            timeout=300  # 5分钟超时
        )
        
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print("-" * 60)
        
        if response.status_code == 200:
            # 先打印原始响应内容
            print("原始响应内容 (前500字符):")
            print(response.text[:500])
            print("-" * 60)
            
            # 尝试解析JSON
            try:
                result = response.json()
                print("✅ JSON解析成功!")
                print("-" * 60)
                print("转录结果:")
                print(result.get('text', '无文本'))
                print("-" * 60)
                
                # 打印完整响应
                print("完整响应:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                
                return result
            except json.JSONDecodeError:
                print("⚠️  响应不是JSON格式，可能是纯文本")
                print("转录文本:")
                print(response.text)
                return response.text
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: 无法连接到 {WHISPER_API_URL}")
        print(f"请确保Whisper服务已启动: docker run -p 9000:9000 ...")
        print(f"错误详情: {e}")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        files['audio_file'][1].close()

if __name__ == "__main__":
    result = test_whisper_api()
    
    if result:
        print("\n" + "=" * 60)
        print("测试完成，API工作正常!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("测试失败，请检查API服务状态")
        print("=" * 60)
