# 📋 專案工作交接文檔 (HANDOFF.md)

> 📌 **專案**: `Voucher management` (差旅單據自動化分流、辨識重命名與報銷儀表板)  
> 🕒 **交接時間**: 2026-10-01  
> 🏷️ **交班對象**: 下一位進場 AI 代理人  
> 🎯 **核心接棒任務**: **與用戶討論並重構/美化報銷總表的前端 HTML 模板** (`generate_dashboard.py` / `Business Trip/Sep 2026/Reimbursement.html`)

---

## 0. 🚀 進場第一動與導航門禁 (Pre-Flight Navigation - 進場首步強制執行)

新代理人進場請**第一時間在終端機執行以下兩大門禁指令**，0-Token 在記憶體瞬間建立專案拓撲心智模型與代碼語法地圖，嚴禁盲目全局 grep：

```bash
# 1. 第一門禁：專案現場目錄邊界與孤兒檔案審計 (掌握目錄職責)
py -X utf8 .agents\skills\project_structure_keeper\scripts\keeper.py audit

# 2. 第二門禁：專案代碼拓撲與引用中心度分析 (掌握函式定義與調用拓撲)
py .agents\skills\agent_code_map\scripts\map.py
```

---

## 1. 🧠 智腦不二過記憶突觸 (Brain Synapse & Anti-Failure DNA)

### ⛔ 鋼鐵紅線與死因卷宗 (Hard Invariants)
1. **【嚴禁未授權 Git 推送】**：絕對禁止主動執行 `git push`！
2. **【目錄層級對齊與 Git 忽略】**：
   - 出差單據專用目錄為 `Business Trip/<月份>/`（例如 `Business Trip/Sep 2026/`），100% 對齊 Google Drive 雲端層級。
   - `Business Trip/` 與 `archive/` 均已被寫入 `.gitignore`，**嚴禁將單據二進位檔案提交到遠端**。
3. **【自動歸檔守護律 (Auto-Archive Guard)】**：
   - 在執行下載單據時，若在 `Business Trip/` 偵測到已有 `Reimbursement.html` 總表（代表該次出差報銷單據已完全完工），下載器會**自動將該月份整個搬遷至 `archive/`**，等待使用者日後清理。
4. **【AI 視覺開眼與手動確認防禦律】**：
   - 遇到餐飲圖片或純掃描 PDF 時，代碼管線會暫時加上 `[需要手動確認]_`。
   - **AI 代理人必須主動調用多模態視覺工具開眼看圖**（解析日期、店名、金額並標準更名為 `DD-MMM-YY-Desc-Amount.pdf`），**嚴禁連看都不看就扔給用戶手動確認**！只有在嚴重殘缺、信心度低於 85% 時才保留標記。
5. **【多模式規則切換】**：
   - 本專案已配置多模式規則治理，根目錄提供 `切換為生產模式.bat` 與 `切換為開發模式.bat`，可隨時在唯讀辦公與研發治理間物理抽換。

---

## 2. 🗺️ 專案最新物理架構與模組地圖 (Project Topology & Modules)

參照 [docs/TOPOLOGY.md](file:///e:/Projects/Voucher%20management/docs/TOPOLOGY.md)：

| 物理路徑 | 模組名稱 | 核心職責與現狀 |
| :--- | :--- | :--- |
| `Business Trip/` | **出差單據業務根目錄** | 存放各月份出差單據，如 `Sep 2026/`（含 `Transportation/` 15 筆、`Public Relations/` 3 筆，均已標準命名） |
| `archive/` | **歷史完工單據歸檔目錄** | 存放已產生 `Reimbursement.html` 總表之歷史月份（.gitignore 已保護） |
| `generate_dashboard.py` | **報銷總表生成引擎** | 負責掃描指定月份目錄，生成獨立單頁 `Reimbursement.html` (內建 Alpine.js、動態樣式與 localStorage 快取) |
| `.agents/skills/google_drive_downloader/` | **雲端下載技能** | 雙軌下載通道 (GAS Web App + Drive REST API) 5 線程極速增量同步 (Zero-Overwrite) |
| `.agents/skills/voucher_pipeline_manager/` | **單據流水線技能** | 自動三級分流、圖片轉 PDF、PyMuPDF 高鐵/打車票據正則命名 (`DD-MMM-YY-Route-Amount.pdf`) |
| `.agents/skills/project_structure_keeper/` | **專案拓撲守護技能** | 專案現場結構導航、職責清單維護與交接審計 (`keeper.py audit`) |
| `.agents/skills/agent_code_map/` | **專案代碼地圖技能** | 靜態 AST 代碼分析與符號定義尋址 (`map.py`, `callers.py`) |

---

## 3. 系統現況與已固化基線 (System Baseline & Assets)

- **`Sep 2026` 單據處理狀態**：
  - 交通費 (Transportation): 15 筆，全數標準命名完成。
  - 公關費 (Public Relations): 3 筆，經 AI 視覺開眼識別全數標準命名完成（總金額 ₹28,379）。
  - 當前總表：[`Business Trip/Sep 2026/Reimbursement.html`](file:///e:/Projects/Voucher%20management/Business%20Trip/Sep%202026/Reimbursement.html)。
- **當前儀表板模板架構**：
  - 目前位於 `generate_dashboard.py` 第 91~466 行，採用 `Alpine.js` ＋ 內嵌 CSS (深色主題/Glassmorphism)。
  - 功能支援：點擊編輯、長按 0.5 秒複製、刪除、日期排序、JSON 數據導出、localStorage 持久化。

---

## 4. 下一棒核心待辦任務 (Immediate Action Items)

### 🎯 任務目標：與用戶討論並重構/美化報銷總表的 HTML 前端模板

1. **第一優先**：進入【**討論模式**】！
   - 先詢問用戶對目前 [`Business Trip/Sep 2026/Reimbursement.html`](file:///e:/Projects/Voucher%20management/Business%20Trip/Sep%202026/Reimbursement.html) 的視覺風格、版面佈局或互動功能有哪些具體的痛點或改進想法。
   - **在用戶說「結束討論」前，禁止直接修改代碼！**
2. **可能的優化維度建議（可供用戶挑選）**：
   - **統計卡片 (KPI Dashboard)**：在頁首增加總金額統計（公關費總額、交通費總額、出差總支出）、單據總筆數卡片。
   - **匯出增強**：除了 JSON 導出，是否需要支援直接匯出 Excel/CSV，或是純文字/Markdown 報銷清單？
   - **單據預覽體驗**：目前是用另開新分頁預覽，是否改為 Modal 燈箱彈窗同屏預覽 PDF/圖片？
   - **分類與搜尋過濾**：增加即時關鍵字搜尋框或依日期區間過濾。
   - **列印/列印友善模式 (Print Media Query)**：方便直接列印出紙本黏貼封面。
3. **改動實施單一真理源**：
   - 報銷總表是由 `generate_dashboard.py` 動態生成的，因此模板修改必須落在 `generate_dashboard.py` 中的 `html_content` 模板字串，修改完成後執行 `py generate_dashboard.py "Sep 2026"` 重新生成驗收。

---
*最後交接更新：遠端倉庫已同步推送，當前會話即刻封裝完畢。*
