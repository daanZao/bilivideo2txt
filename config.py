import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.absolute()

# 标签配置 - 每个标签包含whisper提示词和文案整理/翻译提示词
TAG_CONFIGS = {
    "科技": {
        "whisper_prompt": "这是一段科技类视频，可能涉及技术评测、产品介绍、行业分析等内容。请准确识别技术术语和专业名词。",
        "process_prompt": """你是一位科技内容编辑。请对以下语音转录文本翻译成中文：

1. 修正识别错误的技术术语和专业名词
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "政治": {
        "whisper_prompt": "这是一段政治新闻或时政分析视频，可能涉及国际关系、政策解读等内容。请注意识别人名、地名和政治术语。",
        "process_prompt": """你是一位时政新闻编辑。请对以下语音转录文本翻译成中文：

1. 修正识别错误的人名、地名和政治术语
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "人工智能": {
        "whisper_prompt": "这是一段人工智能相关的技术视频，可能涉及AI模型、机器学习、深度学习等内容。请准确识别AI领域的专业术语。",
        "process_prompt": """你是一位AI技术内容编辑。请对以下语音转录文本翻译成中文：

1. 修正AI/ML领域的专业术语（如神经网络、Transformer、大语言模型等）
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "机器人": {
        "whisper_prompt": "This is a podcast conversation between a host and a guest discussing technology and current events. Speakers use informal American English with frequent filler words like 'you know', 'I mean', and 'kind of'. Proper nouns may include tech companies, author names, and academic terms. Output should use standard punctuation with periods at the end of sentences.",
        "process_prompt": """你是一位机器人技术编辑。请对以下语音转录文本翻译成中文：

1. 修正机器人领域的专业术语
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "创业故事": {
        "whisper_prompt": "This is a podcast conversation between a host and a guest discussing technology and current events. Speakers use informal American English with frequent filler words like 'you know', 'I mean', and 'kind of'. Proper nouns may include tech companies, author names, and academic terms. Output should use standard punctuation with periods at the end of sentences.",
        "process_prompt": """你是一位商业内容编辑。请对以下语音转录文本翻译成中文：

1. 修正公司名称、人名和商业术语
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "生产力": {
        "whisper_prompt": "这是一段关于生产力工具或效率提升的视频，可能涉及软件工具、工作方法、时间管理等内容。请准确识别软件名称和方法论术语。",
        "process_prompt": """你是一位效率工具内容编辑。请对以下语音转录文本翻译成中文：

1. 修正软件名称、工具名称和方法论术语
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    },
    "管理": {
        "whisper_prompt": "这是一段管理学或领导力相关的视频，可能涉及团队管理、项目管理、组织发展等内容。请准确识别管理学术语和方法论。",
        "process_prompt": """你是一位管理内容编辑。请对以下语音转录文本翻译成中文：

1. 修正管理学术语和方法论名称，优化管理理念的表达
2. 去除口语化的重复和停顿,优化原文中分句和分段
3. 输出符合中文阅读习惯的文章

原始文本：
{text}

请输出处理后的文本："""
    }
}

# 用户配置列表 - 每个用户可以独立配置
USER_CONFIGS = [
    {
        "name": "Web3天空之城",
        "url": "https://space.bilibili.com/351754674",
        "start_date": datetime(2026, 3, 16),
        "tags": ["科技", "政治", "人工智能", "机器人", "创业故事", "生产力", "管理"]
    }
]

# 向后兼容：保留BILIBILI_USERS变量
BILIBILI_USERS = [{"name": cfg["name"], "url": cfg["url"]} for cfg in USER_CONFIGS]

# 向后兼容：保留ENABLED_CATEGORIES变量（使用第一个用户的标签配置）
ENABLED_CATEGORIES = USER_CONFIGS[0]["tags"] if USER_CONFIGS else []

# 向后兼容：保留START_DATE变量（使用第一个用户的开始时间）
START_DATE = USER_CONFIGS[0]["start_date"] if USER_CONFIGS else datetime(2024, 1, 1)

# 音频输出目录
AUDIO_OUTPUT_DIR = BASE_DIR / "audio"
AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)

# 数据库配置
DATABASE_URL = f"sqlite:///{BASE_DIR / 'bili_video.db'}"

# AI服务配置（当前停用）
AI_CONFIG = {
    "api_key": os.getenv("AI_API_KEY", ""),
    "model": os.getenv("AI_MODEL", "gpt-3.5-turbo"),
    "base_url": os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
}

# Whisper服务配置
WHISPER_CONFIG = {
    "api_url": os.getenv("WHISPER_API_URL", "http://localhost:9000"),
    "model": os.getenv("WHISPER_MODEL", "large-v3"),
    "language": os.getenv("WHISPER_LANGUAGE", "zh"),
}

# 飞书配置
FEISHU_CONFIG = {
    "app_id": os.getenv("FEISHU_APP_ID", ""),
    "app_secret": os.getenv("FEISHU_APP_SECRET", ""),
    "wiki_space_id": os.getenv("FEISHU_WIKI_SPACE_ID", ""),
    "folder_token": os.getenv("FEISHU_FOLDER_TOKEN", ""),
}

# 抓取速度配置（秒/条，单线程）
FETCH_CONFIG = {
    "bilibili_api_delay": float(os.getenv("BILIBILI_API_DELAY", "1.0")),  # bilibili-api 抓取间隔
    "ytdlp_delay": float(os.getenv("YTDLP_DELAY", "2.0")),  # yt-dlp 下载间隔
}

# Whisper 服务配置
WHISPER_CONFIG = {
    "api_url": os.getenv("WHISPER_API_URL", "http://localhost:9000"),
    "model": os.getenv("WHISPER_MODEL", "large-v3"),
    "language": os.getenv("WHISPER_LANGUAGE", "zh"),
    "timeout": int(os.getenv("WHISPER_TIMEOUT", "3000")),  # 请求超时时间（秒）
    "concurrency": int(os.getenv("WHISPER_CONCURRENCY", "1")),  # Whisper 并发请求数（建议1，因为GPU资源有限）
    "thread_pool_size": int(os.getenv("WHISPER_THREAD_POOL", "5")),  # 线程池大小（管理等待的任务）
}

# 日志目录
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_user_config(name: str = None) -> dict:
    """
    获取用户配置
    
    Args:
        name: 用户名称，如果为None则返回第一个用户配置
        
    Returns:
        用户配置字典
    """
    if not USER_CONFIGS:
        return None
    
    if name is None:
        return USER_CONFIGS[0]
    
    for cfg in USER_CONFIGS:
        if cfg["name"] == name:
            return cfg
    
    return None


def get_all_user_names() -> list:
    """获取所有用户名称列表"""
    return [cfg["name"] for cfg in USER_CONFIGS]


def get_tag_config(tag: str) -> dict:
    """
    获取标签配置
    
    Args:
        tag: 标签名称
        
    Returns:
        标签配置字典，包含whisper_prompt和process_prompt
    """
    return TAG_CONFIGS.get(tag, {
        "whisper_prompt": "",
        "process_prompt": "请对以下文本进行整理和优化：\n\n{text}"
    })


def get_whisper_prompt(tag: str) -> str:
    """
    获取指定标签的Whisper提示词
    
    Args:
        tag: 标签名称
        
    Returns:
        Whisper提示词
    """
    config = TAG_CONFIGS.get(tag, {})
    return config.get("whisper_prompt", "")


def get_process_prompt(tag: str, text: str) -> str:
    """
    获取指定标签的文案处理提示词（已填充文本）
    
    Args:
        tag: 标签名称
        text: 需要处理的文本
        
    Returns:
        填充了文本的处理提示词
    """
    config = TAG_CONFIGS.get(tag, {})
    prompt_template = config.get("process_prompt", "请对以下文本进行整理：\n\n{text}")
    return prompt_template.format(text=text)
