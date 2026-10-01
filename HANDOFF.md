# 📋 專案工作交接文檔 (HANDOFF.md)

> 📌 **專案**: `Voucher management` (差旅單據自動化分流、辨識重命名與報銷儀表板)  
> 🕒 **交接時間**: 2026-10-01  
> 🏷️ **交班對象**: 下一位進場 AI 代理人  
> 🎯 **核心接棒任務**: **針對「漏上傳單據補件」場景，與用戶研究設計專案補件流水線機制，並處理根目錄待補單據 `receipt_14a702de-f3bb-4be0-b154-de9e5edf7d8c.pdf`**

---

## 0. 🚀 進場第一動與導航門禁 (Pre-Flight Navigation - 進場首步強制執行)

新代理人進場請**第一時間在終端機執行以下兩大門禁指令**，0-Token 在記憶體瞬間建立專案拓撲心智模型與代碼語法地圖，嚴禁盲目全局 grep：

```bash
# 1. 第一門禁：專案現場目錄邊界與孤兒檔案審計 (掌握目錄職責)
py -X utf8 .agents\skills\project_structure_keeper\scripts\keeper.py audit

# 2. 第二門禁：專案代碼拓撲與引用中心度分析 (掌握函式定義與調用拓撲)
py -X utf8 .agents\skills\agent_code_map\scripts\map.py
```

---

## 1. 🧠 智腦不二過記憶突觸 (Brain Synapse & Anti-Failure DNA)

### ⛔ 鋼鐵紅線與死因卷宗 (Hard Invariants)
1. **【嚴禁未授權 Git 推送】**：絕對禁止主動執行 `git push`！
2. **【目錄層級對齊與 Git 忽略】**：
   - 出差單據專用目錄為 `Business Trip/<月份>/`（例如 `Business Trip/Sep 2026/`），100% 對齊 Google Drive 雲端層級。
   - `Business Trip/` 與 `archive/` 均已被寫入 `.gitignore`，**嚴禁將單據二進位檔案提交到遠端倉庫**。
3. **【多頁 PDF 預覽必須垂直拼接 (Zero-Blank)】**：
   - 儀表板預覽引擎已全面採用 `Pillow (PIL)` 進行多頁垂直拼接（`Image.paste`）。嚴禁退回使用單頁渲染或 `fitz.Pixmap.copy`（曾引發第二頁純白翻車）。
4. **【左側空間最大化與右側抽屜操作列】**：
   - 當右側抽屜開啟時，左側表格操作欄自動隱藏，寬度自適應拓寬；所有單據操作（複製路徑、刪除）完整收攏於右側抽屜底部。
5. **【AI 視覺開眼與手動確認防禦律】**：
   - 遇到餐飲圖片或純掃描 PDF 時，代碼管線會暫時加上 `[需要手動確認]_`。
   - **AI 代理人必須主動調用多模態視覺工具開眼看圖**（解析日期、店名、金額並標準更名為 `DD-MMM-YY-Desc-Amount.pdf`），**嚴禁連看都不看就扔給用戶手動確認**！只有在嚴重殘缺、信心度低於 85% 時才保留標記。
6. **【代碼高內聚收攏於技能目錄】**：
   - 儀表板生成引擎已從根目錄遷移至 `.agents/skills/voucher_pipeline_manager/scripts/generate_dashboard.py`，流水線入口為 `.agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py`，嚴禁在根目錄散落腳本。

---

## 2. 🗺️ 專案最新物理架構與模組地圖 (Project Topology & Modules)

參照 [docs/TOPOLOGY.md](file:///e:/Projects/Voucher%20management/docs/TOPOLOGY.md)：

| 物理路徑 | 模組名稱 | 核心職責與現狀 |
| :--- | :--- | :--- |
| `Business Trip/` | **出差單據業務根目錄** | 存放各月份出差單據，如 `Sep 2026/`（含 `Transportation/` 15 筆、`Public Relations/` 3 筆，均已標準命名） |
| `archive/` | **歷史完工單據歸檔目錄** | 存放已產生 `Reimbursement.html` 總表之歷史月份（.gitignore 已保護） |
| `.agents/skills/voucher_pipeline_manager/` | **單據流水線與儀表板技能** | 自動三級分流、圖片轉 PDF、PyMuPDF 交通單據正規命名、Pillow 垂直拼接預覽圖生成、雙欄響應式 `Reimbursement.html` 儀表板 |
| `.agents/skills/google_drive_downloader/` | **雲端下載技能** | 雙軌下載通道 (GAS Web App + Drive REST API) 5 線程極速增量同步 (Zero-Overwrite) |
| `.agents/skills/project_structure_keeper/` | **專案拓撲守護技能** | 專案現場結構導航、職責清單維護與交接審計 (`keeper.py audit`) |
| `.agents/skills/agent_code_map/` | **專案代碼地圖技能** | 靜態 AST 代碼分析與符號定義尋址 (`map.py`, `callers.py`) |

---

## 3. 系統現況與已固化基線 (System Baseline & Assets)

- **`Sep 2026` 單據現狀**：
  - 交通費 (Transportation): 16 筆（含已補登歸位的 9/25 Manesar ₹539 單據），全數標準命名完成。
  - 公關費 (Public Relations): 3 筆，經 AI 視覺開眼識別全數標準命名完成。
  - 結構化總帳：[`Business Trip/Sep 2026/Sep_2026_Vouchers.json`](file:///e:/Projects/Voucher%20management/Business%20Trip/Sep%202026/Sep_2026_Vouchers.json)（共 19 筆，免推倒 HTML，隨時供外部腳本/AI 讀取）。
  - 當前總表：[`Business Trip/Sep 2026/Reimbursement.html`](file:///e:/Projects/Voucher%20management/Business%20Trip/Sep%202026/Reimbursement.html)（支援滑鼠左鍵平移拖曳、邊界調整、多頁垂直無縫拼接、抽屜開啟操作欄自適應）。
- **待補單據處理結果**：
  - 原根目錄孤兒檔案 `receipt_14a702de-f3bb-4be0-b154-de9e5edf7d8c.pdf` 已成功補登歸位至：
    `Business Trip/Sep 2026/Transportation/25-Sep-26-Gurgaon to Manesar-539.pdf`。
  - 舊版過渡腳本 `rename_vouchers.py` 已安全退役刪除，代碼全數內聚於技能目錄。

---

## 4. 下一棒核心待辦任務與技能調用指引 (Immediate Action Items & Guidelines)

### 🎯 核心使命：維持微創補登管線高可用，嚴禁推倒 HTML！

1. **遇漏單據補件場景（強烈推薦）**：
   - 強制調用已固化之微創補登指令，直接單點突破：
     ```bash
     py .agents\skills\voucher_pipeline_manager\scripts\voucher_pipeline.py patch "<單據路徑>" --month "<月份>" --type trans
     ```
   - 效益：不推倒整份 HTML，自動解析、垂直拼接預覽圖、局部追加 defaultData 與同步更新本地 `<月份>_Vouchers.json`。
2. **遇全新月份全量建置場景**：
   - 執行全量管線：
     ```bash
     py .agents\skills\voucher_pipeline_manager\scripts\voucher_pipeline.py "<新月份名稱>"
     ```
3. **改動實施單一真理源**：
   - 技能代碼位於 `.agents/skills/voucher_pipeline_manager/scripts/`。
   - 修改完成後，本地 Git 提交保存，嚴禁未授權 push。

---
*最後交接更新：2026-10-01 補單管線升級完畢，舊腳本清理，雙門禁審計與心智模型已就緒。*
