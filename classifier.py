import openai
import config
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoClassifier:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=config.AI_CONFIG["api_key"],
            base_url=config.AI_CONFIG["base_url"]
        )
        self.model = config.AI_CONFIG["model"]
        self.enabled_categories = config.ENABLED_CATEGORIES
    
    def classify_video(self, title: str, description: str = "") -> Optional[str]:
        if not config.AI_CONFIG["api_key"]:
            logger.warning("AI API key not configured, skipping classification")
            return None
        
        prompt = f"""请根据以下视频信息判断其分类：

标题：{title}
简介：{description if description else "无"}

可选分类：科技、政治、教育、生活、娱乐、游戏、音乐、舞蹈、影视、其他

要求：
1. 只返回一个分类名称
2. 不要包含任何其他内容
3. 如果不确定，返回"其他"
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个视频分类助手，根据视频标题和简介判断视频分类。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            logger.info(f"Classified as: {category}")
            return category
            
        except Exception as e:
            logger.error(f"Error classifying video: {e}")
            return None
    
    def should_process(self, category: str) -> bool:
        if not category:
            return False
        
        return category in self.enabled_categories
    
    def classify_and_filter(self, title: str, description: str = "") -> tuple[Optional[str], bool]:
        category = self.classify_video(title, description)
        
        if not category:
            return None, False
        
        should_process = self.should_process(category)
        
        return category, should_process
