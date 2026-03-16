"""
数据库迁移脚本
添加 procstate 列到现有数据库
"""

import sqlite3
import sys
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "bili_video.db"


def migrate_database():
    """迁移数据库，添加 procstate 和 retry_count 列"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("New database will be created with the new schema.")
        return True
    
    print(f"Migrating database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查现有列
        cursor.execute("PRAGMA table_info(videos)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # 添加 procstate 列（如果不存在）
        if 'procstate' not in column_names:
            print("Adding 'procstate' column...")
            cursor.execute("ALTER TABLE videos ADD COLUMN procstate INTEGER DEFAULT 0")
            
            # 根据现有 status 字段迁移数据
            print("Migrating existing data to procstate...")
            cursor.execute("""
                UPDATE videos 
                SET procstate = CASE 
                    WHEN status = 'completed' THEN 6
                    WHEN status = 'transcribed' THEN 4
                    WHEN status = 'downloaded' THEN 2
                    WHEN status = 'tag_matched' THEN 1
                    WHEN status = 'info_fetched' THEN 0
                    WHEN status = 'pending' AND audio_path IS NOT NULL THEN 2
                    WHEN status = 'pending' AND audio_path IS NULL THEN 0
                    ELSE 0
                END
            """)
        else:
            print("Column 'procstate' already exists, skipping.")
        
        # 添加 retry_count 列（如果不存在）
        if 'retry_count' not in column_names:
            print("Adding 'retry_count' column...")
            cursor.execute("ALTER TABLE videos ADD COLUMN retry_count INTEGER DEFAULT 0")
        else:
            print("Column 'retry_count' already exists, skipping.")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # 显示统计
        cursor.execute("SELECT procstate, COUNT(*) FROM videos GROUP BY procstate")
        stats = cursor.fetchall()
        print("\nState distribution after migration:")
        state_names = {
            0: "Info Fetched",
            1: "Tag Matched",
            2: "Audio Downloaded",
            3: "Audio Failed",
            4: "Transcribed",
            5: "Transcribe Failed",
            6: "Translated",
            7: "Translate Failed"
        }
        for state, count in stats:
            print(f"  State {state} ({state_names.get(state, 'Unknown')}): {count} videos")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        conn.close()
        return False


def main():
    print("=" * 60)
    print("Database Migration Tool")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n✅ Migration completed!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
