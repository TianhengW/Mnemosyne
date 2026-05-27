# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyobjc-framework-Vision>=10.0",
#     "pyobjc-framework-Quartz>=10.0",
#     "pyobjc-framework-Cocoa>=10.0",
#     "Pillow>=10.0",
# ]
# ///

"""
Screen Monitor 守护进程 — 每 30 秒截图 + Apple Vision OCR，记录全部屏幕活动。

用法:
  uv run scripts/screen-monitor.py              # 前台运行（调试用）
  uv run scripts/screen-monitor.py --once       # 只运行一次（测试用）
  uv run scripts/screen-monitor.py --summary    # 生成今日摘要

由 launchd 管理为 KeepAlive 守护进程。
"""

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Force unbuffered output for launchd
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

CACHE_DIR = Path(os.path.expanduser("~/.cache/pa-screen-monitor"))
SCREENSHOTS_DIR = CACHE_DIR / "screenshots"
DB_PATH = CACHE_DIR / "ocr.db"
SCREENSHOT_RETENTION_DAYS = 7
OCR_RETENTION_DAYS = 30
CAPTURE_INTERVAL = 30


def init_db():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS screen_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            app_name TEXT,
            window_title TEXT,
            ocr_text TEXT,
            screenshot_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_timestamp ON screen_log(timestamp);
        CREATE VIRTUAL TABLE IF NOT EXISTS screen_fts USING fts5(
            ocr_text, window_title, content=screen_log, content_rowid=id
        );
        CREATE TRIGGER IF NOT EXISTS screen_log_ai AFTER INSERT ON screen_log BEGIN
            INSERT INTO screen_fts(rowid, ocr_text, window_title)
            VALUES (new.id, new.ocr_text, new.window_title);
        END;
    """)
    conn.close()


def get_active_window() -> tuple[str, str]:
    """Get the active application name and window title via osascript."""
    try:
        app_script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        result = subprocess.run(
            ["osascript", "-e", app_script],
            capture_output=True, text=True, timeout=5
        )
        app_name = result.stdout.strip()

        title_script = """
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            tell frontApp
                if (count of windows) > 0 then
                    return name of front window
                else
                    return ""
                end if
            end tell
        end tell
        """
        result2 = subprocess.run(
            ["osascript", "-e", title_script],
            capture_output=True, text=True, timeout=5
        )
        window_title = result2.stdout.strip()

        return app_name, window_title
    except Exception:
        return "", ""


def take_screenshot(path: str) -> bool:
    """Take a silent screenshot using macOS screencapture."""
    try:
        subprocess.run(
            ["screencapture", "-x", "-C", path],
            timeout=10, check=True
        )
        return Path(path).exists()
    except Exception:
        return False


def ocr_image(image_path: str) -> str:
    """Run Apple Vision OCR on an image file."""
    try:
        import Vision
        import Quartz

        image_url = Quartz.CFURLCreateWithFileSystemPath(
            None, image_path, Quartz.kCFURLPOSIXPathStyle, False
        )
        image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
        if not image_source:
            return ""

        cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
        if not cg_image:
            return ""

        request_handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
            cg_image, None
        )

        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setRecognitionLanguages_(["zh-Hans", "en-US"])
        request.setUsesLanguageCorrection_(True)

        success = request_handler.performRequests_error_([request], None)
        if not success[0]:
            return ""

        results = request.results()
        if not results:
            return ""

        texts = []
        for observation in results:
            candidate = observation.topCandidates_(1)
            if candidate:
                texts.append(candidate[0].string())

        return "\n".join(texts)
    except Exception as e:
        return f"[OCR Error: {e}]"


def cleanup_old_screenshots():
    """Delete screenshots older than retention period."""
    cutoff = datetime.now() - timedelta(days=SCREENSHOT_RETENTION_DAYS)
    if not SCREENSHOTS_DIR.exists():
        return

    for day_dir in SCREENSHOTS_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(day_dir.name, "%Y-%m-%d")
            if dir_date < cutoff:
                shutil.rmtree(day_dir)
        except ValueError:
            continue


def cleanup_old_ocr():
    """Delete OCR records older than retention period."""
    cutoff = (datetime.now() - timedelta(days=OCR_RETENTION_DAYS)).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("DELETE FROM screen_log WHERE timestamp < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


def capture_once():
    """Perform one capture cycle: screenshot → OCR → store."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    timestamp = now.isoformat()

    day_dir = SCREENSHOTS_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = str(day_dir / f"{time_str}.png")

    # Get active window info
    app_name, window_title = get_active_window()

    # Take screenshot
    if not take_screenshot(screenshot_path):
        return

    # OCR
    ocr_text = ocr_image(screenshot_path)

    # Store in database
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO screen_log (timestamp, app_name, window_title, ocr_text, screenshot_path) VALUES (?, ?, ?, ?, ?)",
            (timestamp, app_name, window_title, ocr_text, screenshot_path)
        )
        conn.commit()
    finally:
        conn.close()


