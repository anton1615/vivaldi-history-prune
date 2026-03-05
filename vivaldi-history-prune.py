# ==============================================================================
# Vivaldi History Pruning Script / Vivaldi 歷史紀錄優化腳本
#
# Features / 功能特色:
# 1. Auto-backup before execution / 每次執行前自動備份 History 檔案
#    Example / 例如：History.backup.2025-12-22_10-25-10
#
# 2. Clean redundant visits / 清理多餘訪問記錄
#    Keep only the latest visit per unique URL / 每個 URL 只保留最新一次訪問記錄
#
# 3. Update urls table / 更新 urls 表格
#    Set visit_count to 1 and fix last_visit_time
#    將 visit_count 設為 1，並修正 last_visit_time
#
# 4. VACUUM database / 執行 VACUUM 壓縮資料庫
#
# 5. Generate log file / 產生日誌檔案
#    Contains execution summary and Top 10 domains by unique URL count
#    包含執行摘要與 Top 10 域名統計
#
# IMPORTANT / 重要提醒:
# - Fully close Vivaldi before running / 執行前請務必完全關閉 Vivaldi
# - Requires psutil module / 需要 psutil 模組
#   Install with / 安裝指令：pip install psutil
# ==============================================================================

import sqlite3
import shutil
import os
import sys
from datetime import datetime
from collections import Counter
from urllib.parse import urlparse

try:
    import psutil
except ImportError:
    print("=" * 60)
    print("Error: psutil module not installed!")
    print("錯誤：未安裝 psutil 模組！")
    print("=" * 60)
    print("\nPlease run the following command to install:")
    print("請執行以下指令安裝：")
    print("    pip install psutil")
    print("\nThen run this script again.")
    print("安裝完成後再重新執行本腳本。")
    input("\nPress any key to exit / 按任意鍵結束程式... ")
    sys.exit(1)

history_path = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Vivaldi", "User Data", "Default", "History"
)

if not os.path.exists(history_path):
    print("=" * 60)
    print("Error: History file not found!")
    print("錯誤：找不到 History 檔案！")
    print("=" * 60)
    print(f"\nPath / 路徑: {history_path}")
    print("\nPlease check if the path is correct.")
    print("請檢查路徑是否正確。")
    input("\nPress any key to exit / 按任意鍵結束程式... ")
    sys.exit(1)

file_size_mb = os.path.getsize(history_path) / (1024 * 1024)
print("=" * 60)
print(f"Current History size / History 檔案目前大小: {file_size_mb:.2f} MB")
print("=" * 60)


def is_vivaldi_running():
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "vivaldi" in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


print("\nChecking if Vivaldi is fully closed...")
print("正在檢查 Vivaldi 是否已完全關閉...")

if is_vivaldi_running():
    print("\n" + "!" * 60)
    print("WARNING: Vivaldi is still running (including background processes)!")
    print("警告：偵測到 Vivaldi 仍在執行中（包含背景程序）！")
    print("!" * 60)
    print("\nContinuing may cause History file corruption or optimization failure.")
    print("繼續執行可能導致 History 檔案損壞或優化失敗。")

    response = input("\nForce continue? / 是否強制繼續？ (y/N): ").strip().lower()
    if response != "y":
        print("\nAborted. Please fully close Vivaldi and try again.")
        print("已中止執行，請先完全關閉 Vivaldi 再試。")
        input("\nPress any key to exit / 按任意鍵結束程式... ")
        sys.exit(0)
else:
    print("\n✓ Vivaldi is fully closed. Safe to continue.")
    print("✓ Vivaldi 已完全關閉，安全繼續。")

print("\nReady to start optimization. Please confirm the checks above.")
print("即將開始優化，請確認以上檢查無誤。")
input("\nPress any key to continue / 按任意鍵繼續執行... ")

before_size_mb = file_size_mb

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_path = os.path.join(os.path.dirname(history_path), f"History.backup.{timestamp}")
log_path = os.path.join(os.path.dirname(history_path), f"log.{timestamp}.txt")

