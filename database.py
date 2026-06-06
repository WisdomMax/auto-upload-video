import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. items 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_no INTEGER,
        title TEXT,
        description TEXT,
        coupang_url TEXT,
        short_url TEXT,
        original_video_path TEXT,
        r2_video_url TEXT,
        publish_status TEXT DEFAULT 'pending',
        publish_results TEXT,
        youtube_title TEXT,
        youtube_description TEXT,
        youtube_tags TEXT,
        sns_caption TEXT,
        dm_template TEXT,
        comment_reply TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. 하위 호환성을 위한 컬럼 추가 감지 로직
    alterations = [
        ("r2_video_url", "TEXT"),
        ("publish_status", "TEXT DEFAULT 'pending'"),
        ("publish_results", "TEXT"),
        ("youtube_trends", "TEXT")
    ]
    for col, col_type in alterations:
        try:
            cursor.execute(f"ALTER TABLE items ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # 이미 컬럼이 존재하는 경우 발생함
            
    # 3. settings 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# --- CRUD for Items ---

def create_item(product_no, title, description, coupang_url, original_video_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO items (product_no, title, description, coupang_url, original_video_path, publish_status)
    VALUES (?, ?, ?, ?, ?, 'pending')
    """, (product_no, title, description, coupang_url, original_video_path))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_item_r2_url(item_id, r2_video_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET r2_video_url = ? WHERE id = ?", (r2_video_url, item_id))
    conn.commit()
    conn.close()

def update_item_publish_results(item_id, publish_status, publish_results):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET publish_status = ?, publish_results = ? WHERE id = ?", (publish_status, publish_results, item_id))
    conn.commit()
    conn.close()

def update_item_coupang_urls(item_id, coupang_url, short_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET coupang_url = ?, short_url = ? WHERE id = ?", (coupang_url, short_url, item_id))
    conn.commit()
    conn.close()

def update_item_generated_contents(item_id, youtube_title, youtube_description, youtube_tags, sns_caption, dm_template, comment_reply):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE items 
    SET youtube_title = ?, youtube_description = ?, youtube_tags = ?, sns_caption = ?, dm_template = ?, comment_reply = ?
    WHERE id = ?
    """, (youtube_title, youtube_description, youtube_tags, sns_caption, dm_template, comment_reply, item_id))
    conn.commit()
    conn.close()

def update_item_youtube_trends(item_id, youtube_trends):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET youtube_trends = ? WHERE id = ?", (youtube_trends, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# --- Settings Management ---

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def get_all_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

# 모듈이 로드될 때 DB 초기화 자동 진행
init_db()
