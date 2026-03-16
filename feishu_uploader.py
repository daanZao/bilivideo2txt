"""
飞书云文档和Wiki上传模块
使用飞书开放平台API
"""
import os
import logging
from typing import Optional, List
from datetime import datetime

import requests

import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeishuUploader:
    """飞书文档上传器"""
    
    def __init__(self):
        self.app_id = config.FEISHU_CONFIG.get("app_id", "")
        self.app_secret = config.FEISHU_CONFIG.get("app_secret", "")
        self.wiki_space_id = config.FEISHU_CONFIG.get("wiki_space_id", "")
        self.folder_token = config.FEISHU_CONFIG.get("folder_token", "")
        
        self.access_token = None
        
        if not self.app_id or not self.app_secret:
            logger.warning("Feishu app_id or app_secret not configured")
            return
        
        # 获取tenant_access_token
        if self._get_access_token():
            logger.info("Feishu client initialized successfully")
    
    def _get_access_token(self) -> bool:
        """获取飞书tenant_access_token"""
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            result = resp.json()
            
            if result.get("code") == 0:
                self.access_token = result.get("tenant_access_token")
                return True
            else:
                logger.error(f"Failed to get access token: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return False
    
    def _request(self, method: str, url: str, **kwargs) -> dict:
        """发送飞书API请求"""
        if not self.access_token:
            if not self._get_access_token():
                return {"code": -1, "msg": "Failed to get access token"}
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            resp = requests.request(method, url, headers=headers, **kwargs, timeout=30)
            # 检查响应状态
            if resp.status_code != 200:
                logger.error(f"HTTP error {resp.status_code}: {resp.text[:500]}")
                return {"code": -1, "msg": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            return resp.json()
        except Exception as e:
            logger.error(f"API request error: {e}")
            return {"code": -1, "msg": str(e)}
    
    def create_document(self, title: str, author: str = "", bili_url: str = "", body_content: str = "", folder_token: Optional[str] = None, tags: str = "", description: str = "") -> Optional[str]:
        """
        创建飞书云文档
        
        Args:
            title: 文档标题
            author: 作者名称
            bili_url: B站视频链接
            body_content: 正文内容（译文）
            folder_token: 文件夹token（可选）
            tags: 标签文本（用于高亮块）
            description: 摘要文本（用于高亮块）
            
        Returns:
            文档的document_id，失败返回None
        """
        if not self.access_token:
            logger.error("Feishu client not initialized")
            return None
        
        try:
            # 1. 创建文档
            logger.info(f"Creating Feishu document: {title}")
            
            url = "https://open.feishu.cn/open-apis/docx/v1/documents"
            data = {
                "title": title
            }
            if folder_token:
                data["folder_token"] = folder_token
            
            result = self._request("POST", url, json=data)
            
            if result.get("code") != 0:
                logger.error(f"Failed to create document: {result}")
                return None
            
            document_id = result["data"]["document"]["document_id"]
            logger.info(f"Document created: {document_id}")
            
            # 2. 写入内容
            if author or bili_url or body_content or tags or description:
                self._write_content(document_id, author, bili_url, body_content, tags, description)
            
            return document_id
            
        except Exception as e:
            logger.error(f"Error creating Feishu document: {e}")
            return None
    
    def _write_content(self, document_id: str, author: str = "", bili_url: str = "", body_content: str = "", tags: str = "", description: str = ""):
        """
        向文档写入内容
        
        Args:
            document_id: 文档ID
            author: 作者名称
            bili_url: B站视频链接
            body_content: 正文内容（译文）
            tags: 标签文本（用于高亮块）
            description: 摘要文本（用于高亮块）
        """
        try:
            logger.info(f"Writing content to document: {document_id}")
            
            # 获取文档的第一个块ID（page块）
            list_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks"
            list_result = self._request("GET", list_url)
            
            if list_result.get("code") != 0:
                logger.error(f"Failed to list document blocks: {list_result}")
                return
            
            # 获取page块ID
            items = list_result.get("data", {}).get("items", [])
            if not items:
                logger.error("No blocks found in document")
                return
            
            # 查找page类型的块
            page_block_id = None
            for item in items:
                if item.get("block_type") == 1:  # page类型
                    page_block_id = item.get("block_id")
                    break
            
            if not page_block_id:
                logger.error("No page block found")
                return
            
            logger.info(f"Page block ID: {page_block_id}")
            
            # 使用 children 接口在page块下创建子块
            children_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{page_block_id}/children"
            
            # 第一步：在page下创建callout块（包含作者、链接、标签、摘要）
            callout_block_id = None
            if author or bili_url or tags or description:
                # 先创建空的callout块
                callout_data = {
                    "children": [
                        {
                            "block_type": 19,  # callout类型
                            "callout": {
                                "background_color": 5  # 5=浅蓝色
                            }
                        }
                    ]
                }
                
                result = self._request("POST", children_url, json=callout_data)
                
                if result.get("code") != 0:
                    logger.error(f"Failed to create callout block: {result}")
                else:
                    callout_block_id = result.get("data", {}).get("children", [{}])[0].get("block_id")
                    logger.info(f"Callout block created: {callout_block_id}")
                    
                    # 立即在callout块内添加内容（覆盖默认的空内容）
                    if callout_block_id:
                        callout_children_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{callout_block_id}/children"
                        
                        # 先删除默认的子块（如果存在）
                        # 飞书API会在创建callout时自动添加一个空段落，我们需要替换它
                        
                        # 构建三行内容
                        callout_children = []
                        
                        # 第一行：👤 作者：xxx  🔗 B站视频：链接
                        line1_elements = []
                        if author:
                            line1_elements.append({
                                "text_run": {
                                    "content": f"👤 作者：{author}"
                                }
                            })
                        if author and bili_url:
                            line1_elements.append({
                                "text_run": {
                                    "content": "  "
                                }
                            })
                        if bili_url:
                            line1_elements.append({
                                "text_run": {
                                    "content": f"🔗 B站视频：{bili_url}"
                                }
                            })
                        
                        if line1_elements:
                            callout_children.append({
                                "block_type": 2,
                                "text": {
                                    "elements": line1_elements
                                }
                            })
                        
                        # 第二行：🏷️ 标签：xxx
                        if tags:
                            callout_children.append({
                                "block_type": 2,
                                "text": {
                                    "elements": [
                                        {
                                            "text_run": {
                                                "content": f"🏷️ 标签：{tags}"
                                            }
                                        }
                                    ]
                                }
                            })
                        
                        # 第三行：📖 摘要：xxx
                        if description:
                            callout_children.append({
                                "block_type": 2,
                                "text": {
                                    "elements": [
                                        {
                                            "text_run": {
                                                "content": f"📖 摘要：{description}"
                                            }
                                        }
                                    ]
                                }
                            })
                        
                        if callout_children:
                            callout_content_data = {"children": callout_children}
                            callout_result = self._request("POST", callout_children_url, json=callout_content_data)
                            if callout_result.get("code") != 0:
                                logger.error(f"Failed to write callout content: {callout_result}")
                            else:
                                logger.info("Callout content written successfully")
            
            # 第三步：在page下创建正文text块（译文）
            if body_content:
                text_blocks = []
                max_length = 10000
                content_chunks = [body_content[i:i+max_length] for i in range(0, len(body_content), max_length)]
                
                for chunk in content_chunks:
                    text_blocks.append({
                        "block_type": 2,  # text类型
                        "text": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": chunk
                                    }
                                }
                            ]
                        }
                    })
                
                # 分批创建正文块
                batch_size = 100
                for i in range(0, len(text_blocks), batch_size):
                    batch = text_blocks[i:i+batch_size]
                    data = {"children": batch}
                    
                    result = self._request("POST", children_url, json=data)
                    
                    if result.get("code") != 0:
                        logger.error(f"Failed to write body blocks batch {i//batch_size + 1}: {result}")
                    else:
                        logger.info(f"Body blocks batch {i//batch_size + 1}/{(len(text_blocks) + batch_size - 1)//batch_size} written")
                
        except Exception as e:
            logger.error(f"Error writing content to document: {e}")
    
    def create_wiki_document(self, title: str, author: str = "", bili_url: str = "", body_content: str = "", wiki_space_id: Optional[str] = None, parent_node_token: Optional[str] = None, tags: str = "", description: str = "") -> Optional[dict]:
        """
        在Wiki空间中直接创建文档节点
        
        Args:
            title: 文档标题
            author: 作者名称
            bili_url: B站视频链接
            body_content: 正文内容（译文）
            wiki_space_id: Wiki空间ID（可选，默认使用配置中的）
            parent_node_token: 父节点token（可选）
            tags: 标签文本（用于高亮块）
            description: 摘要文本（用于高亮块）
            
        Returns:
            包含node_token和obj_token的字典，失败返回None
        """
        if not self.access_token:
            logger.error("Feishu client not initialized")
            return None
        
        space_id = wiki_space_id or self.wiki_space_id
        if not space_id:
            logger.error("Wiki space_id not configured")
            return None
        
        try:
            logger.info(f"Creating wiki document in space {space_id}: {title}")
            
            url = "https://open.feishu.cn/open-apis/wiki/v2/spaces/{}/nodes".format(space_id)
            
            data = {
                "node_type": "origin",
                "obj_type": "docx",
                "title": title
            }
            
            if parent_node_token:
                data["parent_node_token"] = parent_node_token
            
            result = self._request("POST", url, json=data)
            
            if result.get("code") != 0:
                logger.error(f"Failed to create wiki document: {result}")
                return None
            
            # 提取节点token和文档token
            node_data = result.get("data", {}).get("node", {})
            node_token = node_data.get("node_token")
            obj_token = node_data.get("obj_token")
            
            if node_token and obj_token:
                logger.info(f"Wiki document created: node_token={node_token}, obj_token={obj_token}")
                
                # 写入内容
                if author or bili_url or body_content or tags or description:
                    logger.info(f"Writing content to wiki document")
                    self._write_content(obj_token, author, bili_url, body_content, tags, description)
                else:
                    logger.warning("No content to write")
                
                return {
                    "node_token": node_token,
                    "obj_token": obj_token
                }
            else:
                logger.warning(f"Could not find tokens in response: {result}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating wiki document: {e}")
            return None
    
    def upload_video_content(self, video_data: dict) -> dict:
        """
        上传视频内容到飞书
        
        Args:
            video_data: 视频数据字典，包含：
                - bv_id: BV号
                - title: 视频标题
                - author: 作者
                - created_at: 创建时间
                - description: 视频简介
                - video_labels: 视频标签
                - raw_language: 原始语言
                - raw_transcription: 原始转录文本
                - processed_transcription: 处理后的文本（翻译后）
                
        Returns:
            上传结果字典，包含document_id和wiki_node_token
        """
        if not self.access_token:
            logger.error("Feishu client not initialized, skipping upload")
            return {"success": False, "error": "Feishu not configured"}
        
        bv_id = video_data.get("bv_id", "")
        title = video_data.get("title", "")
        author = video_data.get("author", "")
        created_at = video_data.get("created_at")
        description = video_data.get("description", "")
        video_labels = video_data.get("video_labels", [])
        raw_language = video_data.get("raw_language", "")
        raw_transcription = video_data.get("raw_transcription", "")
        processed_transcription = video_data.get("processed_transcription", "")
        
        # 格式化创建时间
        created_at_str = ""
        created_at_date = ""
        if created_at:
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                created_at_date = created_at.strftime("%Y%m%d")
            else:
                created_at_str = str(created_at)
                # 尝试从字符串提取日期
                try:
                    dt = datetime.strptime(str(created_at)[:10], "%Y-%m-%d")
                    created_at_date = dt.strftime("%Y%m%d")
                except:
                    created_at_date = ""
        
        # 格式化标签
        tags_str = ", ".join(video_labels) if video_labels else ""
        
        # 构建文档标题：【YYYYMMDD】+ 原标题
        if created_at_date:
            doc_title = f"【{created_at_date}】{title}"
        else:
            doc_title = title
        
        # B站视频链接
        bili_url = f"https://www.bilibili.com/video/{bv_id}" if bv_id else ""
        
        # 构建正文内容（译文）
        body_content = processed_transcription or raw_transcription or ""
        
        result = {
            "success": True,
            "bv_id": bv_id,
            "title": title
        }
        
        # 如果配置了Wiki空间，直接在Wiki中创建文档
        if self.wiki_space_id:
            logger.info(f"Creating document in Wiki space: {title}")
            wiki_result = self.create_wiki_document(doc_title, author, bili_url, body_content, tags=tags_str, description=description)
            if wiki_result:
                result["wiki_node_token"] = wiki_result["node_token"]
                result["wiki_url"] = f"https://www.feishu.cn/wiki/{wiki_result['node_token']}"
                result["document_id"] = wiki_result["obj_token"]
                logger.info(f"Wiki document created: {result['wiki_url']}")
        else:
            # 否则创建普通云文档
            logger.info(f"Creating Feishu Cloud Document: {title}")
            document_id = self.create_document(doc_title, author, bili_url, body_content, tags=tags_str, description=description)
            if document_id:
                result["document_id"] = document_id
                result["document_url"] = f"https://www.feishu.cn/docx/{document_id}"
                logger.info(f"Cloud document created: {result['document_url']}")
        
        return result


# 便捷函数
def upload_to_feishu(video_data: dict) -> dict:
    """
    便捷函数：上传视频内容到飞书
    
    Args:
        video_data: 视频数据字典
        
    Returns:
        上传结果
    """
    uploader = FeishuUploader()
    return uploader.upload_video_content(video_data)


if __name__ == "__main__":
    # 测试代码
    test_data = {
        "bv_id": "BV1B1wMzrEWy",
        "title": "半岛电视台：约翰·米尔斯海默访谈",
        "author": "Web3天空之城",
        "created_at": datetime(2026, 3, 15, 21, 29, 30),
        "description": "这是一段关于国际关系的访谈视频",
        "video_labels": ["人物", "社会", "地缘政治"],
        "raw_language": "en",
        "raw_transcription": "This is a test transcription in English.",
        "processed_transcription": "这是一段测试的中文翻译内容。"
    }
    
    result = upload_to_feishu(test_data)
    print(f"Upload result: {result}")
