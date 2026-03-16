"""
翻译模块
调用 AI API 将非中文文本翻译成中文
"""
import logging
import openai
import config

logger = logging.getLogger(__name__)


def translate_text(text: str, video_labels: list = None, source_lang: str = "en") -> str:
    """
    将文本翻译成中文
    
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
                    return process_prompt.replace("请对以下语音转录文本翻译成中文", "请将以下{source_lang}文本翻译成中文") + "\n\n原文：\n{text}\n\n请输出中文翻译："
    
    # 默认提示词
    return """请将以下{source_lang}文本翻译成中文：

{text}

要求：
1. 保持原文的意思和语气
2. 翻译要自然流畅，符合中文表达习惯
3. 保留专有名词的原文，可在括号中注明中文
4. 如果是多人对话，保留说话人标识

请直接输出中文翻译："""
