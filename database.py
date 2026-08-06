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
        ("youtube_trends", "TEXT"),
        ("product_code", "TEXT"),
        ("scheduled_at", "TEXT"),
        ("video_hash", "TEXT")
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

    # 4. agent_logs 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type TEXT,
        status TEXT,
        message TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 5. recommended_items 테이블 생성
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommended_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        coupang_url TEXT NOT NULL,
        original_image_url TEXT,
        price INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 6. ig_processed_users 테이블 생성 (게시물/릴스별 유저 중복 응답 방지 DB 락)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ig_processed_users (
        username TEXT NOT NULL,
        reel_id TEXT NOT NULL,
        dm_sent INTEGER DEFAULT 0,
        reply_posted INTEGER DEFAULT 0,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (username, reel_id)
    )
    """)
    
    conn.commit()
    conn.close()

def extract_reel_shortcode(reel_id: str) -> str:
    if not reel_id:
        return ""
    import re
    m = re.search(r'/reel(?:s)?/([^/?#]+)', str(reel_id))
    if m:
        return m.group(1).strip()
    return str(reel_id).strip().strip('/')

def get_ig_user_status_for_reel(username: str, reel_id: str) -> dict:
    """유저 및 릴스별 DM 발송 여부(dm_sent)와 대댓글 작성 여부(reply_posted)를 독립 조회"""
    if not username or not reel_id:
        return {"dm_sent": False, "reply_posted": False, "exists": False}
    shortcode = extract_reel_shortcode(reel_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dm_sent, reply_posted FROM ig_processed_users WHERE LOWER(username) = LOWER(?) AND reel_id = ?", (username.strip(), shortcode))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"dm_sent": bool(row['dm_sent']), "reply_posted": bool(row['reply_posted']), "exists": True}
        return {"dm_sent": False, "reply_posted": False, "exists": False}
    except Exception:
        conn.close()
        return {"dm_sent": False, "reply_posted": False, "exists": False}

def update_ig_user_dm_status(username: str, reel_id: str, dm_sent: bool):
    """DM 발송 상태 독립적으로 DB에 기록/갱신"""
    if not username or not reel_id:
        return
    shortcode = extract_reel_shortcode(reel_id)
    uname_clean = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT reply_posted FROM ig_processed_users WHERE username = ? AND reel_id = ?", (uname_clean, shortcode))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE ig_processed_users SET dm_sent = ?, processed_at = CURRENT_TIMESTAMP WHERE username = ? AND reel_id = ?", (1 if dm_sent else 0, uname_clean, shortcode))
        else:
            cursor.execute("INSERT INTO ig_processed_users (username, reel_id, dm_sent, reply_posted) VALUES (?, ?, ?, 0)", (uname_clean, shortcode, 1 if dm_sent else 0))
        conn.commit()
    except Exception as e:
        print(f"[DB Error update_ig_user_dm_status] {e}")
    conn.close()

def update_ig_user_reply_status(username: str, reel_id: str, reply_posted: bool):
    """대댓글 작성 상태 독립적으로 DB에 기록/갱신"""
    if not username or not reel_id:
        return
    shortcode = extract_reel_shortcode(reel_id)
    uname_clean = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dm_sent FROM ig_processed_users WHERE username = ? AND reel_id = ?", (uname_clean, shortcode))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE ig_processed_users SET reply_posted = ?, processed_at = CURRENT_TIMESTAMP WHERE username = ? AND reel_id = ?", (1 if reply_posted else 0, uname_clean, shortcode))
        else:
            cursor.execute("INSERT INTO ig_processed_users (username, reel_id, dm_sent, reply_posted) VALUES (?, ?, 0, ?)", (uname_clean, shortcode, 1 if reply_posted else 0))
        conn.commit()
    except Exception as e:
        print(f"[DB Error update_ig_user_reply_status] {e}")
    conn.close()

def is_ig_user_processed_for_reel(username: str, reel_id: str) -> bool:
    status = get_ig_user_status_for_reel(username, reel_id)
    # DM과 대댓글이 모두 완결된 경우 true
    return status['dm_sent'] and status['reply_posted']

def mark_ig_user_processed_for_reel(username: str, reel_id: str, dm_sent: bool = True, reply_posted: bool = True):
    if not username or not reel_id:
        return
    shortcode = extract_reel_shortcode(reel_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO ig_processed_users (username, reel_id, dm_sent, reply_posted, processed_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(username, reel_id) DO UPDATE SET
            dm_sent = excluded.dm_sent,
            reply_posted = excluded.reply_posted,
            processed_at = CURRENT_TIMESTAMP
        """, (username.strip().lower(), shortcode, 1 if dm_sent else 0, 1 if reply_posted else 0))
        conn.commit()
    except Exception:
        pass
    conn.close()

# --- CRUD for Items ---

def create_item(product_no, title, description, coupang_url, original_video_path, product_code=None, video_hash=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO items (product_no, title, description, coupang_url, original_video_path, publish_status, product_code, video_hash)
    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (product_no, title, description, coupang_url, original_video_path, product_code, video_hash))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    backup_db()  # 데이터 생성 후 백업 실행
    return item_id