log_lines = []
log_lines.append("=" * 60)
log_lines.append(
    f"Execution Time / 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
log_lines.append(f"History Path / History 檔案路徑: {history_path}")
log_lines.append(f"Size Before Optimization / 優化前檔案大小: {before_size_mb:.2f} MB")
log_lines.append("=" * 60)

print("\nCreating backup... / 正在建立備份...")
try:
    shutil.copyfile(history_path, backup_path)
    print(f"✓ Backup successful / 備份成功: {os.path.basename(backup_path)}")
    log_lines.append(f"\nBackup / 備份: {os.path.basename(backup_path)} - SUCCESS")
except Exception as e:
    print(f"✗ Backup failed / 備份失敗！ Error / 錯誤: {e}")
    print("\nPlease check disk space, permissions, or if Vivaldi is fully closed.")
    print("請檢查磁碟空間、權限或是否完全關閉 Vivaldi。")
    log_lines.append(f"\nBackup / 備份: FAILED - {e}")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    input("\nPress any key to exit / 按任意鍵結束程式... ")
    sys.exit(1)

print("\nCleaning redundant visits (keeping latest per URL)...")
print("開始清理多餘訪問記錄（每個 URL 保留最新一次）...")

conn = sqlite3.connect(history_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM visits")
total_visits_before = cur.fetchone()[0]

cur.execute("""
    DELETE FROM visits
    WHERE id NOT IN (
        SELECT MAX(id)
        FROM visits
        GROUP BY url
    )
""")

cur.execute("SELECT COUNT(*) FROM visits")
remaining_visits = cur.fetchone()[0]
deleted_visits = total_visits_before - remaining_visits

cur.execute("""
    UPDATE urls
    SET visit_count = 1,
        last_visit_time = (
            SELECT visit_time
            FROM visits
            WHERE visits.url = urls.id
            LIMIT 1
        )
    WHERE EXISTS (
        SELECT 1 FROM visits WHERE visits.url = urls.id
    )
""")

conn.commit()
conn.close()

print("\nCompressing database (VACUUM), this may take a while...")
print("正在壓縮資料庫（VACUUM），這可能需要一點時間...")

conn_vacuum = sqlite3.connect(history_path)
conn_vacuum.execute("VACUUM")
conn_vacuum.close()

print("✓ Database compression complete.")
print("✓ 資料庫壓縮完成。")

after_size_mb = os.path.getsize(history_path) / (1024 * 1024)

log_lines.append("")
log_lines.append("-" * 60)
log_lines.append("EXECUTION SUMMARY / 執行摘要")
log_lines.append("-" * 60)
log_lines.append(f"Deleted visits / 已刪除訪問記錄: {deleted_visits}")
log_lines.append(
    f"Remaining visits / 剩餘訪問記錄: {remaining_visits} (one per URL / 每個 URL 一筆)"
)
log_lines.append(f"Size after optimization / 優化後檔案大小: {after_size_mb:.2f} MB")
log_lines.append(
    f"Size reduction / 檔案大小減少: {before_size_mb - after_size_mb:.2f} MB"
)
log_lines.append("")
log_lines.append("-" * 60)
log_lines.append("TOP 10 DOMAINS BY UNIQUE URL COUNT")
log_lines.append("優化後仍保留記錄的域名中，包含最多不同頁面的 Top 10")
log_lines.append("-" * 60)

conn = sqlite3.connect(history_path)
cur = conn.cursor()

cur.execute("""
    SELECT url FROM urls
    WHERE id IN (SELECT url FROM visits)
""")

domains = []
for row in cur.fetchall():
    url = row[0]
    try:
        host = urlparse(url).hostname or ""
        if host.startswith("www."):
            host = host[4:]
        if host:
            domains.append(host)
    except:
        continue

domain_counter = Counter(domains)
top10 = domain_counter.most_common(10)

for i, (domain, count) in enumerate(top10, 1):
    line = f"{i:2}. {domain:<30} → {count} unique pages / 個不同頁面"
    log_lines.append(line)

conn.close()

log_lines.append("")
log_lines.append("=" * 60)
log_lines.append("Script execution completed. / 腳本執行完成。")
log_lines.append("=" * 60)

with open(log_path, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

print("\n" + "=" * 60)
print("COMPLETED! / 完成！")
print("=" * 60)
print(f"Deleted / 已刪除: {deleted_visits} redundant visit records / 筆多餘訪問記錄")
print(f"Size before / 優化前: {before_size_mb:.2f} MB")
print(f"Size after / 優化後: {after_size_mb:.2f} MB")
print(f"Reduced / 減少了: {before_size_mb - after_size_mb:.2f} MB")
print(f"\nDetailed log saved to / 詳細日誌已儲存至: {os.path.basename(log_path)}")
print("=" * 60)

input("\nPress any key to exit / 按任意鍵結束程式... ")
