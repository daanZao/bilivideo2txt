# Bilibili Video to Text 项目设计文档

## 1. 项目概述

本项目旨在从Bilibili平台自动抓取指定用户的视频内容，提取音频并转换为文本，通过AI处理生成结构化的播客内容。系统支持多语言视频识别、自动翻译、标签筛选、状态驱动处理流程等功能。

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      定时任务调度器                           │
│                   (每天运行3-4次)                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   视频抓取模块 (bilibili-api + yt-dlp)        │
│  - 从Bilibili抓取指定用户视频列表                             │
│  - 提取视频元数据(标题、简介、作者、创建时间、标签)             │
│  - 下载音频(m4a格式，无需转换)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   状态驱动处理引擎                            │
│  - 状态0: 已获取视频信息                                      │
│  - 状态1: 标签命中待处理                                      │
│  - 状态2: 音频下载成功                                        │
│  - 状态3: 音频下载失败                                        │
│  - 状态4: 转录成功                                            │
│  - 状态5: 转录失败                                            │
│  - 状态6: 翻译成功                                            │
│  - 状态7: 翻译失败                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              语音识别模块 (faster-whisper) ✅ 已实现          │
│  - 调用RESTful API接口                                        │
│  - 音频转文本                                                 │
│  - 自动检测语言                                               │
│  - 支持标签特定的提示词                                       │
│  - Semaphore+线程池并发控制 ✅ 新增                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   翻译模块 ✅ 已实现                          │
│  - 非中文视频自动翻译                                         │
│  - 调用AI大模型API                                            │
│  - 保留说话人标识                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   飞书上传模块 ✅ 已实现                      │
│  - 创建云文档/Wiki页面                                        │
│  - 格式化内容（高亮块+译文）                                  │
│  - 自动添加视频元数据                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据存储模块                                │
│  - SQLite数据库                                               │
│  - 状态持久化                                                 │
│  - 支持断点续传                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 组件 | 技术选型 | 说明 | 状态 |
|------|---------|------|------|
| 视频列表抓取 | bilibili-api-python | Bilibili API封装库 | ✅ 已实现 |
| 视频标签获取 | bilibili-api-python | 视频标签API | ✅ 已实现 |
| 视频下载 | yt-dlp | 开源视频下载工具，支持Bilibili | ✅ 已实现 |
| 音频格式 | m4a | 原始音频格式，无需转换 | ✅ 已实现 |
| 标签筛选 | 字符串匹配 | 标签与目标分类匹配 | ✅ 已实现 |
| 状态管理 | SQLAlchemy + SQLite | 状态驱动处理流程 | ✅ 已实现 |
| AI分类 | 阿里云通义千问/OpenAI | 视频分类（已停用） | ⏸️ 已停用 |
| 语音识别 | faster-whisper | 高效的语音转文本引擎 | ✅ 已实现 |
| Whisper服务 | ahmetoner/whisper-asr-webservice | RESTful API封装 | ✅ 已实现 |
| 并发控制 | Semaphore + ThreadPoolExecutor | 限制并发请求数，管理任务队列 | ✅ 已实现 |
| 重试机制 | 指数退避 + 最大重试次数 | 自动重试失败任务 | ✅ 已实现 |
| 速度控制 | 可配置延迟 | bilibili-api/yt-dlp 抓取速度控制 | ✅ 已实现 |
| 语言检测 | 字符统计 | 基于Unicode范围检测 | ✅ 已实现 |
| 文本翻译 | 阿里云通义千问/OpenAI | 多语言翻译成中文 | ✅ 已实现 |
| 飞书云文档 | REST API | 飞书开放平台API | ✅ 已实现 |
| 飞书Wiki | REST API | 飞书知识库API | ✅ 已实现 |
| 数据库 | SQLite | 轻量级本地数据库 | ✅ 已实现 |
| 定时任务 | APScheduler | Python定时任务框架 | ⏳ 待实现 |
| 编程语言 | Python 3.9+ | 主要开发语言 | ✅ 已实现 |

## 3. 项目结构

