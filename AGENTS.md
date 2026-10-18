# 🛠️ Voucher management 專案工程規範 (AGENTS.md)

<RULE[development_invariants]>
1. 🚦【核心原則與決策門禁】：
   - 核心職責：業務邏輯編寫、單元測試、Bug 修復與流程自動化。
   - 核心方法：編寫代碼或方案前強制執行「Pre-mortem 屍前驗屍 ✕ 第十人反對法則」。

2. ⛔【不可違背之工程紅線 (Hard Invariants)】：
   - 嚴禁未經授權主動發起 `git push`；嚴禁以 `taskkill` 殺除核心進程。
   - 零即時上行律、Schema 探測先行、終端 stdout 真值管道。
</RULE[development_invariants]>

<!-- [START: CODE_MAP_INVARIANT] -->
## 🗺️ 專案代碼導航與呼叫鏈門禁 (Code Map Navigation Invariant)
1. **嚴禁盲目摸象**：排查 Bug、尋找函式位置或跨檔案追蹤時，**絕對嚴禁**一上來直接使用全局 `grep` 大海撈針！
2. **第一步宏觀導航**：凡面對未知代碼或排查架構，優先在終端執行極速地圖命令（0 成本在記憶體建立心智模型）：
   ```powershell
   py .agents\skills\agent_code_map\scripts\map.py
   ```
3. **第二步微觀定位 (Unified Search)**：同時獲取符號定義位置與所有被呼叫點：
   ```powershell
   py .agents\skills\agent_code_map\scripts\callers.py <symbol_name>
   ```
4. **專項指令速查**：
   - 原始定義尋址: `py .agents\skills\agent_code_map\scripts\callers.py def <symbol_name>`
   - 提取函式文檔/簽名: `py .agents\skills\agent_code_map\scripts\callers.py doc <symbol_name>`
   - 前端 DOM 錨點查詢: `py .agents\skills\agent_code_map\scripts\callers.py dom <id_or_class>`
<!-- [END: CODE_MAP_INVARIANT] -->
