---
name: voucher_receipt_collector
description: Voucher專案專用收據與發票收集轉檔大師。負責從Notes、Gmail等管道檢索Uber乘車單據並自動轉檔為標準PDF。當需要收集收據、抓取Uber發票、收集郵件單據時自動觸發。嚴禁用於主管線分流與儀表板總表維護。
---

# Voucher Receipt Collector (單據收集與轉檔大師)

> [!IMPORTANT]
> **【核心職責與一票否決硬鎖】**
> - **職責定位**：負責前端「單據檢索、外部渠道抓取與向量 PDF 轉檔（Ingestion & Preprocessing）」。
> - **邊界分流**：主管線初始化、正規化更名與總表 Dashboard 統一由 `voucher_pipeline_manager` 接管。
> - 🔴 **一票否決**：嚴禁覆蓋本地已存在的同名收據單據！

---

## 🚀 常用指令導航 (CLI --help 探索)

| 常用場景 | 推薦指令 (具備固定簽名) |
| :--- | :--- |
| **環境檢測** | `py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py status` |
| **全量收集** | `py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --month <月份> -o <目錄>` |
| **指定管道** | `py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --source notes/gmail` |
| **預演模式** | `py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --dry-run` |

> 💡 **參數探索**：真實參數一律下達 `--help` 獲取即時物理真值，文檔不重複流水帳。

---

## 🧭 深入指南索引 (按需 view_file 載入)

| 任務情境 | 查閱檔案 |
| :--- | :--- |
| 需查閱全量子命令與 CLI 參數詳細字典 | [references/cli_manual.md](file:///e:/Projects/Voucher%20management/.agents/skills/voucher_receipt_collector/references/cli_manual.md) |