```
bili-video2txt/
├── config.py                      # 配置文件
├── models.py                      # 数据库模型（SQLAlchemy）
├── fetcher.py                     # 视频抓取模块
├── video_processor.py             # 主处理器（状态驱动）✅ 新增
├── transcription_worker.py        # 并发转录工作器（Semaphore+线程池）✅ 新增
├── classifier.py                  # AI分类模块（已停用）
├── feishu_uploader.py             # 飞书文档上传模块
├── migrate_db.py                  # 数据库迁移脚本 ✅ 新增
├── requirements.txt               # Python依赖
├── .env.example                   # 环境变量示例文件
├── .gitignore                     # Git忽略文件
├── test_api.py                    # API连接测试脚本
├── test_whisper_api.py            # Whisper API测试脚本
├── test_transcribe_and_translate.py  # 转录翻译测试脚本
├── test_feishu_upload.py          # 飞书上传测试脚本
├── test_ytdlp_download.py         # yt-dlp下载测试脚本
├── test_single_video.py           # 单视频处理测试脚本
├── test_raw_audio.py              # 原始音频测试脚本
├── audio/                         # 音频存储目录（自动创建）
├── logs/                          # 日志目录（自动创建）
└── bili_video.db                  # SQLite数据库文件（自动创建）
```

## 4. 状态驱动处理流程

### 4.1 状态定义

| 状态值 | 状态名称 | 说明 |
|--------|---------|------|
| 0 | INFO_FETCHED | 已获取视频信息（初始状态） |
| 1 | TAG_MATCHED | 标签命中，需要后续处理 |
| 2 | AUDIO_SUCCESS | 音频下载成功 |
| 3 | AUDIO_FAILED | 音频下载失败 |
| 4 | TRANSCRIBE_SUCCESS | 转录成功 |
| 5 | TRANSCRIBE_FAILED | 转录失败 |
| 6 | TRANSLATE_SUCCESS | 翻译成功 |
| 7 | TRANSLATE_FAILED | 翻译失败 |

### 4.2 状态流转图

```
┌─────────────────┐
│  获取视频信息    │
│  procstate = 0  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     不匹配    ┌─────────────┐
│   标签匹配判断   │──────────────▶│    结束     │
│                 │               └─────────────┘
└────────┬────────┘
         │ 匹配
         ▼
┌─────────────────┐
│  procstate = 1  │
│  标签命中待处理  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    失败      ┌─────────────────┐
│   下载音频      │─────────────▶│  procstate = 3  │
│                 │              │  音频下载失败    │
└────────┬────────┘              └─────────────────┘
         │ 成功
         ▼
┌─────────────────┐
│  procstate = 2  │
│  音频下载成功    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    失败      ┌─────────────────┐
│   语音识别      │─────────────▶│  procstate = 5  │
│  (Whisper API)  │              │  转录失败        │
└────────┬────────┘              └─────────────────┘
         │ 成功
         ▼
┌─────────────────┐
│  procstate = 4  │
│   转录成功      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    失败      ┌─────────────────┐
│   翻译判断      │─────────────▶│  procstate = 7  │
│  (AI大模型)     │              │  翻译失败        │
└────────┬────────┘              └─────────────────┘
         │ 成功/无需翻译
         ▼
┌─────────────────┐
│  procstate = 6  │
│   翻译成功      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   上传飞书      │
│  (Wiki/云文档)  │
└─────────────────┘
```

### 4.3 主处理器 (video_processor.py)

**核心类：**

```python
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
    
    def run(self):
        """运行完整处理流程"""
        # Step 1: 获取所有用户的视频信息
        self._fetch_all_videos()
        
        # Step 2: 处理标签匹配和音频下载
        self._process_audio_download()
        
        # Step 3: 处理音频转录
        self._process_transcription()
        
        # Step 4: 处理翻译
        self._process_translation()
        
        # Step 5: 上传到飞书
        self._upload_to_feishu()
```

**处理步骤详解：**

1. **_fetch_all_videos()**: 获取视频信息
   - 遍历所有配置的用户
   - 获取视频列表和标签
   - 入库时设置 `procstate = 0`

2. **_process_audio_download()**: 标签匹配和音频下载
   - **_match_tags()**: 检查标签匹配，匹配则设置 `procstate = 1`
   - **_download_audios()**: 下载音频，成功则设置 `procstate = 2`，失败则设置 `procstate = 3`

