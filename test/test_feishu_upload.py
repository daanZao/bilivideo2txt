"""
测试飞书云文档和Wiki上传功能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import logging
from datetime import datetime

from feishu_uploader import FeishuUploader, upload_to_feishu

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_create_document():
    """测试创建云文档"""
    logger.info("=" * 60)
    logger.info("测试创建飞书云文档")
    logger.info("=" * 60)
    
    uploader = FeishuUploader()
    
    if not uploader.access_token:
        logger.error("❌ Feishu未配置，请先设置环境变量")
        print("\n" + "=" * 60)
        print("环境变量配置说明：")
        print("=" * 60)
        print("""
请在 .env 文件中添加以下配置：

# 飞书配置
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxx
FEISHU_WIKI_SPACE_ID=7618058725593402306
FEISHU_FOLDER_TOKEN=（可选）

获取方式：
1. 访问 https://open.feishu.cn/
2. 创建企业自建应用
3. 在"凭证与基础信息"中获取 App ID 和 App Secret
4. 在"权限管理"中添加 docx 和 wiki 相关权限
5. 发布应用并获取管理员审核
6. 打开目标Wiki空间，从URL中获取 space_id
        """)
        return
    
    # 测试创建文档
    title = f"测试文档 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    content = """# 测试文档

这是一份测试文档。

## 测试内容

- 项目1
- 项目2
- 项目3

## 总结

测试完成！
"""
    
    # 如果配置了Wiki空间，直接在Wiki中创建文档
    if uploader.wiki_space_id:
        logger.info(f"\n测试在Wiki空间中创建文档: {uploader.wiki_space_id}")
        wiki_result = uploader.create_wiki_document(title, "", "", content)
        if wiki_result:
            logger.info(f"✅ Wiki文档创建成功!")
            logger.info(f"Node Token: {wiki_result['node_token']}")
            logger.info(f"Obj Token: {wiki_result['obj_token']}")
            logger.info(f"Wiki链接: https://www.feishu.cn/wiki/{wiki_result['node_token']}")
        else:
            logger.error("❌ Wiki文档创建失败")
    else:
        # 创建普通云文档
        document_id = uploader.create_document(title, "", "", content)
        
        if document_id:
            logger.info(f"✅ 云文档创建成功!")
            logger.info(f"Document ID: {document_id}")
            logger.info(f"文档链接: https://www.feishu.cn/docx/{document_id}")
        else:
            logger.error("❌ 云文档创建失败")


def test_upload_video_content():
    """测试上传视频内容"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试上传视频内容到飞书")
    logger.info("=" * 60)
    
    uploader = FeishuUploader()
    
    if not uploader.access_token:
        logger.error("❌ Feishu未配置，跳过测试")
        return
    
    # 测试数据
    test_data = {
        "bv_id": "BV1B1wMzrEWy",
        "title": "半岛电视台：约翰·米尔斯海默访谈测试",
        "author": "Web3天空之城",
        "created_at": datetime(2026, 3, 15, 21, 29, 30),
        "description": "这是一段关于国际关系的访谈视频，测试飞书上传功能。",
        "video_labels": ["人物", "社会", "地缘政治", "测试"],
        "raw_language": "en",
        "raw_transcription": """This is a test transcription.

John Mearsheimer: This is a test of the transcription system.

Host: Thank you for joining us today.

John Mearsheimer: It's my pleasure to be here.""",
        "processed_transcription": """这是一段测试转录。

约翰·米尔斯海默：这是对转录系统的测试。

主持人：感谢您今天加入我们。

约翰·米尔斯海默：很高兴来到这里。"""
    }
    
    result = uploader.upload_video_content(test_data)
    
    if result.get("success"):
        logger.info(f"✅ 视频内容上传成功!")
        logger.info(f"BV号: {result.get('bv_id')}")
        logger.info(f"标题: {result.get('title')}")
        if result.get("document_url"):
            logger.info(f"云文档链接: {result['document_url']}")
        if result.get("wiki_url"):
            logger.info(f"Wiki链接: {result['wiki_url']}")
    else:
        logger.error(f"❌ 上传失败: {result.get('error')}")


def show_help():
    """显示配置帮助"""
    print("\n" + "=" * 60)
    print("飞书API配置帮助")
    print("=" * 60)
    print("""
1. 访问飞书开放平台
   https://open.feishu.cn/

2. 创建企业自建应用
   - 点击"创建企业自建应用"
   - 填写应用名称和描述

3. 获取应用凭证
   - 进入应用详情页
   - 在"凭证与基础信息"中获取 App ID 和 App Secret

4. 配置权限
   进入"权限管理"，添加以下权限：
   
   云文档权限：
   - docx:document:create (创建文档)
   - docx:document:read (读取文档)
   - docx:document:write (写入文档)
   
   Wiki权限：
   - wiki:space:read (读取知识空间)
   - wiki:space:write (写入知识空间)
   - wiki:page:read (读取页面)
   - wiki:page:create (创建页面)

5. 发布应用
   - 进入"版本管理与发布"
   - 创建版本并发布
   - 让管理员审核通过

6. 获取Wiki Space ID
   - 打开目标Wiki空间
   - 从URL中获取: https://www.feishu.cn/wiki/space/{space_id}
   - 例如: 7618058725593402306

7. 配置环境变量
   在 .env 文件中添加：
   
   FEISHU_APP_ID=cli_xxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxx
   FEISHU_WIKI_SPACE_ID=7618058725593402306

8. 运行测试
   python test_feishu_upload.py
""")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_help()
        sys.exit(0)
    
    logger.info("开始测试飞书上传功能...")
    
    # 测试1: 创建云文档
    test_create_document()
    
    # 测试2: 上传视频内容
    test_upload_video_content()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)
