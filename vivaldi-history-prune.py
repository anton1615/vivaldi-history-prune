# ==============================================================================
# Vivaldi History 優化腳本 - 功能說明
#
# 1. 每次執行前自動備份 History 檔案，檔名帶日期時間標籤
#    例如：History.backup.2025-12-22_10-25-10
#
# 2. 清理多餘 visits：每個 unique URL 只保留最新一次訪問記錄（使用 MAX(id)）
#
# 3. 更新 urls 表格的 visit_count 為 1，並修正 last_visit_time
#
# 4. 執行 VACUUM 壓縮資料庫
#
# 5. 產生 log 檔案（檔名帶時間標記，例如 log.2025-12-22_10-25-10.txt）
#    內容包含：
#    - 執行摘要（刪除數量、大小變化）
#    - 優化後仍保留記錄的域名中，包含最多不同頁面（unique URL）的 Top 10
#
# 使用前請務必完全關閉 Vivaldi，並正確設定下方 history_path
#
# 【重要提醒】本腳本需要 psutil 模組來檢查 Vivaldi 是否已關閉
# 若尚未安裝，請開命令提示字元執行：
#     pip install psutil
# ==============================================================================

import sqlite3
import shutil
import os
import sys
from datetime import datetime
from collections import Counter
from urllib.parse import urlparse

try:
    import psutil  # 用來檢查 Vivaldi 是否在執行
except ImportError:
    print("錯誤：未安裝 psutil 模組！")
    print("請開啟命令提示字元執行以下指令安裝：")
    print("    pip install psutil")
    print("安裝完成後再重新執行本腳本。")
    input("\n按任意鍵結束程式...")
    sys.exit(1)

# ==================== 已替換為你的使用者名稱 "Anton" ====================
# Windows 標準路徑（在 vivaldi://about/ 可確認 Profile Path 是否正確）
history_path = r"C:\Users\Anton\AppData\Local\Vivaldi\User Data\Default\History"
# ============================================================================

if not os.path.exists(history_path):
    print("錯誤：找不到 History 檔案，請檢查路徑是否正確！")
    print("路徑：", history_path)
    input("\n按任意鍵結束程式...")
    sys.exit(1)

# 顯示目前檔案大小（MB）
file_size_mb = os.path.getsize(history_path) / (1024 * 1024)
print(f"History 檔案目前大小：{file_size_mb:.2f} MB")

# 檢查 Vivaldi 是否仍在執行
def is_vivaldi_running():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'vivaldi' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

print("\n正在檢查 Vivaldi 是否已完全關閉...")
if is_vivaldi_running():
    print("警告：偵測到 Vivaldi 仍在執行中（包含背景進程）！")
    print("   繼續執行可能導致 History 檔案損壞或優化失敗。")
    response = input("是否強制繼續？(y/N): ").strip().lower()
    if response != 'y':
        print("已中止執行，請先完全關閉 Vivaldi 再試。")
        input("\n按任意鍵結束程式...")
        sys.exit(0)
else:
    print("Vivaldi 已完全關閉，安全繼續。")

print("\n即將開始優化，請確認以上檢查無誤。")
input("按任意鍵繼續執行...")

# 優化前檔案大小
before_size_mb = file_size_mb

# 時間標記
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_path = os.path.join(os.path.dirname(history_path), f"History.backup.{timestamp}")
log_path = os.path.join(os.path.dirname(history_path), f"log.{timestamp}.txt")

# log 內容準備
log_lines = []
log_lines.append(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append(f"History 檔案路徑: {history_path}")
log_lines.append(f"優化前檔案大小: {before_size_mb:.2f} MB")
log_lines.append("")

print("正在建立備份...")
try:
    shutil.copyfile(history_path, backup_path)
    print(f"備份成功：{os.path.basename(backup_path)}")
    log_lines.append(f"備份成功：{os.path.basename(backup_path)}")
except Exception as e:
    print(f"備份失敗！錯誤訊息：{e}")
    print("程式已中止，請檢查磁碟空間、權限或是否完全關閉 Vivaldi。")
    log_lines.append(f"備份失敗：{e}")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    input("\n按任意鍵結束程式...")
    sys.exit(1)

print("開始清理多餘 visits（每個 URL 保留最新一次）...")

# 第一階段：開啟連接，執行刪除與更新
conn = sqlite3.connect(history_path)
cur = conn.cursor()

# 刪除前 visits 總數
cur.execute("SELECT COUNT(*) FROM visits")
total_visits_before = cur.fetchone()[0]

# 刪除多餘 visits，只保留每個 url 的最新一筆
cur.execute("""
DELETE FROM visits
WHERE id NOT IN (
    SELECT MAX(id)
    FROM visits
    GROUP BY url
)
""")

# 剩餘 visits 數
cur.execute("SELECT COUNT(*) FROM visits")
remaining_visits = cur.fetchone()[0]
deleted_visits = total_visits_before - remaining_visits

# 更新 urls 表格
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

# 提交所有修改並關閉連接
conn.commit()
conn.close()

# 第二階段：重新開啟連接，只為了執行 VACUUM（避免 transaction 錯誤）
print("正在壓縮資料庫（VACUUM），這可能需要一點時間...")
conn_vacuum = sqlite3.connect(history_path)
conn_vacuum.execute("VACUUM")
conn_vacuum.close()
print("資料庫壓縮完成。")

# 優化後大小
after_size_mb = os.path.getsize(history_path) / (1024 * 1024)

# 記錄摘要到 log
log_lines.append(f"刪除 visits 記錄數量: {deleted_visits}")
log_lines.append(f"剩餘 visits 記錄數量: {remaining_visits}（每個 URL 一筆）")
log_lines.append(f"優化後檔案大小: {after_size_mb:.2f} MB")
log_lines.append(f"檔案大小減少: {before_size_mb - after_size_mb:.2f} MB")
log_lines.append("")
log_lines.append("優化後仍保留記錄的域名中，包含最多不同頁面（unique URL）的 Top 10：")
log_lines.append("-" * 60)

# ==================== 統計域名 Top 10 開始 ====================
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
    line = f"{i:2}. {domain:<30} → {count} 個不同頁面"
    log_lines.append(line)

conn.close()
# ==================== 統計域名 Top 10 結束 ====================

log_lines.append("")
log_lines.append("腳本執行完成。")

# 寫入 log 檔案
with open(log_path, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

# 螢幕顯示結果
print("\n" + "="*50)
print("完成！已刪除 {} 筆多餘 visits 記錄".format(deleted_visits))
print(f"優化前檔案大小：{before_size_mb:.2f} MB")
print(f"優化後檔案大小：{after_size_mb:.2f} MB")
print(f"減少了：{before_size_mb - after_size_mb:.2f} MB")
print(f"詳細 log 已儲存至：{os.path.basename(log_path)}")
print("="*50)

# 結束前暫停
input("\n按任意鍵結束程式...")