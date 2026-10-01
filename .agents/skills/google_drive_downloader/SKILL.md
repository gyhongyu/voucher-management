---
name: google_drive_downloader
description: Voucher Management 專案專屬 Google Drive 出差單據單向增量下載總管 (Voucher Drive Downloader)。專門用於將雲端 Business Trip 資料夾 (1cHZL5SFj0O9V25gxLXsyuhJklF0x_F_S) 中的出差發票與 PDF/JPG 收據單向同步至本地月份目錄。內建「防覆蓋保護鐵律 (Zero-Overwrite Guard)」：若本地已存在該月份目錄且包含單據，嚴格拒絕下載並安全跳過；自動忽略「說明」等非單據目錄。當使用者提到「下載雲端單據」、「拉取Google Drive單據」、「下載出差發票」、「sync drive」、「drive download」、「google drive download」或剛出差回來需要拉取雲端單據時自動觸發。
---

# 📥 Google Drive Voucher Downloader (出差單據單向增量下載總管)

> 📌 **核心使命**：**「出差手機隨手丟雲端，回家一鍵拉取進管線，嚴防覆蓋已命名單據！」**  
> 專門銜接使用者的 Google Drive 雲端出差目錄（`Business Trip`）與本專案的自動化報銷流水線（`rename_vouchers.py` ➔ `generate_dashboard.py`）。

---

## 💀 屍前驗屍與四大硬性鐵律 (Pre-Mortem Invariants)

1. **【防覆蓋最高防線 (Zero-Overwrite Guard)】**：
   - 若本地已存在該月份目錄（如 `Sep` 或 `Sep 2026`）且已含有檔案，**嚴格拒絕下載並安全跳過**！
   - 杜絕將本地已由 AI 視覺辨識改名好的標準單據砸爛或重複覆蓋。
2. **【智能目錄過濾 (Noise Filter)】**：
   - 自動過濾 `說明` 等非月份資料夾，精確鎖定 `Sep 2026` 等出差月份。
3. **【雙軌自癒通訊 (Dual Transport Pipeline)】**：
   - 具備 Google Drive 授權直載與 REST API 自動換票通道，支援大容量單據無損下載。
4. **【單一入口與 Command Hygiene】**：
   - 固定命令簽名：`py .agents\skills\google_drive_downloader\scripts\drive_downloader.py`。

---

## 🚦 CLI 常用指令

```bash
# 1. 執行標準單向增量下載 (自動檢測新月份，已存在月份自動跳過)
py .agents\skills\google_drive_downloader\scripts\drive_downloader.py

# 2. 指定下載特定月份 (依然受防覆蓋保護)
py .agents\skills\google_drive_downloader\scripts\drive_downloader.py --month "Sep 2026"
```

---

## 🔄 標準作業流 (SOP)

1. **出差期間**：手機拍攝收據或收到電子收據，直接丟入 Google Drive `Business Trip / <Month YYYY>` 目錄。
2. **拉取單據**：在專案根目錄執行 `py .agents\skills\google_drive_downloader\scripts\drive_downloader.py`。
3. **轉檔與命名**：執行既有管線 `py rename_vouchers.py "<Month>"`。
4. **儀表板產出**：執行 `py generate_dashboard.py "<Month>"`。

---

## 📁 模組結構

- 核心下載腳本：[`scripts/drive_downloader.py`](file:///e:/Projects/Voucher%20management/.agents/skills/google_drive_downloader/scripts/drive_downloader.py)
- GAS 雲端網關代碼：[`gas/Code.js`](file:///e:/Projects/Voucher%20management/.agents/skills/google_drive_downloader/gas/Code.js)
- Clasp 設定檔：[`.clasp.json`](file:///e:/Projects/Voucher%20management/.agents/skills/google_drive_downloader/.clasp.json)