3. **_process_transcription()**: 音频转录（并发处理）
   - 处理 `procstate = 2` 的视频（新任务）和 `procstate = 5` 的视频（重试任务）
   - 使用 **TranscriptionWorker** 进行并发转录
   - **Semaphore** 限制同时发送到 Whisper 的请求数（默认1）
   - **ThreadPoolExecutor** 管理等待处理的任务队列（默认5）
   - 成功则设置 `procstate = 4`，失败则设置 `procstate = 5`

4. **_process_translation()**: 文本翻译
   - 处理 `procstate = 4` 的视频（新任务）和 `procstate = 7` 的视频（重试任务）
   - 中文视频：直接使用原文
   - 英文视频：调用 AI 翻译
   - 成功则设置 `procstate = 6`，失败则设置 `procstate = 7`
   - 支持自动重试机制（最多3次）

5. **_upload_to_feishu()**: 上传飞书
   - 处理 `procstate = 6` 的视频
   - 创建格式化的飞书文档

## 5. 数据模型

### 5.1 视频信息表 (videos)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| bv_id | VARCHAR(20) | PRIMARY KEY | Bilibili视频BV号 |
| title | VARCHAR(500) | NOT NULL | 视频标题 |
| created_at | DATETIME | | 视频创建时间 |
| description | TEXT | | 视频简介 |
| author | VARCHAR(100) | NOT NULL | 视频作者 |
| category | VARCHAR(50) | | AI分类结果（已停用） |
| video_labels | JSON | | 视频标签数组 |
| audio_path | VARCHAR(500) | | 本地音频文件路径 |
| raw_language | VARCHAR(10) | | 原始语言代码 |
| raw_transcription | TEXT | | 原始转录文本 |
| processed_transcription | TEXT | | 处理后的文本（翻译后） |
| processed_at | DATETIME | | 处理完成时间 |
| status | VARCHAR(20) | DEFAULT 'pending' | 处理状态（文本） |
| procstate | INTEGER | DEFAULT 0 | 处理状态（数值）✅ 新增 |
| retry_count | INTEGER | DEFAULT 0 | 重试次数 ✅ 新增 |
| created_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |
| updated_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | 记录更新时间 |

### 5.2 状态值对照

| procstate | status | 说明 |
|-----------|--------|------|
| 0 | info_fetched | 已获取视频信息 |
| 1 | tag_matched | 标签命中待处理 |
| 2 | audio_downloaded | 音频下载成功 |
| 3 | audio_failed | 音频下载失败 |
| 4 | transcribed | 转录成功 |
| 5 | transcribe_failed | 转录失败 |
| 6 | completed | 翻译成功 |
| 7 | translate_failed | 翻译失败 |
| 6 | uploaded | 已上传飞书 |

## 6. 并发转录模块 (transcription_worker.py)

### 6.1 设计原理

由于 Whisper 转录音频较慢且音频长度不可预知，采用 **Semaphore + ThreadPoolExecutor** 实现并发控制：

- **Semaphore（信号量）**：限制同时发送到 Whisper 服务的请求数（默认1）
- **ThreadPoolExecutor（线程池）**：管理等待处理的任务队列（默认5个线程）

### 6.2 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    待转录视频列表                            │
│         [Video1, Video2, Video3, Video4, Video5...]         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   ThreadPoolExecutor                         │
│              线程池（管理等待的任务队列）                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ Thread1 │ │ Thread2 │ │ Thread3 │ │ Thread4 │ │Thread5 │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬────┘ │
│       └───────────┴───────────┴───────────┴────────────┘    │
│                           │                                  │
│                           ▼                                  │
│              ┌─────────────────────────┐                     │
│              │      Semaphore(1)       │                     │
│              │  限制并发请求数到Whisper │                     │
│              └───────────┬─────────────┘                     │
│                          │                                   │
│                          ▼                                   │
│              ┌─────────────────────────┐                     │
│              │    Whisper API Server   │                     │
│              │   (GPU资源限制，需保护)  │                     │
│              └─────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 核心类

```python
class TranscriptionWorker:
    """
    Whisper 转录工作器
    
    使用信号量限制同时发送到 Whisper 服务的请求数，
    使用线程池管理等待处理的任务队列。
    """
    
    def __init__(self, max_concurrency=1, pool_size=5):
        self.semaphore = threading.Semaphore(max_concurrency)
        self.executor = ThreadPoolExecutor(max_workers=pool_size)
    
    def submit_tasks(self, videos: List[Video], callback: Callable) -> Dict:
        """提交转录任务到线程池"""
        
    def _transcribe_with_semaphore(self, video: Video) -> Tuple[bool, dict]:
        """使用信号量保护的转录方法"""
```

