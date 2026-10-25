# 📖 Google Drive Downloader CLI 詳細手冊 (CLI Manual)

> 本文檔提供 `drive_downloader.py` 之完整參數字典與雙軌通訊架構說明。一般 AI 代理人操作請參閱主手冊 [SKILL.md](../SKILL.md)。

---

## 1. 雙軌通訊架構 (Dual-Transport Pipeline)

下載引擎採用高可用雙軌架構，確保網路中斷或 OAuth 過期時能無感自癒：
1. **主軌道 (Primary)**: 官方 Google Drive REST API。直接讀取 `~/.clasprc.json` 憑證並自動換票（支援 5 執行緒並發下載）。
2. **備援軌道 (Fallback)**: Google Apps Script Web App。當無 OAuth 權限或主軌道異常時，透過無伺服器 Webhook 以 Base64 下載。

---

## 2. CLI 參數字典

### 命令語法
```bash
py .agents/skills/google_drive_downloader/scripts/drive_downloader.py [--month <MONTH>] [--path <PROJECT_ROOT>]
```

### 參數說明
* `--month` (選用): 指定僅同步特定出差月份（例如 `"Sep 2026"`）。若未指定，預設全量掃描 Google Drive 雲端 `Business Trip` 目錄下的所有月份。
* `--path` (選用): 指定專案根目錄。預設自動向上反查定位至專案根目錄。

---

## 3. 防覆蓋鐵律 (Zero-Overwrite Guard)

* 若本地已存在目標月份目錄且包含 `Reimbursement.html`（代表該月份已完成清洗與儀表板產出），腳本將**嚴格拒絕下載並安全跳過**。
* 若目錄內已有同名單據，自動略過不重複拉取，杜絕破壞已手動識別之單據。
