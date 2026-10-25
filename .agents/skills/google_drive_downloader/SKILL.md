---
name: google_drive_downloader
description: Voucher專屬Google Drive出差單據增量下載總管。單向同步Business Trip雲端發票至本地月份目錄，具備防覆蓋保護鐵律。
---

# Google Drive Voucher Downloader (出差單據增量下載總管)

> [!IMPORTANT]
> **【核心職責與一票否決硬鎖】**
> - **職責定位**：負責將 Google Drive `Business Trip` 雲端收據單向增量拉取至本地 `Business Trip/<Month>/`。
> - **下游對齊**：單據拉取完畢後，下游交由 `voucher_pipeline_manager` 進行清洗與儀表板產出。
> - 🔴 **一票否決**：嚴禁覆蓋本地已完工（存在 `Reimbursement.html`）或已存在的同名單據！

---

## 🚀 常用指令導航 (CLI --help 探索)

| 常用場景 | 推薦指令 (具備固定簽名) |
| :--- | :--- |
| **增量同步全量月份** | `py .agents/skills/google_drive_downloader/scripts/drive_downloader.py` |
| **指定單一月份同步** | `py .agents/skills/google_drive_downloader/scripts/drive_downloader.py --month "<月份>"` |
| **查看 CLI 參數** | `py .agents/skills/google_drive_downloader/scripts/drive_downloader.py --help` |

> 💡 **單 Agent 接力指引**：下載完成後，直接調用 `py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run "<月份>"` 啟動處理管線。

---

## 🧭 深入指南索引 (按需 view_file 載入)

| 任務情境 | 查閱檔案 |
| :--- | :--- |
| 查閱雙軌通訊機制 (REST API / GAS Fallback) 與 CLI 詳細字典 | [references/cli_manual.md](file:///e:/Projects/Voucher%20management/.agents/skills/google_drive_downloader/references/cli_manual.md) |
| 查閱專案整體單據命名與數據契約規範 | [references/data_contract.md](file:///e:/Projects/Voucher%20management/.agents/skills/voucher_pipeline_manager/references/data_contract.md) |