### 6.4 配置参数

```python
WHISPER_CONFIG = {
    "concurrency": 1,        # 同时发送到 Whisper 的请求数
    "thread_pool_size": 5,   # 线程池大小（管理等待的任务）
    "timeout": 3000,         # 单个请求超时时间（秒）
}
```

**推荐配置：**
- `concurrency=1`：Whisper 服务通常受 GPU 资源限制，建议单线程
- `thread_pool_size=5`：可根据内存和预期并发量调整

### 6.5 日志示例

```
[Queue] Video BVxxx waiting for semaphore (current concurrency: 0/1)
[Start] Video BVxxx starting transcription (current active: 1)
[Success] Video BVxxx transcribed successfully
[Done] Video BVxxx transcription completed (active: 0)
[DB] Video BVxxx updated with transcription result
```

## 7. 重试机制

### 7.1 设计原理

系统支持自动重试失败的步骤，包括：
- **状态3（音频下载失败）**
- **状态5（转录失败）**
- **状态7（翻译失败）**

### 7.2 重试策略

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_RETRY_COUNT` | 3 | 最大重试次数 |
| `RETRY_DELAY` | 5秒 | 重试间隔（指数退避） |

### 7.3 重试流程

```
失败状态(3/5/7)
      │
      ▼
┌─────────────────┐
│ retry_count < 3 │──否──▶ 保持失败状态
└────────┬────────┘
         │ 是
         ▼
┌─────────────────┐
│ retry_count += 1│
│ 等待 5秒        │
└────────┬────────┘
         │
         ▼
   重新执行任务
         │
         ▼
   成功/失败判断
```

### 7.4 数据库字段

```python
retry_count = Column(Integer, default=0)  # 记录每个视频的重试次数
```

**重置规则：**
- 新任务开始时：`retry_count = 0`
- 任务成功时：`retry_count = 0`
- 任务失败时：`retry_count += 1`

## 8. 速度控制配置

### 8.1 配置项

```python
# 抓取速度控制
FETCH_CONFIG = {
    "bilibili_api_delay": 1.0,   # bilibili-api 抓取间隔（秒/条）
    "ytdlp_delay": 2.0,          # yt-dlp 下载间隔（秒/条）
}

# Whisper 服务配置
WHISPER_CONFIG = {
    "timeout": 3000,             # 请求超时时间（秒）
}
```

### 8.2 环境变量

```bash
# 抓取速度控制
BILIBILI_API_DELAY=1.0          # bilibili-api 抓取间隔（秒）
YTDLP_DELAY=2.0                 # yt-dlp 下载间隔（秒）

# Whisper 配置
WHISPER_TIMEOUT=3000            # Whisper 请求超时时间（秒）
WHISPER_CONCURRENCY=1           # Whisper 并发请求数
WHISPER_THREAD_POOL=5           # 线程池大小
```

### 8.3 使用场景

| 场景 | 推荐配置 |
|------|----------|
| 开发测试 | `BILIBILI_API_DELAY=0.5`, `YTDLP_DELAY=1.0` |
| 生产环境 | `BILIBILI_API_DELAY=2.0`, `YTDLP_DELAY=3.0` |
| 大规模抓取 | 增加延迟，避免触发反爬 |
| 本地 Whisper | `WHISPER_CONCURRENCY=1`, `WHISPER_THREAD_POOL=5` |
| 云端 Whisper | 根据服务端限制调整并发数 |

## 9. 飞书文档格式

### 9.1 文档结构

飞书文档包含两个主要块：

1. **高亮块 (Callout)** - 蓝色背景
   - 第一行：👤 作者：xxx  🔗 B站视频：链接
   - 第二行：🏷️ 标签：标签1, 标签2, ...
   - 第三行：📖 摘要：视频简介

2. **文本块 (Text)**
   - 视频译文内容

### 9.2 文档标题格式

```
【YYYYMMDD】视频标题
```

例如：`【20260315】半岛电视台：约翰·米尔斯海默访谈`

### 9.3 飞书上传模块

**核心方法：**

```python
class FeishuUploader:
    def upload_video_content(self, video_data: dict) -> dict:
        """
        上传视频内容到飞书
        
        Args:
            video_data: {
                'bv_id': BV号,
                'title': 标题,
                'author': 作者,
                'description': 简介,
                'video_labels': 标签列表,
                'raw_transcription': 原文,
                'processed_transcription': 译文,
                'created_at': 创建时间
            }
        
        Returns:
            {
                'success': True/False,
                'wiki_url': Wiki链接,
                'document_id': 文档ID
            }
        """
