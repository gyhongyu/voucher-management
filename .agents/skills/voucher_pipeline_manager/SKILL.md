---
name: voucher_pipeline_manager
description: 出差報銷單據全自動化流水線總管。負責散落單據分流、圖片轉PDF、交通單據正規命名、AI開眼引導、微創補單與總表HTML產出。
---

# Voucher Pipeline Manager (報銷單據自動化流水線總管)

> [!IMPORTANT]
> **【核心職責與一票否決硬鎖】**
> - **職責定位**：接管本地出差單據「分流 ➔ 轉檔備份 ➔ 文字抽取更名 ➔ 總表台帳生成 ➔ 漏單微創追加」。
> - **單一真理源**：嚴格遵循 [references/data_contract.md](file:///e:/Projects/Voucher%20management/.agents/skills/voucher_pipeline_manager/references/data_contract.md) 檔名與 JSON 規範，對齊未來 Web 前端同構。
> - 🔴 **一票否決**：嚴禁依賴歷史月份代碼；面對補件嚴禁推倒整份 HTML，必須調用 `patch` 模式！

---

## 🚀 常用指令導航 (CLI --help 探索)

| 常用場景 | 推薦指令 (具備固定簽名) |
| :--- | :--- |
| **全量管線處理** | `py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run "<月份>"` |
| **漏單微創補件** | `py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py patch "<單據路徑>" --month "<月份>" --type trans/pr/other` |
| **探索參數細節** | `py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py --help` |

> 💡 **AI 代理人指引**：全量處理後若終端提示有 `[需要手動確認]_` 發票，請主動調用多模態視覺工具開眼辨識日期與金額並標準更名。

---

## 🧭 深入指南索引 (按需 view_file 載入)

| 任務情境 | 查閱檔案 |
| :--- | :--- |
| 查閱 CLI 各子命令完整參數字典與進階調用範例 | [references/cli_manual.md](file:///e:/Projects/Voucher%20management/.agents/skills/voucher_pipeline_manager/references/cli_manual.md) |
| 查閱檔名正規正則、類別映射與未來 Web 前端同構規範 | [references/data_contract.md](file:///e:/Projects/Voucher%20management/.agents/skills/voucher_pipeline_manager/references/data_contract.md) |
