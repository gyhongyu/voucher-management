# 🗺️ 專案實體拓撲架構與模組職責活地圖 (TOPOLOGY.md)

> 📌 **專案**: `Voucher management` | **維護方式**: 粗粒度增量更新 (僅在重大模組拆分或新增時更新)  
> ⚠️ **所有 AI 代理人注意**: 嚴禁在未登錄路徑亂建檔案；查找各模組職責請依循本表尋址。

---

## 🏢 核心模組職責地圖 (Module Responsibility Map)

| 物理路徑 | 模組名稱 | 職責與包含內容 | 代理人調閱時機 |
| :--- | :--- | :--- | :--- |
| `Business Trip/` | **出差單據業務根目錄** | 100% 對齊 Google Drive 雲端層級，存放各月份出差單據 (如 `Sep 2026/`) | 進行單據下載、分類與流水線處理時訪問 |
| `archive/` | **歷史完工單據歸檔目錄** | 存放已產生 Reimbursement.html 總表之已完工歷史月份，等待使用者日後清理 (gitignore) | 查閱歷史歸檔或使用者手動清理時訪問 |
| `docs/` | **研發 DMC 知識庫與文檔** | 存放 STATE.md、ACTIVE_LOG.md、TOPOLOGY.md 等架構與研發文檔 | 涉及該模組功能調整時查閱 |
| `.agents/skills/project_structure_keeper/` | **專案拓撲守護技能** | 專案現場結構導航、職責清單維護與交接審計 | 掌握專案全景與模組分工時喚醒 |
| `.agents/skills/google_drive_downloader/` | **差旅單據增量下載技能** | 連接雲端 Business Trip，具備自動歸檔、雙軌下載與防覆蓋 (Zero-Overwrite) | 從雲端拉取最新單據時調用 |
| `.agents/skills/voucher_pipeline_manager/` | **單據流水線與總表總管技能** | 自動三級分流、圖片轉PDF、交通票據OCR標準重命名、生成獨立報銷總表 | 處理散落單據或重建歷史管線時調用 |

---

## 🚫 結構守門鐵律 (Structure Guardrails)
1. **嚴禁隨意在根目錄亂扔代碼檔案**：代碼請依職責歸入對應模組或子資料夾。
2. **單一超大代碼拆分門禁**：當單一模組代碼膨脹進行模組化拆分時，必須同步更新本文檔與 `docs/ACTIVE_LOG.md`。
3. **路徑認知優先**：進入本專案第一時間應先檢視本文檔，確保 0 秒建立全局心智模型。
