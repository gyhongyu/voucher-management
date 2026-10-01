# 📝 研發結構化原子日誌 (ACTIVE_LOG.md)
> ⚠️ **【鐵律：只追加不修改 (Append-Only)】**
> 任何代碼修正、重構、架構決策或工具鏈變更，以標準 6 行格式追加至文末。

---

### [2026-10-01] 固化專案專屬單據下載與全流程流水線處理技能
- **背景/意圖**：用戶反饋 AI 代理不會主動看 README，若刪除歷史月份目錄將喪失單據處理心智模型；同時需要從 Google Drive 雲端安全單向拉取差旅單據。
- **改動細節**：
  1. 建立並播種 `.agents/skills/google_drive_downloader`，佈署獨立 GAS Web App 網關並採用 5 線程 Base64 並發傳輸，100% 保持雲端目錄名稱 (`Sep 2026`)，嚴格 Zero-Overwrite 守護。
  2. 建立並播種 `.agents/skills/voucher_pipeline_manager`，封裝三級目錄自動分流、圖片轉檔、PyMuPDF 高鐵/打車票據智慧識別重命名 (`DD-MMM-YY-Route-Amount.pdf`) 與獨立報銷總表生成。
  3. 更新 `AGENTS.md`、`.agent_profiles/` 與 `docs/TOPOLOGY.md`，將技能完全寫入專案憲法與推薦映射庫。
- **影響範圍**：`.agents/skills/`、`Sep 2026/`、`docs/TOPOLOGY.md`、`AGENTS.md`。

### [2026-10-01] 對齊雲端 Business Trip 目錄層級與自動歸檔 (Auto-Archive) 閉環
- **背景/意圖**：用戶指出根目錄直接放月份資料夾不符合 Google Drive 雲端真實層級；同時歷史單據已有技能可隨時重現，應自動移入 archive 保持工作區極簡。
- **改動細節**：
  1. 重構 `google_drive_downloader`，將下載目錄全面對齊為 `Business Trip/<Folder_Name>`；新增 `auto_archive_processed_trips`，在下載前自動將已包含 `Reimbursement.html` 的歷史月份目錄安全移至 `archive/`。
  2. 升級雙軌下載通道 (GAS Web App + Drive REST API)，支援大圖與掃描檔下載重試；`.gitignore` 登錄 `archive/`。
  3. 重構 `voucher_pipeline_manager` 與 `generate_dashboard.py`，自動尋址 `Business Trip/<月份>`。
  4. 清理根目錄歷史舊目錄，同步更新 `docs/TOPOLOGY.md`。
- **影響範圍**：`Business Trip/`、`archive/`、`generate_dashboard.py`、`drive_downloader.py`、`voucher_pipeline.py`、`TOPOLOGY.md`。
- **驗證方式**：實測 `Sep 2026` 產生總表後，再次調用下載器成功觸發自動歸檔至 `archive/Sep 2026/`，隨後重新單向拉取 18 筆全新單據並一鍵完成流水線處理。
