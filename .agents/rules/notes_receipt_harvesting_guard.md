---
trigger: model_decision
description: "當從 Lotus Notes 收集/檢索出差單據、Uber 或發票郵件時"
---

# 🛡️ Notes 收據信匣隔離、防跨匣翻垃圾桶與跨月對齊規範

<RULE[notes_receipt_harvesting_invariant]>
1. ⛔【嚴禁行為 (Anti-Pattern)】：
   - 未經指示調用跨信匣全局 search、翻出 Trash 垃圾桶郵件誤導用戶、未經用戶要求擅自跨渠道查 Gmail、以單一自然月機械截斷跨月底行程
2. ✅【標準做法 (Standard Practice)】：
   - 嚴格只查指定信匣 (mail list -f Uber)；行程跨月底時主動依公關費/單據真實日期窗口納入次月上旬連貫單據
</RULE[notes_receipt_harvesting_invariant]>
