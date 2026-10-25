# 📖 Voucher Pipeline CLI 詳細命令手冊 (CLI Manual)

> 本文檔提供 `voucher_pipeline.py` 之完整參數字典與進階操作範例。一般 AI 代理人操作請優先參閱主手冊 [SKILL.md](../SKILL.md)。

---

## 1. 全量管線子命令 (`run`)

對指定月份執行完整的四大階段：自動目錄初始化 ➔ 散落單據分流 ➔ 圖片轉 PDF 並備份 ➔ 交通單據文字辨識更名 ➔ 產出總表儀表板與台帳。

### 命令語法
```bash
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run <MONTH> [--path <PROJECT_ROOT>]
```

### 參數說明
* `<MONTH>` (必要): 目標出差月份名稱，例如 `"Sep 2026"` 或 `"Business Trip/Sep 2026"`。腳本會自適應優先在 `Business Trip/` 下尋找。
* `--path` (選用): 專案根目錄路徑。若未提供，預設自動向上反查至專案根目錄。

### 執行範例
```bash
# 標準調用
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run "Sep 2026"
```

---

## 2. 微創補件子命令 (`patch`)

專門針對後續發現之漏單據進行「局部單點補登」。本命令具備**零推倒保護**：
1. 自動解析單據文字特徵與命名。
2. 將檔案搬移歸位至指定分類目錄。
3. 自動渲染多頁垂直拼接高清預覽圖至 `.previews/`。
4. 微創注入 `Reimbursement.html` 內部的 `defaultData`，免刷新覆蓋現有編輯。
5. 同步更新本地 `<Month>_Vouchers.json` 結構化總帳。

### 命令語法
```bash
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py patch <FILE> --month <MONTH> [--type {trans,pr,other}] [--path <PROJECT_ROOT>]
```

### 參數說明
* `<FILE>` (必要): 待補登的單據路徑（支援相對路徑或絕對路徑）。
* `--month` (必要): 目標月份資料夾名稱，例如 `"Sep 2026"`。
* `--type` (選用): 單據分類，選項為 `trans`（交通）、`pr`（公關）、`other`（雜項）。預設為 `trans`。
* `--path` (選用): 專案根目錄。

### 執行範例
```bash
# 補登一張漏掉的 Uber 車單
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py patch "scratch/uber_receipt.pdf" --month "Sep 2026" --type trans
```

---

## 3. 相容模式調用 (Legacy Compatibility)

為了相容傳統簡短指令，直接傳入月份名稱將預設觸發 `run` 模式：
```bash
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py "Sep 2026"
```
