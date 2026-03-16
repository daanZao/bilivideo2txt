from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Integer, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import config

Base = declarative_base()


class UnicodeJSON(TypeDecorator):
    """自定义JSON类型，确保中文字符不被转义为ASCII"""
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value

class Video(Base):
    __tablename__ = "videos"
    
    bv_id = Column(String(20), primary_key=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    author = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    video_labels = Column(UnicodeJSON, nullable=True)
    audio_path = Column(String(500), nullable=True)
    raw_language = Column(String(10), nullable=True)
    raw_transcription = Column(Text, nullable=True)
    processed_transcription = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    # 处理状态: 0=已获取信息, 1=标签命中待处理, 2=音频下载成功, 3=音频下载失败, 4=转录成功, 5=转录失败, 6=翻译成功, 7=翻译失败
    procstate = Column(Integer, default=0)
    # 重试次数（用于失败状态）
    retry_count = Column(Integer, default=0)
    created_time = Column(DateTime, default=datetime.now)
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Video(bv_id={self.bv_id}, title={self.title}, status={self.status}, procstate={self.procstate})>"

engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(engine)
    print("Database initialized successfully")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