```

## 10. 配置模块

### 10.1 用户配置

```python
USER_CONFIGS = [
    {
        "name": "Web3天空之城",
        "url": "https://space.bilibili.com/351754674",
        "start_date": datetime(2026, 3, 11),
        "tags": ["科技", "政治", "人工智能", "机器人", "创业故事", "生产力", "管理"]
    }
]
```

### 10.2 标签配置

```python
TAG_CONFIGS = {
    "科技": {
        "whisper_prompt": "这是一段科技类视频...",
        "process_prompt": "你是一位科技内容编辑..."
    },
    "政治": {
        "whisper_prompt": "这是一段政治新闻...",
        "process_prompt": "你是一位时政新闻编辑..."
    },
    # ... 其他标签
}
```

### 10.3 服务配置

```python
# 抓取速度控制
FETCH_CONFIG = {
    "bilibili_api_delay": float(os.getenv("BILIBILI_API_DELAY", "1.0")),  # bilibili-api 抓取间隔（秒）
    "ytdlp_delay": float(os.getenv("YTDLP_DELAY", "2.0")),               # yt-dlp 下载间隔（秒）
}

# Whisper服务配置
WHISPER_CONFIG = {
    "api_url": os.getenv("WHISPER_API_URL", "http://localhost:9000"),
    "model": os.getenv("WHISPER_MODEL", "large-v3"),
    "language": os.getenv("WHISPER_LANGUAGE", "zh"),
    "timeout": int(os.getenv("WHISPER_TIMEOUT", "3000")),              # 请求超时时间（秒）
    "concurrency": int(os.getenv("WHISPER_CONCURRENCY", "1")),         # 并发请求数
    "thread_pool_size": int(os.getenv("WHISPER_THREAD_POOL", "5")),    # 线程池大小
}

# AI服务配置（用于翻译）
AI_CONFIG = {
    "api_key": os.getenv("AI_API_KEY", ""),
    "model": os.getenv("AI_MODEL", "gpt-3.5-turbo"),
    "base_url": os.getenv("AI_BASE_URL", ""),
}

# 飞书配置
FEISHU_CONFIG = {
    "app_id": os.getenv("FEISHU_APP_ID", ""),
    "app_secret": os.getenv("FEISHU_APP_SECRET", ""),
    "wiki_space_id": os.getenv("FEISHU_WIKI_SPACE_ID", ""),
    "folder_token": os.getenv("FEISHU_FOLDER_TOKEN", ""),
}

# 重试配置
MAX_RETRY_COUNT = int(os.getenv("MAX_RETRY_COUNT", "3"))  # 最大重试次数
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))          # 重试间隔（秒）
```

## 11. 安装和使用

### 11.1 安装依赖

```bash
pip install -r requirements.txt
```

### 11.2 配置环境变量

```bash
copy .env.example .env
```

编辑 `.env` 文件：
```
# AI服务配置（用于翻译）
AI_API_KEY=your-api-key-here
AI_MODEL=gpt-3.5-turbo
AI_BASE_URL=https://api.openai.com/v1

# Whisper服务配置
WHISPER_API_URL=http://localhost:9000
WHISPER_MODEL=large-v3
WHISPER_LANGUAGE=zh
WHISPER_TIMEOUT=3000              # 请求超时时间（秒）
WHISPER_CONCURRENCY=1             # 并发请求数（建议1，GPU限制）
WHISPER_THREAD_POOL=5             # 线程池大小

# 抓取速度控制
BILIBILI_API_DELAY=1.0            # bilibili-api 抓取间隔（秒）
YTDLP_DELAY=2.0                   # yt-dlp 下载间隔（秒）

# 重试配置
MAX_RETRY_COUNT=3                 # 最大重试次数
RETRY_DELAY=5                     # 重试间隔（秒）

