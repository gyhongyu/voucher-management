# 報銷單據管理系統 (Voucher Management Pipeline)

> [!IMPORTANT]
> **🚨 專案架構重要聲明**
> 本專案為標準的 **「AI 代理人原生 ＋ CLI 確定性管線」** 出差報銷單據治理系統。
> 專案內已全面收斂至三大標準專案技能（`.agents/skills/`），遵循 **全域技能架構師 Authoring Standard v2.0** 與 **跨環境數據契約 ([data_contract.md](.agents/skills/voucher_pipeline_manager/references/data_contract.md))**。
> 本地處理不依賴外部收費 API；當遇到掃描圖或手寫單據時，由具備多模態視覺（Vision）的 AI 代理人直接開眼協同命名。未來亦支援無縫擴展至 Web 靜態端（Vanilla JS + LLM API）雙軌並行。

---

## 1. 核心管線三件套 (Core Skills Suite)

專案嚴格將外部渠道攝取與內部數據清洗分離為 3 大專業技能：

```mermaid
graph LR
    subgraph 1. 外部渠道攝取 (Ingestion)
        A1["google_drive_downloader<br/>(Google Drive 雲端增量拉取)"]
        A2["voucher_receipt_collector<br/>(Notes / Gmail 抓取 Uber 車單)"]
    end

    subgraph 2. 本地清洗與總表產出 (Processing & Presentation)
        B["voucher_pipeline_manager<br/>(分流 ➔ 轉檔備份 ➔ 文字抽取更名 ➔ 儀表板/台帳 ➔ 微創補單)"]
    end

    A1 -->|Raw 檔案| B
    A2 -->|Raw 檔案| B
```

| 技能模組 | 職責與邊界 | 常用指令 |
| :--- | :--- | :--- |
| **[`google_drive_downloader`](.agents/skills/google_drive_downloader/SKILL.md)** | 負責從 Google Drive `Business Trip` 雲端目錄單向增量同步出差發票至本地，具備防覆蓋保護。 | `py .agents/skills/google_drive_downloader/scripts/drive_downloader.py` |
| **[`voucher_receipt_collector`](.agents/skills/voucher_receipt_collector/SKILL.md)** | 負責從企業 NotesMaster 或 GAS Gmail 網關檢索 Uber 乘車收據並導出為標準 PDF。 | `py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --month "Sep-26" -o "Business Trip/Sep 2026/Transportation"` |
| **[`voucher_pipeline_manager`](.agents/skills/voucher_pipeline_manager/SKILL.md)** | 本地主管線：散落單據智能分流、Pillow 圖片轉 PDF、PyMuPDF 交通單據正規命名、AI 開眼協同、生成 `Reimbursement.html` 與微創補登。 | `py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run "<月份資料夾>"` |

---

## 2. 標準目錄結構

所有出差月份統一存放於 `Business Trip/` 目錄下（具備歷史資料夾自動相容尋址）：

```text
E:\Projects\Voucher management\
├── .agents/
│   ├── rules/
│   │   └── voucher_workflow_knowledge.md   # [按需喚醒] 新代理人進場認知與工作流規則
│   └── skills/
│       ├── google_drive_downloader/        # 雲端硬碟單向增量下載總管
│       ├── voucher_receipt_collector/       # Notes/Gmail 收據收集大師
│       └── voucher_pipeline_manager/       # 單據全流程流水線與儀表板總管
├── Business Trip/                          # 出差單據核心目錄 (SSOT)
│   └── Sep 2026/                           # 範例出差月份
│       ├── Transportation/                 # 交通單據 (Uber / Cab / Toll PDF)
│       ├── Public Relations/               # 公關費用 (宴請發票 / 餐廳收據)
│       ├── Other Expenses/                 # 其他雜項 (清關 / 列印 / 雜費)
│       ├── .backup_images/                 # 系統備份 (轉為 PDF 後的原始照片)
│       ├── .previews/                      # 高清預覽 (垂直拼接避免 CORS 攔截圖)
│       ├── Reimbursement.html              # 獨立報銷總表儀表板
│       └── Sep_2026_Vouchers.json          # 結構化總帳數據
├── README.md                               # [本文檔]
└── AGENTS.md                               # [母法自鎖] 根目錄 1 行憲法
```

---

## 3. 數據契約與檔名標準 (Data Contract)

為保障本地 Python 腳本與未來 Web 前端（Vanilla JS + LLM API）100% 同構，所有單據檔名必須完全符合統一正規：

* **正規表達式**：
  * Python: `^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$`
  * JavaScript: `/^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$/i`
* **格式說明**：`{DD}-{MMM}-{YY}-{Route_or_Description}-{Amount}.pdf`
  * 例：`25-Sep-26-Gurgaon to Gurgaon-350.pdf`
* **完整數據規範**：參閱 [`references/data_contract.md`](.agents/skills/voucher_pipeline_manager/references/data_contract.md)。

---

## 4. 標準作業流程 (SOP)

### 階段一：單據攝取 (Ingestion)
出差結束後，透過外部渠道拉取單據：
```bash
# 方式 A：從 Google Drive 增量同步出差單據
py .agents/skills/google_drive_downloader/scripts/drive_downloader.py --month "Sep 2026"

# 方式 B：從 Notes / Gmail 提取 Uber 乘車收據
py .agents/skills/voucher_receipt_collector/scripts/voucher_receipt_collector.py collect --month "Sep-26" -o "Business Trip/Sep 2026/Transportation"
```

### 階段二：執行全自動流水線
```bash
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py run "Sep 2026"
```
腳本將全自動完成：
1. 目錄結構自動補全（Transportation / Public Relations / Other Expenses / .backup_images）。
2. 散落檔案特徵識別與自動分流。
3. 圖片無損轉換為標準 PDF，原始照片搬遷至 `.backup_images/` 嚴防丟失。
4. 電子 PDF 文字萃取、路線辨識與標準重命名。
5. 渲染垂直拼接多頁預覽圖至 `.previews/`，並產出獨立 `Reimbursement.html` 與 `<月份>_Vouchers.json`。

### 階段三：AI 代理人多模態開眼（處理未辨識發票）
若終端提示有帶 `[需要手動確認]_` 的單據（如餐飲照片或無文字層之掃描檔）：
1. AI 代理人調用內置多模態視覺工具檢視該發票圖片。
2. 辨識日期、店名與金額，並標準更名（如：`25-Sep-26-Restaurant Name-1500.pdf`）。
3. 重新執行一次 `voucher_pipeline.py run "Sep 2026"` 刷新總表。

### 階段四：後續漏單據微創追加（Zero-Overwrite）
若後續有零星漏上傳的單據，**嚴禁全局推倒重新執行**，直接調用微創補單命令：
```bash
py .agents/skills/voucher_pipeline_manager/scripts/voucher_pipeline.py patch "<單據檔案路徑>" --month "Sep 2026" --type trans
```
該命令會自動辨識單據、安全搬移、渲染預覽圖、微創追加進 `Reimbursement.html` 的 `defaultData` 並同步維護 JSON 總帳！

---

## 5. 跨環境擴展性 (Future Web Track)
本專案已做好對齊 Web 靜態部署的同構準備：
* 檔名正規、目錄分類映射與 JSON 總帳字典均已固化。
* 未來建立 GitHub Pages 靜態前端時，直接調用外部 LLM API 解析發票，本地與網頁端產出格式 100% 互通。
