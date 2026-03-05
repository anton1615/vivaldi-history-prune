# Vivaldi History Prune

Vivaldi 瀏覽器歷史紀錄優化工具，透過清理冗餘訪問記錄來減少資料庫大小。

## 功能特色

- **自動備份**：每次執行前自動建立帶時間戳記的備份檔案
- **智能清理**：每個 URL 只保留最新一次訪問記錄
- **資料庫壓縮**：執行 VACUUM 釋放未使用的空間
- **詳細日誌**：生成執行報告，包含 Top 10 域名統計
- **安全檢查**：自動偵測 Vivaldi 是否仍在執行

## 系統需求

- Python 3.6+
- Windows 10/11
- Vivaldi 瀏覽器

## 安裝

```bash
pip install psutil
```

## 使用方法

1. 完全關閉 Vivaldi 瀏覽器（包含背景程序）
2. 執行腳本：
   ```bash
   python vivaldi-history-prune.py
   ```

## 執行流程

1. 檢查 Vivaldi 是否已關閉
2. 建立備份檔案（`History.backup.YYYY-MM-DD_HH-MM-SS`）
3. 刪除多餘的 `visits` 記錄
4. 更新 `urls` 表格的 `visit_count` 與 `last_visit_time`
5. 執行 `VACUUM` 壓縮資料庫
6. 生成日誌檔案（`log.YYYY-MM-DD_HH-MM-SS.txt`）

## 輸出範例

```
History 檔案目前大小：156.32 MB
Vivaldi 已完全關閉，安全繼續。
正在建立備份...
備份成功：History.backup.2025-12-22_10-25-10
開始清理多餘 visits...
正在壓縮資料庫（VACUUM）...
資料庫壓縮完成。

==================================================
完成！已刪除 45678 筆多餘 visits 記錄
優化前檔案大小：156.32 MB
優化後檔案大小：42.15 MB
減少了：114.17 MB
詳細 log 已儲存至：log.2025-12-22_10-25-10.txt
==================================================
```

## 日誌檔案內容

日誌包含：
- 執行時間與檔案路徑
- 優化前後檔案大小
- 刪除與剩餘記錄數量
- Top 10 域名統計（依 unique URL 數量排序）

## 檔案結構

```
%LOCALAPPDATA%\Vivaldi\User Data\Default\
├── History                    # 主資料庫（優化目標）
├── History.backup.2025-12-22_10-25-10  # 備份檔案
└── log.2025-12-22_10-25-10.txt         # 執行日誌
```

## 技術規格

| 項目 | 說明 |
|------|------|
| 目標檔案 | `History` (SQLite 資料庫) |
| 備份命名 | `History.backup.{timestamp}` |
| 日誌命名 | `log.{timestamp}.txt` |
| 時間格式 | `%Y-%m-%d_%H-%M-%S` |
| 清理策略 | 保留 `MAX(id)` 的 visit 記錄 |

## SQL 操作

### 刪除多餘 visits
```sql
DELETE FROM visits
WHERE id NOT IN (
  SELECT MAX(id)
  FROM visits
  GROUP BY url
)
```

### 更新 urls 表格
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

## 注意事項

- 執行前務必完全關閉 Vivaldi
- 備份檔案會保留在原目錄，請定期清理
- 首次執行建議先手動備份整個 `User Data` 資料夾

## 授權

MIT License