# 飞书配置（可选）
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxx
FEISHU_WIKI_SPACE_ID=123456
FEISHU_FOLDER_TOKEN=AbCdEfGh
```

### 11.3 部署Whisper服务

```bash
docker run -d \
  --name whisper-asr \
  --gpus all \
  -p 9000:9000 \
  -e ASR_MODEL=large-v3 \
  ahmetoner/whisper-asr-webservice:latest
```

### 11.4 运行主程序

**首次运行（需要迁移数据库）：**
```bash
python migrate_db.py
python video_processor.py
```

**后续运行：**
```bash
python video_processor.py
```

## 12. 数据库迁移

### 12.1 迁移脚本 (migrate_db.py)

用于添加 `procstate` 和 `retry_count` 列到现有数据库：

```bash
python migrate_db.py
```

**功能：**
- 自动检测并添加 `procstate` 列
- 自动检测并添加 `retry_count` 列
- 根据现有 `status` 字段迁移数据状态
- 显示迁移后的状态分布统计

### 12.2 迁移规则

| 原 status | 新 procstate |
|-----------|--------------|
| completed | 6 |
| transcribed | 4 |
| downloaded | 2 |
| tag_matched | 1 |
| info_fetched | 0 |
| pending + audio_path | 2 |
| pending + no audio_path | 0 |

## 13. 测试脚本

| 脚本 | 功能 |
|------|------|
| test_api.py | 测试Bilibili API连接 |
| test_whisper_api.py | 测试Whisper API |
| test_transcribe_and_translate.py | 测试转录和翻译 |
| test_feishu_upload.py | 测试飞书上传 |
| test_ytdlp_download.py | 测试音频下载 |
| test_single_video.py | 单视频完整流程测试 |
| test_raw_audio.py | 测试原始音频处理 |

## 14. 注意事项

1. **状态持久化**：所有处理状态保存在数据库中，支持断点续传
2. **标签匹配**：标签匹配区分大小写，但配置会自动转为小写比较
3. **翻译成本**：非中文视频会调用AI API进行翻译，注意API调用成本
4. **Whisper服务**：需要单独部署faster-whisper服务，确保GPU资源充足
5. **飞书权限**：需要配置文档和Wiki相关权限才能正常上传
6. **频率限制**：遵守Bilibili的访问频率限制（可配置 `BILIBILI_API_DELAY` 和 `YTDLP_DELAY`）
7. **并发控制**：Whisper 转录使用 Semaphore 限制并发，保护 GPU 资源
8. **重试机制**：失败任务会自动重试，最多3次（可配置 `MAX_RETRY_COUNT`）

## 15. 常见问题

**Q: 如何查看当前处理状态？**
A: 直接查询数据库：`SELECT procstate, COUNT(*) FROM videos GROUP BY procstate`

**Q: 如何重新处理失败的视频？**
A: 修改对应视频的 `procstate` 为上一个成功状态，重新运行程序

**Q: 如何跳过某些状态？**
A: 可以单独调用处理器的某个方法，如只运行 `_process_transcription()`

**Q: 状态0和状态1的区别？**
A: 状态0表示刚入库，还未进行标签匹配；状态1表示标签已匹配，等待下载音频

**Q: 如何添加新的处理状态？**
A: 在 `VideoState` 类中添加新常量，并在相应处理方法中实现状态流转

**Q: 如何调整 Whisper 并发数？**
A: 修改环境变量 `WHISPER_CONCURRENCY`（默认1），建议根据 GPU 资源调整

**Q: 如何查看转录队列状态？**
A: 查看日志中的 `[Queue]` 和 `[Active]` 标记，或查询数据库 `retry_count` 字段

**Q: 重试次数超限后怎么办？**
A: 可以手动重置 `retry_count = 0` 并修改 `procstate` 到上一个成功状态

## 16. 更新日志

### 2026-03-18
- ✅ 添加并发转录模块（Semaphore + ThreadPoolExecutor）
- ✅ 实现自动重试机制（支持状态3/5/7）
- ✅ 添加速度控制配置（bilibili-api/yt-dlp 延迟）
- ✅ 添加 Whisper 超时和并发配置
- ✅ 添加 `retry_count` 数据库字段

### 2026-03-17
- ✅ 添加状态驱动处理流程（procstate）
- ✅ 实现数据库迁移脚本
- ✅ 重构主处理器为状态机模式
- ✅ 更新飞书上传格式（高亮块+文本块）
- ✅ 优化标签匹配和音频下载流程