def generate_today_summary() -> str:
    """Generate a summary of today's screen activity."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        # App usage time (approximate: each record = 30s)
        app_rows = conn.execute(
            "SELECT app_name, COUNT(*) * 30 as seconds FROM screen_log WHERE timestamp LIKE ? GROUP BY app_name ORDER BY seconds DESC",
            (f"{today}%",)
        ).fetchall()

        # Total records
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM screen_log WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()

        # Unique window titles (papers, files, etc.)
        titles = conn.execute(
            "SELECT DISTINCT window_title FROM screen_log WHERE timestamp LIKE ? AND window_title != ''",
            (f"{today}%",)
        ).fetchall()

    finally:
        conn.close()

    total_records = total["cnt"] if total else 0
    total_hours = total_records * 30 / 3600

    summary = f"## 📺 今日屏幕活动摘要 ({today})\n\n"
    summary += f"**总记录时间**: {total_hours:.1f} 小时 ({total_records} 条记录)\n\n"

    if app_rows:
        summary += "### App 使用时间\n"
        summary += "| 应用 | 时间 |\n|------|------|\n"
        for row in app_rows[:10]:
            minutes = row["seconds"] / 60
            if minutes >= 1:
                summary += f"| {row['app_name']} | {minutes:.0f} 分钟 |\n"

    if titles:
        summary += "\n### 活跃窗口标题\n"
        for t in titles[:20]:
            if t["window_title"]:
                summary += f"- {t['window_title'][:80]}\n"

    return summary


def main():
    parser = argparse.ArgumentParser(description="PA Screen Monitor")
    parser.add_argument("--once", action="store_true", help="只运行一次（测试）")
    parser.add_argument("--summary", action="store_true", help="生成今日摘要")
    args = parser.parse_args()

    init_db()

    if args.summary:
        print(generate_today_summary())
        return

    if args.once:
        print("[Screen Monitor] 单次捕获...")
        capture_once()
        print("[OK] 完成")
        return

    # Daemon mode
    print(f"[Screen Monitor] 启动守护模式 (间隔 {CAPTURE_INTERVAL}s)")
    print(f"  截图目录: {SCREENSHOTS_DIR}")
    print(f"  数据库: {DB_PATH}")
    print(f"  截图保留: {SCREENSHOT_RETENTION_DAYS} 天")

    last_cleanup = time.time()
    cleanup_interval = 3600  # 每小时清理一次

    while True:
        try:
            capture_once()
        except Exception as e:
            print(f"[ERROR] 捕获失败: {e}")

        # Periodic cleanup
        if time.time() - last_cleanup > cleanup_interval:
            try:
                cleanup_old_screenshots()
                cleanup_old_ocr()
                last_cleanup = time.time()
            except Exception as e:
                print(f"[ERROR] 清理失败: {e}")

        time.sleep(CAPTURE_INTERVAL)


if __name__ == "__main__":
    main()
