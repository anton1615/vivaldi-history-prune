# Vivaldi History Prune

A tool to optimize Vivaldi browser history database by removing redundant visit records and reducing database size.

## Features

- **Auto Backup**: Creates timestamped backup before each execution
- **Smart Cleaning**: Keeps only the latest visit per unique URL
- **Database Compression**: Executes VACUUM to release unused space
- **Detailed Logging**: Generates execution report with Top 10 domain statistics
- **Safety Check**: Automatically detects if Vivaldi is still running

## Requirements

- Python 3.6+
- Windows 10/11
- Vivaldi Browser

## Installation

```bash
pip install psutil
```

## Usage

1. Fully close Vivaldi browser (including background processes)
2. Run the script:
   ```bash
   python vivaldi-history-prune.py
   ```

## Execution Flow

1. Check if Vivaldi is closed
2. Create backup file (`History.backup.YYYY-MM-DD_HH-MM-SS`)
3. Delete redundant `visits` records
4. Update `urls` table (`visit_count` and `last_visit_time`)
5. Execute `VACUUM` to compress database
6. Generate log file (`log.YYYY-MM-DD_HH-MM-SS.txt`)

## Sample Output

```
============================================================
Current History size / History 檔案目前大小: 156.32 MB
============================================================

Checking if Vivaldi is fully closed...
正在檢查 Vivaldi 是否已完全關閉...

✓ Vivaldi is fully closed. Safe to continue.
✓ Vivaldi 已完全關閉，安全繼續。

Creating backup... / 正在建立備份...
✓ Backup successful / 備份成功: History.backup.2025-12-22_10-25-10

Cleaning redundant visits (keeping latest per URL)...
開始清理多餘訪問記錄（每個 URL 保留最新一次）...

Compressing database (VACUUM), this may take a while...
正在壓縮資料庫（VACUUM），這可能需要一點時間...

✓ Database compression complete.
✓ 資料庫壓縮完成。

============================================================
COMPLETED! / 完成！
============================================================
Deleted / 已刪除: 45678 redundant visit records / 筆多餘訪問記錄
Size before / 優化前: 156.32 MB
Size after / 優化後: 42.15 MB
Reduced / 減少了: 114.17 MB

Detailed log saved to / 詳細日誌已儲存至: log.2025-12-22_10-25-10.txt
============================================================
```

## Log File Content

The log includes:
- Execution time and file path
- File size before and after optimization
- Deleted and remaining record counts
- Top 10 domains by unique URL count

## File Structure

```
%LOCALAPPDATA%\Vivaldi\User Data\Default\
├── History                              # Main database (optimization target)
├── History.backup.2025-12-22_10-25-10   # Backup file
└── log.2025-12-22_10-25-10.txt          # Execution log
```

## Technical Specifications

| Item | Description |
|------|-------------|
| Target File | `History` (SQLite database) |
| Backup Naming | `History.backup.{timestamp}` |
| Log Naming | `log.{timestamp}.txt` |
| Timestamp Format | `%Y-%m-%d_%H-%M-%S` |
| Cleanup Strategy | Keep `MAX(id)` visit record per URL |

## SQL Operations

### Delete redundant visits
```sql
DELETE FROM visits
WHERE id NOT IN (
    SELECT MAX(id)
    FROM visits
    GROUP BY url
)
```

### Update urls table
```sql
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
```

## Important Notes

- Always fully close Vivaldi before execution
- Backup files are preserved in the original directory, clean them periodically
- For first-time execution, manually backup the entire `User Data` folder

## License

MIT License
