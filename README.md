# 🎬 BiliVideo2Txt

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-BSD--3--Clause-green.svg" alt="License: BSD-3-Clause">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
</p>

<p align="center">
  <b>自动抓取 Bilibili 视频，AI 转录翻译，一键同步到飞书文档</b>
</p>

<p align="center">
  <a href="#-功能特性">功能特性</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-工作流程">工作流程</a> •
  <a href="#-配置说明">配置说明</a> •
  <a href="doc/doc.md">详细文档</a>
</p>

---

## ✨ 功能特性

- 🤖 **全自动处理** - 从视频抓取到飞书上传，全程无需人工干预
- 🎯 **智能标签筛选** - 自动识别视频标签，只处理感兴趣的内容
- 🌍 **多语言支持** - 自动检测语言，非中文视频智能翻译
- ⚡ **并发转录** - Semaphore + 线程池，高效利用 Whisper 服务
- 🔄 **自动重试** - 失败任务自动重试，确保数据完整性
- 📊 **状态驱动** - 8 种处理状态，随时掌握进度，支持断点续传
- 📄 **飞书集成** - 自动生成格式化文档，支持 Wiki 和云文档

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/daanZao/bilivideo2txt.git
cd bilivideo2txt
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

### 4. 部署 Whisper 服务

```bash
docker run -d \
  --name whisper-asr \
  --gpus all \
  -p 9000:9000 \
  -e ASR_MODEL=large-v3 \
  ahmetoner/whisper-asr-webservice:latest
```

### 5. 运行

```bash
# 首次运行（需要迁移数据库）
python migrate_db.py

# 启动处理
python video_processor.py
```

## 📋 工作流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  抓取视频    │ → │  下载音频    │ → │  Whisper转录 │ → │  AI翻译     │
│  (bilibili) │    │  (yt-dlp)   │    │  (并发处理)  │    │  (自动检测)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                  ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   完成      │ ← │  飞书上传    │ ← │  格式化内容  │ ← │  生成译文   │
│             │    │  (Wiki/文档)│    │  (高亮块)   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## ⚙️ 配置说明

### 基础配置

```python
# 监控的 Bilibili 用户
USER_CONFIGS = [
    {
        "name": "Web3天空之城",
        "url": "https://space.bilibili.com/351754674",
        "tags": ["科技", "政治", "人工智能"]
    }
]
```

### 环境变量

```bash
# AI 翻译服务
AI_API_KEY=your-api-key
AI_MODEL=gpt-3.5-turbo

# Whisper 服务
WHISPER_API_URL=http://localhost:9000
WHISPER_CONCURRENCY=1        # 并发请求数
WHISPER_THREAD_POOL=5        # 线程池大小

# 飞书（可选）
FEISHU_APP_ID=your-app-id
FEISHU_APP_SECRET=your-secret
FEISHU_WIKI_SPACE_ID=your-space-id
```

## 🏗️ 项目结构

```
bilivideo2txt/
├── video_processor.py        # 主处理器（状态驱动）
├── transcription_worker.py   # 并发转录工作器
├── fetcher.py                # 视频抓取模块
├── feishu_uploader.py        # 飞书上传模块
├── config.py                 # 配置文件
├── models.py                 # 数据库模型
└── doc/
    └── doc.md                # 📖 详细文档
```

## 📊 处理状态

| 状态 | 说明 |
|------|------|
| 0 | 已获取视频信息 |
| 1 | 标签命中待处理 |
| 2 | 音频下载成功 |
| 3 | 音频下载失败（可重试）|
| 4 | 转录成功 |
| 5 | 转录失败（可重试）|
| 6 | 翻译成功 |
| 7 | 翻译失败（可重试）|

## 🛠️ 技术栈

- **视频抓取**: bilibili-api-python + yt-dlp
- **语音识别**: faster-whisper (Docker)
- **文本翻译**: OpenAI / 阿里云通义千问
- **文档存储**: 飞书云文档 / Wiki
- **数据库**: SQLite + SQLAlchemy
- **并发控制**: Semaphore + ThreadPoolExecutor

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目基于 [BSD-3-Clause](LICENSE) 许可证开源。

## 🙏 致谢

- [bilibili-api-python](https://github.com/Nemo2011/bilibili-api) - Bilibili API 封装
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载工具
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - 语音识别引擎
- [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice) - Whisper API 服务

---

<p align="center">
  如果这个项目对你有帮助，请给个 ⭐ Star！
</p>

<p align="center">
  <a href="doc/doc.md">📖 查看详细文档</a>
</p>
