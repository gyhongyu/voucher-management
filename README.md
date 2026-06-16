# 報銷單據管理系統工作流說明 (Reimbursement Voucher Management Workflow)

> [!IMPORTANT]
> **🚨 專案屬性重要說明 (IMPORTANT NOTE FOR USERS & DEVELOPERS)**
> 本專案**不是**一個獨立運行的應用程式 (Standalone App)，也沒有內建任何雲端大模型 API。
> 它是一個專門設計與 **AI IDE 代理人 (如 Antigravity, Claude, Cursor, Codex 等 AI Agents)** 協同運作的「AI 代理原生工作流」。
>
> 專案中的 Python 腳本（`rename_vouchers.py`、`generate_dashboard.py`）僅作為本地執行輔助。當遇到無法自動解析的發票圖片或掃描 PDF 時，**必須依賴具備視覺 (Vision) 能力的 AI 代理人**進入目錄進行識別與重新命名。若您是一般使用者且未使用 AI 代理人，則需手動介入校對與命名。

此文件旨在為接手的 AI 代理及開發者提供本專案的最新工作流程指南、目錄結構說明及注意事項。

---

## 1. 專案概述
本專案用於自動化整理及管理每月的報銷單據（如計程車收據、餐飲公關發票等），最終生成一個具備搜尋、編輯、排序及路徑複製功能的網頁端儀表板（`Reimbursement.html`），並能導出結構化的 JSON 數據。

---

## 2. 目錄結構
所有腳本皆放在**專案根目錄**下，數據則依「月份」歸檔在子資料夾中：
```text
E:\Projects\Voucher management\
├── rename_vouchers.py             # [公用腳本] 圖片轉換與交通單據自動重命名
├── generate_dashboard.py          # [公用腳本] 掃描檔案並生成 Reimbursement.html
├── README.md                      # [本文檔] 工作流說明文件
├── Mar\                           # 三月份數據 (已整理)
│   ├── Public Relations\
│   ├── Transportation\
│   └── Reimbursement.html
├── Apr\                           # 四月份數據 (已整理)
│   ├── Public Relations\
│   ├── Transportation\
│   └── Reimbursement.html
└── May to Jun\                    # 五至六月份數據 (待處理)
    ├── Public Relations\          # 存放公關單據 (包含 JPG/PNG 圖片及 PDF)
    ├── Transportation\            # 存放交通單據 (包含計程車 PDF 收據)
    └── .backup_images\            # [自動生成] 用於存放已被轉換成 PDF 的原始圖片備份
```

---

## 3. 標準單據檔名格式
所有整理完畢的單據必須符合以下正則表達式格式：
`^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$`
*   **格式**：`{日期(DD-MMM-YY)}-{描述/路線}-{金額}.{副檔名}`
*   **月份對照**：`Jan`, `Feb`, `Mar`, `Apr`, `May`, `Jun`, `Jul`, `Aug`, `Sep`, `Oct`, `Nov`, `Dec` (首字母大寫)
*   **範例**：`08-Apr-26-Bengaluru-1690.pdf` 代表 2026年4月8日，於 Bengaluru，金額為 1690 的 PDF 單據。

---

## 4. 自動化工作流程 (Workflow)

接手新月份（以 `May to Jun` 為例）的處理步驟如下：

### 步驟 1：單據收集與歸檔
將所有原始發票圖片或 PDF 收據放至該月份對應的 `Public Relations` 與 `Transportation` 資料夾下。

### 步驟 2：執行公用命名與圖片轉換腳本
在專案根目錄下執行：
```bash
python rename_vouchers.py "May to Jun"
```
**此腳本將自動執行以下動作**：
1.  **圖片轉 PDF**：掃描並將所有 `.jpg`, `.jpeg`, `.png` 圖片利用 `Pillow` 轉換為 PDF，命名為 `[需要手動確認]_{原圖片名}.pdf`。
2.  **原圖安全備份**：轉換成功的原始圖片將被移至 `May to Jun/.backup_images/` 資料夾，避免直接刪除可能導致的風險。
3.  **交通收據文字解析**：針對 `Transportation` 下的電子 PDF 檔案，使用 `PyMuPDF` 提取文字並進行自動命名。若解析失敗，會被加上前綴 `[需要手動確認]_`。

### 步驟 3：AI 代理視覺協作辨識（重要）
對於檔案名帶有 `[需要手動確認]_` 前綴的檔案（如所有公關費圖片轉成的 PDF），由於無法自動解析文字，**接手此任務的 AI 代理需使用多模態視覺（Vision）能力**：
1.  「看」這些發票/圖片的畫面內容。
2.  識別出裡面的「日期」、「消費描述/路線」與「實付金額」。
3.  使用命令列將檔案手動改名為標準格式（例如：`20-May-26-Client Dinner-2500.pdf`），移除 `[需要手動確認]_` 前綴。

### 步驟 4：生成網頁端儀表板
當所有單據皆已命名完成（或部分待確認）時，執行以下命令生成網頁：
```bash
python generate_dashboard.py "May to Jun"
```
這將在 `May to Jun/` 底下生成獨立的 `Reimbursement.html`。
*   控制台會列印出目前**依然需要手動確認**的單據清單。

### 步驟 5：網頁端編輯與導出
1.  在瀏覽器中開啟該月份的 `Reimbursement.html`。
2.  **補充客戶資訊**：點擊「客戶」欄位直接輸入對應客戶名稱（此欄位無法從檔名自動提取）。
3.  點擊網頁右上角的 **「💾 導出數據 (JSON)」** 按鈕，導出 JSON 數據檔以供上報。

---

## 5. 開發與維護注意事項
*   **路徑安全性**：公用腳本必須藉由參數傳入月份資料夾名稱，防止在根目錄亂改檔案。
*   **無損合併 (Merge Cache)**：網頁端會自動將硬碟掃描到的最新檔案列表與 `localStorage` 快取比對並進行無損合併。清除瀏覽器快取會導致已編輯的「客戶名稱」遺失，應定期點擊導出 JSON 保存。

---

## 6. AI 代理協作模式 (No API Required)
本專案的自動化處理腳本 **不依賴任何外部大模型 API**（如 OpenAI 或 Gemini 的 API 密鑰），因此具有高安全性與零運算成本特性。

為了順利處理非文字型 PDF 與發票圖片，本專案採用 **「本地 AI IDE 代理人協作」** 機制：
1. **執行環境**：使用者需配合具備多模態視覺能力的本地 AI 程式開發工具（例如：**Antigravity、Claude (Cursor/Cline)、Codex** 等）使用此倉庫。
2. **協作流程**：
   * 當執行 `rename_vouchers.py` 後，若有些發票被命名為 `[需要手動確認]_*.pdf`，
   * 接手任務的 AI 代理會自動利用其內置的多模態視覺工具「閱讀」這些發票，提取正確的日期、城市與金額。
   * AI 代理會自動在終端執行改名指令進行標準化，並重新執行 `generate_dashboard.py` 更新報銷網頁。
   * 此機制完全不需要配置專案 API 密鑰，外部開發者只需在本地提供 AI IDE 環境即可直接搭配使用。