def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items ORDER BY product_no ASC, id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_items_ordered_by_product_no_asc():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items ORDER BY product_no ASC, id ASC")
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
def get_item_by_product_no(product_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        no_val = int(product_no)
        cursor.execute("SELECT * FROM items WHERE product_no = ?", (no_val,))
    except ValueError:
        cursor.execute("SELECT * FROM items WHERE product_code = ? OR product_no = ?", (product_no, product_no))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_next_product_no():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(product_no) as max_no FROM items")
    row = cursor.fetchone()
    conn.close()
    if row and row['max_no'] is not None:
        return int(row['max_no']) + 1
    return 1

def get_next_product_code(category_prefix):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_code FROM items WHERE product_code LIKE ? ORDER BY product_code DESC LIMIT 1", (f"{category_prefix}%",))
    row = cursor.fetchone()
    conn.close()
    if row and row['product_code']:
        last_code = row['product_code']
        try:
            num_part = int(last_code[1:])
            next_num = num_part + 1
            return f"{category_prefix}{next_num:05d}"
        except ValueError:
            pass
    return f"{category_prefix}00001"

def get_item_by_code(product_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE product_code = ?", (product_code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_item_by_video_hash(video_hash):
    if not video_hash:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE video_hash = ?", (video_hash,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_item_scheduled_at(item_id, scheduled_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET scheduled_at = ? WHERE id = ?", (scheduled_at, item_id))
    conn.commit()
    conn.close()

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
    backup_db()  # 정보 업데이트 후 백업 실행

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
    backup_db()  # 데이터 삭제 후 백업 실행

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

# --- CRUD for Agent Logs ---

def create_agent_log(task_type, status, message, details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO agent_logs (task_type, status, message, details)
    VALUES (?, ?, ?, ?)
    """, (task_type, status, message, details))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_agent_logs(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- CRUD for Recommended Items ---

def create_recommended_item(product_name, coupang_url, original_image_url, price):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO recommended_items (product_name, coupang_url, original_image_url, price, status)
    VALUES (?, ?, ?, ?, 'pending')
    """, (product_name, coupang_url, original_image_url, price))
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id

def get_recommended_items(status="pending"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommended_items WHERE status = ? ORDER BY created_at DESC", (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recommended_item(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommended_items WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_recommendation_status(rec_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE recommended_items SET status = ? WHERE id = ?", (status, rec_id))
    conn.commit()
    conn.close()

def delete_recommended_item(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recommended_items WHERE id = ?", (rec_id,))
    conn.commit()
    conn.close()

# --- Auto Backup & Integrity Restoration System ---

def backup_db():
    try:
        import shutil
        from datetime import datetime
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(base_dir, "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # 현재 DB 파일이 존재하고 크기가 유효할 때만 백업
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"db_backup_{timestamp}.sqlite")
            shutil.copy2(DB_PATH, backup_path)
            
            # 백업 파일 보관 개수 제한 (최대 20개)
            backups = sorted(
                [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("db_backup_") and f.endswith(".sqlite")],
                key=os.path.getmtime
            )
            while len(backups) > 20:
                old_backup = backups.pop(0)
                os.remove(old_backup)
    except Exception as e:
        print(f"[DB Backup Error] {e}")

def auto_restore_if_needed():
    try:
        import shutil
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(base_dir, "db_backups")
        
        current_count = 0
        if os.path.exists(DB_PATH):
            try:
                # sqlite 커넥션을 직접 맺어 테스트 (재귀 임포트 방지)
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as cnt FROM items")
                current_count = cursor.fetchone()['cnt']
                conn.close()
            except Exception:
                current_count = -1  # DB 파일 깨짐
        else:
            current_count = -1  # DB 파일 없음

        # DB가 깨졌거나, 상품 개수가 비정상적으로 5개 미만인 경우 복구 동작 가동
        if current_count < 5:
            if os.path.exists(backup_dir):
                backups = sorted(
                    [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("db_backup_") and f.endswith(".sqlite")],
                    key=os.path.getmtime,
                    reverse=True
                )
                if backups:
                    latest_backup = backups[0]
                    # 백업 파일 정밀 검증
                    conn_bak = sqlite3.connect(latest_backup)
                    cur_bak = conn_bak.cursor()
                    cur_bak.execute("SELECT COUNT(*) as cnt FROM items")
                    bak_count = cur_bak.fetchone()[0]
                    conn_bak.close()
                    
                    if bak_count > current_count:
                        shutil.copy2(latest_backup, DB_PATH)
                        print(f"🚨 [DB 자동 복구 성공] 손상/누락된 DB를 {os.path.basename(latest_backup)} 파일로부터 복구했습니다. (상품 개수: {bak_count}개)")
    except Exception as e:
        print(f"[DB Auto Recovery Error] {e}")

# 모듈이 로드될 때 안전 무결성 검증 후 DB 초기화 진행
auto_restore_if_needed()
init_db()
