# 📜 出差報銷單據數據契約與跨環境雙軌同構規範 (Data Contract & Dual-Track Spec)

> **核心目標**：保證本地 Python CLI 腳本與未來 GitHub 靜態 Web 前端（Vanilla JS + LLM API）遵循 100% 同一組命名正規、分類標籤與 JSON 總帳結構，實現「雙軌等價（Isomorphic Parity）」。

---

## 1. 單據檔案標準命名合約 (Naming Specification)

所有經過清洗、識別或確認之正式單據（PDF 或 JPG），檔名必須完全相符以下正規表達式：

### 正則規範
* **Python**:
  ```python
  import re
  STANDARD_PATTERN = re.compile(r'^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$', re.IGNORECASE)
  ```
* **JavaScript (Web 前端)**:
  ```javascript
  const STANDARD_PATTERN = /^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$/i;
  ```

### 檔名結構拆解
`{DD}-{MMM}-{YY}-{Route_or_Description}-{Amount}.{ext}`
* `{DD}`: 2 位數日期（01-31）
* `{MMM}`: 3 位英文月份縮寫（Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec）
* `{YY}`: 2 位少年份（如 26 代表 2026）
* `{Route_or_Description}`: 地點起迄路線（如 `Gurgaon to Gurgaon`）或消費店家名稱（如 `Barbeque Nation`）
* `{Amount}`: 四捨五入後之整數金額（以盧比 ₹ 計）

### 特殊狀態前綴
* `[需要手動確認]_`: 當自動解析信心不足、或缺少必要欄位時，暫時保留的前綴，引導 AI 視覺模型或人工審查。

---

## 2. 目錄分類與類別映射 (Category Mapping)

專案嚴格維持三大業務分類目錄，禁止隨意建立額外分類：

| 業務簡稱 (Category Key) | 目錄名稱 (Folder Name) | 涵蓋單據類型 |
| :--- | :--- | :--- |
| `trans` | `Transportation` | 交通支出：Uber 收據、計程車 Cab 單據、過路費 MCD Toll 等 |
| `pr` | `Public Relations` | 公關宴請：客戶用餐發票、商務宴客收據、餐飲掃描檔 |
| `other` | `Other Expenses` | 雜項支出：清關費、列印費、飯店雜項等 |
| - | `.backup_images` | 系統隱藏目錄：JPG/PNG 轉為 PDF 後的原始圖片存檔區（防覆蓋） |
| - | `.previews` | 系統隱藏目錄：用於 HTML/Web 避開 CORS 高清渲染之垂直拼接預覽圖 |

---

## 3. 結構化總帳契約 (`<Month>_Vouchers.json`)

每個月份之報銷總表，均有同名結構化 JSON 作為單一真理源（SSOT）：

```json
{
  "transItems": [
    {
      "date": "2026/09/25",
      "desc": "Gurgaon to Gurgaon",
      "amount": "350",
      "customer": "",
      "summary": "Gurgaon to Gurgaon",
      "path": "E:/Projects/Voucher management/Business Trip/Sep 2026/Transportation/25-Sep-26-Gurgaon to Gurgaon-350.pdf",
      "rel_path": "Transportation/25-Sep-26-Gurgaon to Gurgaon-350.pdf",
      "preview_img": ".previews/25-Sep-26-Gurgaon to Gurgaon-350.png"
    }
  ],
  "prItems": [],
  "otherItems": []
}
```

### 欄位字典
* `date`: `YYYY/MM/DD` 格式字串，供總表依日期升序排序。
* `desc`: 起迄路線或商務說明。
* `amount`: 整數字串或數值，供總計求和。
* `customer`: 客戶名稱（公關費通常填寫拜訪對象）。
* `summary`: 摘要備註。
* `path`: 本地絕對路徑（本地 CLI 使用）。
* `rel_path`: 相對於月份資料夾之相對路徑（Web 靜態部屬與預覽使用）。
* `preview_img`: 預覽圖相對路徑。

---

## 4. LLM API 多模態結構化 Prompt 合約 (未來 Web 端與 Agent 開眼共用)

當未來 Web 前端調用外部大模型（如 OpenRouter 或 OpenAI 視覺模型），或本地 Agent 開眼時，要求 LLM 回傳嚴格 JSON：

```json
{
  "date": "25-Sep-26",
  "category": "trans",
  "route_or_store": "Gurgaon to Gurgaon",
  "amount": 350,
  "confidence": 0.95
}
```
* Web JS 接收後，將自動拼裝為標準檔名：`25-Sep-26-Gurgaon to Gurgaon-350.pdf`，與本地 Python 邏輯 100% 對齊。
