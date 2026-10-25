---
trigger: model_decision
description: "當需要了解本專案定位、詢問專案是做什麼的、新AI代理進場接手、或詢問出差報銷全流程管線架構時"
---

# 🛡️ Voucher Workflow Knowledge 規範

<RULE[voucher_workflow_knowledge_invariant]>
1. ⛔【嚴禁行為 (Anti-Pattern)】：
   - 嚴禁在不知道專案定位與現有三件套管線時盲目手寫腳本或臆造處理流程
2. ✅【標準做法 (Standard Practice)】：
   - 遵循本專案報銷三件套架構：1. google_drive_downloader(雲端拉取) 2. voucher_receipt_collector(郵件抓Uber) 3. voucher_pipeline_manager(清洗/更名/儀表板/微創補單)，所有單據均對齊 references/data_contract.md 命名規範
</RULE[voucher_workflow_knowledge_invariant]>
