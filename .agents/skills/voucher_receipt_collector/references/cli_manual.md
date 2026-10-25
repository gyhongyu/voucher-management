# 📘 Voucher Receipt Collector 命令手冊與操作指南 (CLI Reference)

## 🛠️ 指令清單與參數說明

固定命令簽名路徑：
`py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py <command>`

### 1. 狀態與底座連線檢測 (`status`)
檢查 NotesMaster 本地資料庫與 GAS Gmail 雲端網關的可用性：
```bash
py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py status
```

---

### 2. 收據與發票檢索轉檔 (`collect`)
自動從 Notes 或 Gmail 檢索符合月份的乘車收據，調用標準向量引擎導出 PDF 並存入目標目錄：

```bash
# 1. 檢索並收集特定月份的所有來源 (Notes + Gmail)
py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --month Sep-26 -o Sep-26/Transportation

# 2. 僅從 Gmail 收集 2026 年 6 月份收據
py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --source gmail --month Jun-26 -o Jun-26/Transportation

# 3. 預演模式 (Dry-Run：僅掃描列出，不實際轉檔下載)
py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --month Sep-26 --dry-run
```
