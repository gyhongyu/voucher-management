import os
import re
import json
import sys

# Ensure output encoding is UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF for fast zero-CORS preview image rendering

def ensure_preview_image(pdf_or_img_path, previews_dir):
    """
    將單據檔案 (PDF / 圖片) 渲染為本地預覽圖，存放在 .previews 目錄。
    這樣瀏覽器不管是直接看或在 Canvas 中看，都能 100% 避開 file:// 協議的 CORS 攔截！
    """
    os.makedirs(previews_dir, exist_ok=True)
    filename = os.path.basename(pdf_or_img_path)
    base_name, ext = os.path.splitext(filename)
    preview_filename = f"{base_name}.png"
    preview_full_path = os.path.join(previews_dir, preview_filename)

    # 若已經渲染過且時間比來源新，則直接返回
    if os.path.exists(preview_full_path) and os.path.getmtime(preview_full_path) >= os.path.getmtime(pdf_or_img_path):
        return preview_filename

    try:
        if ext.lower() == '.pdf':
            doc = fitz.open(pdf_or_img_path)
            if len(doc) > 0:
                page = doc[0]
                # 2x 分辨率渲染以確保高清清晰度 (144 DPI)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                pix.save(preview_full_path)
                doc.close()
                return preview_filename
            doc.close()
        elif ext.lower() in ['.jpg', '.jpeg', '.png']:
            # 圖片直接複製或由 PyMuPDF 轉換
            import shutil
            shutil.copy2(pdf_or_img_path, preview_full_path)
            return preview_filename
    except Exception as e:
        print(f"警告: 渲染預覽圖失敗 {filename}: {e}")

    return None

def parse_filename(filepath):
    filename = os.path.basename(filepath)
    # Match standard format: DD-MMM-YY-desc-amount.pdf/jpg
    match = re.match(r'^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$', filename, re.IGNORECASE)
    if match:
        day, month_str, year, desc, amount, ext = match.groups()
        months = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
                  'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
        month = months.get(month_str.capitalize(), '01')
        date_str = f"20{year}/{month}/{day}"
        return {
            "date": date_str,
            "desc": desc,
            "amount": amount,
            "customer": "",
            "summary": desc,
            "path": filepath
        }
    return None

def main():
    if len(sys.argv) < 2:
        print("錯誤: 未指定目標月份資料夾名稱！")
        print("用法: python generate_dashboard.py <月份資料夾名稱>")
        print("範例: python generate_dashboard.py \"May to Jun\"")
        sys.exit(1)

    month_name = sys.argv[1]
    workspace_root = r"E:\Projects\Voucher management"
    
    # 優先尋找 Business Trip 下的月份目錄，其次尋找根目錄或傳入的絕對路徑
    candidate_paths = [
        os.path.join(workspace_root, "Business Trip", month_name),
        os.path.join(workspace_root, month_name),
        month_name
    ]
    month_dir = None
    for cp in candidate_paths:
        if os.path.exists(cp) and os.path.isdir(cp):
            month_dir = cp
            break

    if not month_dir:
        # 如果尚未建立，預設建立於 Business Trip 下
        month_dir = os.path.join(workspace_root, "Business Trip", month_name)
        if not os.path.exists(month_dir):
            print(f"錯誤: 找不到目標資料夾 '{month_name}' (已搜尋: {candidate_paths})")
            sys.exit(1)

    pr_dir = os.path.join(month_dir, "Public Relations")
    trans_dir = os.path.join(month_dir, "Transportation")
    other_dir = os.path.join(month_dir, "Other Expenses")

    previews_dir = os.path.join(month_dir, ".previews")

    pr_items = []
    if os.path.exists(pr_dir):
        for f in os.listdir(pr_dir):
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                full_p = os.path.join(pr_dir, f)
                parsed = parse_filename(full_p)
                if parsed:
                    parsed['rel_path'] = os.path.relpath(full_p, month_dir).replace('\\', '/')
                    prev_file = ensure_preview_image(full_p, previews_dir)
                    parsed['preview_img'] = f".previews/{prev_file}" if prev_file else parsed['rel_path']
                    pr_items.append(parsed)

    trans_items = []
    if os.path.exists(trans_dir):
        for f in os.listdir(trans_dir):
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                full_p = os.path.join(trans_dir, f)
                parsed = parse_filename(full_p)
                if parsed:
                    parsed['rel_path'] = os.path.relpath(full_p, month_dir).replace('\\', '/')
                    prev_file = ensure_preview_image(full_p, previews_dir)
                    parsed['preview_img'] = f".previews/{prev_file}" if prev_file else parsed['rel_path']
                    trans_items.append(parsed)

    other_items = []
    if os.path.exists(other_dir):
        for f in os.listdir(other_dir):
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                full_p = os.path.join(other_dir, f)
                parsed = parse_filename(full_p)
                if parsed:
                    parsed['rel_path'] = os.path.relpath(full_p, month_dir).replace('\\', '/')
                    prev_file = ensure_preview_image(full_p, previews_dir)
                    parsed['preview_img'] = f".previews/{prev_file}" if prev_file else parsed['rel_path']
                    other_items.append(parsed)

    # Dynamic variables for HTML
    normalized_slug = month_name.lower().replace(" ", "_")
    storage_key = f"vouchers_data_{normalized_slug}"
    page_title = f"{month_name} 報銷單據管理器 v2.1"
    dashboard_header = f"Voucher Manager - {month_name}"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <!-- Alpine.js 響應式框架 -->
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <!-- Mozilla PDF.js 純前端 Canvas 渲染引擎 (徹底解決 file:// iframe 安全攔截) -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --bg: #0b0f19;
            --card-bg: rgba(22, 30, 49, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: rgba(255, 255, 255, 0.08);
            --success: #10b981;
            --accent: #38bdf8;
            --highlight: rgba(56, 189, 248, 0.18);
            --highlight-border: #38bdf8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            margin: 0;
            padding: 1.5rem;
            min-height: 100vh;
            overflow-x: hidden;
        }}
        /* 雙欄主架構：左側表格清單 ＋ 右側抽屜式預覽面板 */
        .app-layout {{
            display: flex;
            width: 100%;
            gap: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .main-column {{
            flex: 1;
            min-width: 0;
            transition: all 0.3s ease;
        }}
        .drawer-column {{
            width: var(--drawer-width, 52%);
            min-width: 380px;
            max-width: 85%;
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 1rem;
            box-shadow: -8px 0 25px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            height: calc(100vh - 3rem);
            position: sticky;
            top: 1.5rem;
            overflow: hidden;
            transition: width 0.05s ease;
        }}
        /* 抽屜左側拖曳把手 (Splitter Bar) */
        .drawer-resizer {{
            width: 8px;
            cursor: col-resize;
            background: rgba(255, 255, 255, 0.05);
            transition: background 0.2s;
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            z-index: 50;
        }}
        .drawer-resizer:hover, .drawer-resizer.dragging {{
            background: var(--primary);
            box-shadow: 0 0 10px rgba(99, 102, 241, 0.6);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        h1 {{
            font-weight: 700;
            font-size: 1.85rem;
            margin: 0;
            background: linear-gradient(to right, #818cf8, #c084fc, #38bdf8);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .actions-group {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .btn-main {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.55rem 1.1rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .btn-main:hover {{
            background: var(--primary-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.06);
            color: #cbd5e1;
            border: 1px solid var(--border);
            padding: 0.55rem 1.1rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.12);
            color: #fff;
            transform: translateY(-1px);
        }}
        .tips-banner {{
            margin-bottom: 1.25rem;
            font-size: 0.85rem;
            color: var(--text-dim);
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 0.6rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-card {{
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 0.85rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.75rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
        }}
        .section-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #818cf8;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        th {{
            color: var(--text-dim);
            font-weight: 600;
            padding: 0.75rem 0.6rem;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 0.85rem 0.6rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.92rem;
            vertical-align: middle;
            transition: background-color 0.2s;
        }}
        tbody tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        /* 當前預覽/選中行高亮 */
        tr.active-row td {{
            background: var(--highlight) !important;
            border-bottom-color: var(--highlight-border) !important;
        }}
        tr.active-row td:first-child {{
            border-left: 3px solid var(--highlight-border);
            border-top-left-radius: 4px;
            border-bottom-left-radius: 4px;
        }}
        .editable {{
            transition: all 0.2s;
            padding: 0.25rem 0.45rem;
            border-radius: 0.35rem;
            cursor: text;
            min-height: 1.5rem;
            display: inline-block;
            width: 100%;
            box-sizing: border-box;
        }}
        .editable:hover {{
            background: rgba(255, 255, 255, 0.06);
        }}
        .editable:focus {{
            outline: 2px solid var(--primary);
            background: rgba(15, 23, 42, 0.9);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }}
        .copy-target {{
            cursor: pointer;
            user-select: none;
        }}
        .copy-target:active {{
            opacity: 0.6;
        }}
        .amount {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: #4ade80;
            font-size: 0.95rem;
        }}
        .btn-icon {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 0.35rem 0.65rem;
            border-radius: 0.4rem;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.15s ease;
            white-space: nowrap;
        }}
        .btn-icon:hover {{
            background: rgba(255, 255, 255, 0.12);
            color: white;
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .btn-preview {{
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.25);
            font-weight: 500;
        }}
        .btn-preview:hover, .btn-preview.active {{
            background: rgba(56, 189, 248, 0.3);
            color: #bae6fd;
            border-color: rgba(56, 189, 248, 0.55);
        }}
        .btn-danger {{
            color: #f87171;
            border-color: rgba(248, 113, 113, 0.2);
        }}
        .btn-danger:hover {{
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            border-color: rgba(248, 113, 113, 0.4);
        }}
        .date-badge {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.25rem 0.5rem;
            border-radius: 0.4rem;
            font-size: 0.88rem;
            color: #e2e8f0;
            letter-spacing: 0.02em;
        }}
        .badge-count {{
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.3);
            padding: 0.2rem 0.6rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        .copy-toast {{
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: var(--success);
            color: white;
            padding: 0.65rem 1.5rem;
            border-radius: 2rem;
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            z-index: 2000;
            font-weight: 600;
            font-size: 0.9rem;
            pointer-events: none;
        }}

        /* 抽屜頭部與工具列 */
        .drawer-header {{
            padding: 0.85rem 1.25rem;
            background: #1e293b;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }}
        .drawer-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .drawer-title {{
            font-weight: 600;
            font-size: 0.95rem;
            color: #f1f5f9;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 80%;
        }}
        .drawer-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 0.5rem;
            padding: 0.4rem 0.75rem;
            font-size: 0.825rem;
        }}
        .toolbar-group {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .drawer-body {{
            flex: 1;
            background: #0f172a;
            position: relative;
            overflow: auto;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 1.5rem 1rem;
            cursor: grab;
            user-select: none;
        }}
        .drawer-body:active {{
            cursor: grabbing;
        }}
        .canvas-container {{
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
            border-radius: 0.35rem;
            overflow: hidden;
            display: inline-block;
            transition: transform 0.1s ease;
        }}
        .image-preview {{
            max-width: 100%;
            height: auto;
            border-radius: 0.35rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
            pointer-events: none;
        }}
        .loading-spinner {{
            color: #94a3b8;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding-top: 5rem;
        }}
        [x-cloak] {{ display: none !important; }}
    </style>
</head>
<body x-data="reimbursementApp()" @mouseup="clearTimer()" @touchend="clearTimer()" @keydown.window="handleKeyDown($event)">
    <div class="app-layout">
        <!-- 左側主畫面清單 -->
        <div class="main-column">
            <!-- 頂部 Header -->
            <div class="header">
                <div>
                    <h1>{dashboard_header}</h1>
                    <div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 0.35rem;">
                        出差報銷單據管理 ✕ 快速對齊報銷系統填報 (YYYY/MM/DD)
                    </div>
                </div>
                <div class="actions-group">
                    <input type="file" id="importFileInput" accept=".json" style="display: none;" @change="handleImportFile($event)">
                    <button class="btn-secondary" @click="document.getElementById('importFileInput').click()">
                        📥 匯入數據 (JSON)
                    </button>
                    <button class="btn-main" @click="exportData()">
                        💾 導出數據 (JSON)
                    </button>
                </div>
            </div>

            <div class="tips-banner">
                <div>
                    💡 <b>操作指南</b>：點擊文字可直接 <b>編輯</b>；長按 0.5 秒直接 <b>複製</b>；點擊 <b>👁️ 預覽</b> 開啟右側抽屜（支援放大/縮小/旋轉/鍵盤 ← → 切換）。
                </div>
                <div style="font-size: 0.8rem; color: var(--text-dim);">
                    所有編輯自動即時持久化於本機
                </div>
            </div>

            <!-- 公關費 Section -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <span>🏢 公關費 / 交際費 (Public Relations)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button class="btn-icon" @click="sortData('pr')">📅 日期排序切換</button>
                        <span class="badge-count" x-text="`共 ${{prItems.length}} 筆`"></span>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th width="14%">日期</th>
                            <th width="20%">描述</th>
                            <th width="12%">客戶</th>
                            <th width="22%">摘要</th>
                            <th width="12%">金額</th>
                            <th width="20%">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template x-for="(item, index) in prItems" :key="index">
                            <tr :class="{{ 'active-row': isCurrentItem('pr', index) }}" :id="'row-pr-' + index">
                                <td>
                                    <div contenteditable="true" class="date-badge editable copy-target" x-text="item.date" @blur="updateItem('pr', index, 'date', $event.target.innerText)" @mousedown="startTimer(item.date)" @touchstart="startTimer(item.date)" title="長按複製日期"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.desc" @blur="updateItem('pr', index, 'desc', $event.target.innerText)" @mousedown="startTimer(item.desc)" @touchstart="startTimer(item.desc)" title="長按複製描述"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.customer || '-'" @blur="updateItem('pr', index, 'customer', $event.target.innerText)" @mousedown="startTimer(item.customer)" @touchstart="startTimer(item.customer)" style="color: var(--text-dim);" title="長按複製客戶"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.summary || item.desc" @blur="updateItem('pr', index, 'summary', $event.target.innerText)" @mousedown="startTimer(item.summary || item.desc)" @touchstart="startTimer(item.summary || item.desc)" style="color: #38bdf8;" title="長按複製摘要"></div>
                                </td>
                                <td>
                                    <div class="amount"><span contenteditable="true" class="editable copy-target" x-text="item.amount" @blur="updateItem('pr', index, 'amount', $event.target.innerText)" @mousedown="startTimer(item.amount)" @touchstart="startTimer(item.amount)" title="長按複製金額"></span></div>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 0.35rem; align-items: center;">
                                        <button class="btn-icon" @click="copyText(item.path)" title="複製單據硬碟路徑">📎 路徑</button>
                                        <button class="btn-icon btn-preview" :class="{{ 'active': isCurrentItem('pr', index) }}" @click="selectPreview('pr', index)">👁️ 預覽</button>
                                        <button class="btn-icon btn-danger" @click="deleteItem('pr', index)">🗑️ 刪除</button>
                                    </div>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>

            <!-- 交通費 Section -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <span>🚖 交通費 (Transportation)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button class="btn-icon" @click="sortData('trans')">📅 日期排序切換</button>
                        <span class="badge-count" x-text="`共 ${{transItems.length}} 筆`"></span>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th width="14%">日期</th>
                            <th width="20%">描述</th>
                            <th width="12%">客戶</th>
                            <th width="22%">摘要</th>
                            <th width="12%">金額</th>
                            <th width="20%">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template x-for="(item, index) in transItems" :key="index">
                            <tr :class="{{ 'active-row': isCurrentItem('trans', index) }}" :id="'row-trans-' + index">
                                <td>
                                    <div contenteditable="true" class="date-badge editable copy-target" x-text="item.date" @blur="updateItem('trans', index, 'date', $event.target.innerText)" @mousedown="startTimer(item.date)" @touchstart="startTimer(item.date)" title="長按複製日期"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.desc" @blur="updateItem('trans', index, 'desc', $event.target.innerText)" @mousedown="startTimer(item.desc)" @touchstart="startTimer(item.desc)" title="長按複製描述"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.customer || '-'" @blur="updateItem('trans', index, 'customer', $event.target.innerText)" @mousedown="startTimer(item.customer)" @touchstart="startTimer(item.customer)" style="color: var(--text-dim);" title="長按複製客戶"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.summary || item.customer || item.desc" @blur="updateItem('trans', index, 'summary', $event.target.innerText)" @mousedown="startTimer(item.summary || item.customer || item.desc)" @touchstart="startTimer(item.summary || item.customer || item.desc)" style="color: #38bdf8;" title="長按複製摘要"></div>
                                </td>
                                <td>
                                    <div class="amount"><span contenteditable="true" class="editable copy-target" x-text="item.amount" @blur="updateItem('trans', index, 'amount', $event.target.innerText)" @mousedown="startTimer(item.amount)" @touchstart="startTimer(item.amount)" title="長按複製金額"></span></div>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 0.35rem; align-items: center;">
                                        <button class="btn-icon" @click="copyText(item.path)" title="複製單據硬碟路徑">📎 路徑</button>
                                        <button class="btn-icon btn-preview" :class="{{ 'active': isCurrentItem('trans', index) }}" @click="selectPreview('trans', index)">👁️ 預覽</button>
                                        <button class="btn-icon btn-danger" @click="deleteItem('trans', index)">🗑️ 刪除</button>
                                    </div>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>

            <!-- 其他費用 Section -->
            <div class="section-card" x-show="otherItems && otherItems.length > 0">
                <div class="section-header">
                    <div class="section-title">
                        <span>📦 其他費用 (Other Expenses)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button class="btn-icon" @click="sortData('other')">📅 日期排序切換</button>
                        <span class="badge-count" x-text="`共 ${{otherItems.length}} 筆`"></span>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th width="14%">日期</th>
                            <th width="20%">描述</th>
                            <th width="12%">客戶</th>
                            <th width="22%">摘要</th>
                            <th width="12%">金額</th>
                            <th width="20%">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template x-for="(item, index) in otherItems" :key="index">
                            <tr :class="{{ 'active-row': isCurrentItem('other', index) }}" :id="'row-other-' + index">
                                <td>
                                    <div contenteditable="true" class="date-badge editable copy-target" x-text="item.date" @blur="updateItem('other', index, 'date', $event.target.innerText)" @mousedown="startTimer(item.date)" @touchstart="startTimer(item.date)" title="長按複製日期"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.desc" @blur="updateItem('other', index, 'desc', $event.target.innerText)" @mousedown="startTimer(item.desc)" @touchstart="startTimer(item.desc)" title="長按複製描述"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.customer || '-'" @blur="updateItem('other', index, 'customer', $event.target.innerText)" @mousedown="startTimer(item.customer)" @touchstart="startTimer(item.customer)" style="color: var(--text-dim);" title="長按複製客戶"></div>
                                </td>
                                <td>
                                    <div contenteditable="true" class="editable copy-target" x-text="item.summary || item.desc" @blur="updateItem('other', index, 'summary', $event.target.innerText)" @mousedown="startTimer(item.summary || item.desc)" @touchstart="startTimer(item.summary || item.desc)" style="color: #38bdf8;" title="長按複製摘要"></div>
                                </td>
                                <td>
                                    <div class="amount"><span contenteditable="true" class="editable copy-target" x-text="item.amount" @blur="updateItem('other', index, 'amount', $event.target.innerText)" @mousedown="startTimer(item.amount)" @touchstart="startTimer(item.amount)" title="長按複製金額"></span></div>
                                </td>
                                <td>
                                    <div style="display: flex; gap: 0.35rem; align-items: center;">
                                        <button class="btn-icon" @click="copyText(item.path)" title="複製單據硬碟路徑">📎 路徑</button>
                                        <button class="btn-icon btn-preview" :class="{{ 'active': isCurrentItem('other', index) }}" @click="selectPreview('other', index)">👁️ 預覽</button>
                                        <button class="btn-icon btn-danger" @click="deleteItem('other', index)">🗑️ 刪除</button>
                                    </div>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 右側抽屜式預覽面板 (Drawer Preview) -->
        <div class="drawer-column" x-show="drawerOpen" x-cloak :style="`--drawer-width: ${{drawerWidth}}px;`">
            <!-- 邊緣拖曳調整寬度把手 -->
            <div class="drawer-resizer" @mousedown="startResize($event)" title="按住並左右拖曳調整視窗寬度"></div>

            <div class="drawer-header">
                <div class="drawer-title-row">
                    <div class="drawer-title" x-text="currentDocTitle"></div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <a :href="currentRawUrl" target="_blank" class="btn-icon" style="text-decoration: none;" title="新視窗打開">↗️ 另開</a>
                        <button class="btn-icon" @click="closeDrawer()" style="font-weight: bold;">✕ 關閉</button>
                    </div>
                </div>
                <!-- 預覽控制列：縮放、旋轉、上一筆/下一筆 -->
                <div class="drawer-toolbar">
                    <div class="toolbar-group">
                        <button class="btn-icon" @click="navigateItem(-1)" title="上一筆 (鍵盤 ←)">⬅️ 上一筆</button>
                        <span style="color: var(--text-dim); font-size: 0.8rem;" x-text="`${{currentFlatIndex + 1}} / ${{allFlattenedItems.length}}`"></span>
                        <button class="btn-icon" @click="navigateItem(1)" title="下一筆 (鍵盤 →)">下一筆 ➡️</button>
                    </div>
                    <div class="toolbar-group">
                        <button class="btn-icon" @click="zoomOut()" title="縮小 (Zoom -)">🔍 -</button>
                        <span style="font-family: 'JetBrains Mono', monospace; min-width: 42px; text-align: center;" x-text="`${{Math.round(zoomScale * 100)}}%`"></span>
                        <button class="btn-icon" @click="zoomIn()" title="放大 (Zoom +)">🔍 +</button>
                        <button class="btn-icon" @click="rotateDoc()" title="向右旋轉 90°">🔄 旋轉</button>
                        <button class="btn-icon" @click="resetView()" title="重設縮放與位置">↩️ 重置</button>
                    </div>
                </div>
            </div>

            <!-- 預覽主體：按住滑鼠左鍵可任意平移拖曳單據 (Pan & Drag) -->
            <div class="drawer-body"
                 @mousedown="startPan($event)"
                 @mousemove="onPan($event)"
                 @mouseup="endPan()"
                 @mouseleave="endPan()"
                 @wheel.prevent="onWheelZoom($event)">
                <div class="canvas-container" :style="`transform: translate(${{panX}}px, ${{panY}}px) scale(${{zoomScale}}) rotate(${{rotation}}deg); transform-origin: center center;`">
                    <img :src="currentPreviewImg" class="image-preview" alt="單據預覽">
                </div>
            </div>
        </div>
    </div>

    <!-- 複製成功提示 Toast -->
    <div x-show="showToast" x-transition class="copy-toast" x-text="toastMsg" x-cloak></div>

    <script>
        function reimbursementApp() {{
            const STORAGE_KEY = '{storage_key}';
            
            const defaultData = {{
                prItems: {json.dumps(pr_items, ensure_ascii=False)},
                transItems: {json.dumps(trans_items, ensure_ascii=False)},
                otherItems: {json.dumps(other_items, ensure_ascii=False)},
                deletedPaths: []
            }};

            // 確保所有項目具備 summary 欄位與正規化的 YYYY/MM/DD 日期
            const normalizeItems = (items) => {{
                return items.map(item => {{
                    if (item.date && item.date.includes('-')) {{
                        item.date = item.date.replace(/-/g, '/');
                    }}
                    if (item.summary === undefined) {{
                        item.summary = item.customer || item.desc || '';
                    }}
                    return item;
                }});
            }};

            defaultData.prItems = normalizeItems(defaultData.prItems);
            defaultData.transItems = normalizeItems(defaultData.transItems);
            defaultData.otherItems = normalizeItems(defaultData.otherItems);

            const saved = localStorage.getItem(STORAGE_KEY);
            let initialData;
            
            if (saved) {{
                try {{
                    initialData = JSON.parse(saved);
                    initialData.prItems = normalizeItems(initialData.prItems || []);
                    initialData.transItems = normalizeItems(initialData.transItems || []);
                    initialData.otherItems = normalizeItems(initialData.otherItems || []);
                    initialData.deletedPaths = initialData.deletedPaths || [];
                    const deletedSet = new Set(initialData.deletedPaths);
                    
                    const defaultPaths = new Set([
                        ...defaultData.prItems.map(i => i.path),
                        ...defaultData.transItems.map(i => i.path),
                        ...defaultData.otherItems.map(i => i.path)
                    ]);

                    const originalPrLen = initialData.prItems.length;
                    const originalTransLen = initialData.transItems.length;
                    const originalOtherLen = initialData.otherItems.length;

                    initialData.prItems = initialData.prItems.filter(i => defaultPaths.has(i.path));
                    initialData.transItems = initialData.transItems.filter(i => defaultPaths.has(i.path));
                    initialData.otherItems = initialData.otherItems.filter(i => defaultPaths.has(i.path));
                    
                    let isUpdated = (originalPrLen !== initialData.prItems.length) || 
                                    (originalTransLen !== initialData.transItems.length) ||
                                    (originalOtherLen !== initialData.otherItems.length);

                    const existingPaths = new Set([
                        ...initialData.prItems.map(i => i.path),
                        ...initialData.transItems.map(i => i.path),
                        ...initialData.otherItems.map(i => i.path)
                    ]);
                    
                    defaultData.prItems.forEach(item => {{
                        if (!existingPaths.has(item.path) && !deletedSet.has(item.path)) {{
                            initialData.prItems.push(item);
                            isUpdated = true;
                        }}
                    }});
                    
                    defaultData.transItems.forEach(item => {{
                        if (!existingPaths.has(item.path) && !deletedSet.has(item.path)) {{
                            initialData.transItems.push(item);
                            isUpdated = true;
                        }}
                    }});

                    defaultData.otherItems.forEach(item => {{
                        if (!existingPaths.has(item.path) && !deletedSet.has(item.path)) {{
                            initialData.otherItems.push(item);
                            isUpdated = true;
                        }}
                    }});
                    
                    // 同步更新 preview_img 屬性至快取項目中
                    const pathMap = new Map();
                    [...defaultData.prItems, ...defaultData.transItems, ...defaultData.otherItems].forEach(it => {{
                        pathMap.set(it.path, it.preview_img);
                    }});

                    [initialData.prItems, initialData.transItems, initialData.otherItems].forEach(list => {{
                        list.forEach(it => {{
                            if (pathMap.has(it.path)) {{
                                it.preview_img = pathMap.get(it.path);
                            }}
                        }});
                    }});

                    if (isUpdated) {{
                        localStorage.setItem(STORAGE_KEY, JSON.stringify(initialData));
                    }}
                }} catch (e) {{
                    console.error('Failed to parse localStorage data:', e);
                    initialData = defaultData;
                }}
            }} else {{
                initialData = defaultData;
            }}

            return {{
                prItems: initialData.prItems,
                transItems: initialData.transItems,
                otherItems: initialData.otherItems,
                deletedPaths: initialData.deletedPaths || [],
                prSortAsc: false,
                transSortAsc: false,
                otherSortAsc: false,
                showToast: false,
                toastMsg: '',
                pressTimer: null,

                // 抽屜式預覽狀態
                drawerOpen: false,
                drawerWidth: 650,
                isResizing: false,
                activeCategory: '',
                activeIndex: -1,
                currentPreviewImg: '',
                currentRawUrl: '',
                currentDocTitle: '',
                zoomScale: 1.0,
                rotation: 0,
                panX: 0,
                panY: 0,
                isPanning: false,
                startX: 0,
                startY: 0,

                get allFlattenedItems() {{
                    const list = [];
                    this.prItems.forEach((it, idx) => list.push({{ category: 'pr', index: idx, item: it }}));
                    this.transItems.forEach((it, idx) => list.push({{ category: 'trans', index: idx, item: it }}));
                    this.otherItems.forEach((it, idx) => list.push({{ category: 'other', index: idx, item: it }}));
                    return list;
                }},

                get currentFlatIndex() {{
                    return this.allFlattenedItems.findIndex(x => x.category === this.activeCategory && x.index === this.activeIndex);
                }},

                isCurrentItem(category, index) {{
                    return this.drawerOpen && this.activeCategory === category && this.activeIndex === index;
                }},

                selectPreview(category, index) {{
                    this.activeCategory = category;
                    this.activeIndex = index;
                    const list = category === 'pr' ? this.prItems : (category === 'trans' ? this.transItems : this.otherItems);
                    const item = list[index];
                    if (!item) return;

                    let rawUrl = '';
                    if (item.rel_path) {{
                        rawUrl = encodeURI(item.rel_path);
                    }} else if (item.path) {{
                        const clean = item.path.replace(/\\\\/g, '/');
                        const parts = clean.split('/');
                        const folderIdx = parts.findIndex(p => p === 'Transportation' || p === 'Public Relations' || p === 'Other Expenses');
                        rawUrl = folderIdx !== -1 ? encodeURI(parts.slice(folderIdx).join('/')) : encodeURI(clean);
                    }}

                    // 優先使用 PyMuPDF 生成的高清 PNG 預覽圖
                    this.currentPreviewImg = item.preview_img ? encodeURI(item.preview_img) : rawUrl;
                    this.currentRawUrl = rawUrl;

                    const fileName = decodeURI(rawUrl.split('/').pop());
                    this.currentDocTitle = `📄 ${{item.desc || item.summary || '單據'}} (${{fileName}})`;
                    this.drawerOpen = true;
                    this.resetView();

                    this.$nextTick(() => {{
                        const row = document.getElementById(`row-${{category}}-${{index}}`);
                        if (row) row.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                    }});
                }},

                closeDrawer() {{
                    this.drawerOpen = false;
                    this.activeCategory = '';
                    this.activeIndex = -1;
                }},

                navigateItem(step) {{
                    const flat = this.allFlattenedItems;
                    if (flat.length === 0) return;
                    let nextIdx = this.currentFlatIndex + step;
                    if (nextIdx < 0) nextIdx = flat.length - 1;
                    if (nextIdx >= flat.length) nextIdx = 0;
                    const target = flat[nextIdx];
                    this.selectPreview(target.category, target.index);
                }},

                zoomIn() {{
                    if (this.zoomScale < 3.5) {{
                        this.zoomScale = Math.round((this.zoomScale + 0.15) * 100) / 100;
                    }}
                }},

                zoomOut() {{
                    if (this.zoomScale > 0.4) {{
                        this.zoomScale = Math.round((this.zoomScale - 0.15) * 100) / 100;
                    }}
                }},

                rotateDoc() {{
                    this.rotation = (this.rotation + 90) % 360;
                }},

                resetView() {{
                    this.zoomScale = 1.0;
                    this.rotation = 0;
                    this.panX = 0;
                    this.panY = 0;
                }},

                // --- 圖片拖曳平移 (Pan & Drag) ---
                startPan(e) {{
                    if (e.button !== 0) return; // 僅限左鍵
                    this.isPanning = true;
                    this.startX = e.clientX - this.panX;
                    this.startY = e.clientY - this.panY;
                }},

                onPan(e) {{
                    if (!this.isPanning) return;
                    this.panX = e.clientX - this.startX;
                    this.panY = e.clientY - this.startY;
                }},

                endPan() {{
                    this.isPanning = false;
                }},

                onWheelZoom(e) {{
                    if (e.deltaY < 0) {{
                        this.zoomIn();
                    }} else {{
                        this.zoomOut();
                    }}
                }},

                // --- 抽屜邊界寬度拖曳調整 (Resizer) ---
                startResize(e) {{
                    e.preventDefault();
                    this.isResizing = true;
                    const startMouseX = e.clientX;
                    const startW = this.drawerWidth;

                    const onMouseMove = (moveEvent) => {{
                        if (!this.isResizing) return;
                        const delta = startMouseX - moveEvent.clientX;
                        const newW = Math.max(380, Math.min(window.innerWidth * 0.85, startW + delta));
                        this.drawerWidth = Math.round(newW);
                    }};

                    const onMouseUp = () => {{
                        this.isResizing = false;
                        window.removeEventListener('mousemove', onMouseMove);
                        window.removeEventListener('mouseup', onMouseUp);
                    }};

                    window.addEventListener('mousemove', onMouseMove);
                    window.addEventListener('mouseup', onMouseUp);
                }},

                handleKeyDown(e) {{
                    if (!this.drawerOpen) return;
                    if (e.target.isContentEditable || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                    if (e.key === 'Escape') this.closeDrawer();
                    if (e.key === 'ArrowLeft') this.navigateItem(-1);
                    if (e.key === 'ArrowRight') this.navigateItem(1);
                    if (e.key === '+' || e.key === '=') this.zoomIn();
                    if (e.key === '-') this.zoomOut();
                    if (e.key === 'r' || e.key === 'R') this.rotateDoc();
                }},

                updateItem(type, index, field, value) {{
                    const list = type === 'pr' ? this.prItems : (type === 'trans' ? this.transItems : this.otherItems);
                    list[index][field] = value.trim();
                    this.saveToLocal();
                }},

                deleteItem(type, index) {{
                    const list = type === 'pr' ? this.prItems : (type === 'trans' ? this.transItems : this.otherItems);
                    const item = list[index];
                    if (confirm(`確定要從儀表板中移除此筆記錄嗎？\\n描述：${{item.desc}}\\n金額：${{item.amount}}`)) {{
                        if (item.path && !this.deletedPaths.includes(item.path)) {{
                            this.deletedPaths.push(item.path);
                        }}
                        list.splice(index, 1);
                        if (this.isCurrentItem(type, index)) {{
                            this.closeDrawer();
                        }}
                        this.saveToLocal();
                        this.notify('已成功移除記錄');
                    }}
                }},

                saveToLocal() {{
                    localStorage.setItem(STORAGE_KEY, JSON.stringify({{
                        prItems: this.prItems,
                        transItems: this.transItems,
                        otherItems: this.otherItems,
                        deletedPaths: this.deletedPaths
                    }}));
                }},

                exportData() {{
                    const data = JSON.stringify({{
                        prItems: this.prItems,
                        transItems: this.transItems,
                        otherItems: this.otherItems
                    }}, null, 4);
                    const blob = new Blob([data], {{ type: 'application/json' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `{month_name.replace(" ", "_")}_Vouchers_${{new Date().toISOString().slice(0,10)}}.json`;
                    a.click();
                    this.notify('數據已導出為 JSON');
                }},

                handleImportFile(event) {{
                    const file = event.target.files[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = (e) => {{
                        try {{
                            const imported = JSON.parse(e.target.result);
                            if (imported.prItems || imported.transItems || imported.otherItems) {{
                                this.prItems = normalizeItems(imported.prItems || []);
                                this.transItems = normalizeItems(imported.transItems || []);
                                this.otherItems = normalizeItems(imported.otherItems || []);
                                this.saveToLocal();
                                this.notify('🎉 成功匯入數據！已同步更新至儀表板');
                            }} else {{
                                alert('JSON 格式不符：找不到 prItems 或 transItems 欄位');
                            }}
                        }} catch (err) {{
                            alert('讀取 JSON 失敗，請確認檔案格式是否正確。');
                        }}
                    }};
                    reader.readAsText(file);
                    event.target.value = '';
                }},

                startTimer(text) {{
                    this.clearTimer();
                    this.pressTimer = setTimeout(() => {{ this.copyText(text); }}, 500);
                }},

                clearTimer() {{ if (this.pressTimer) clearTimeout(this.pressTimer); }},

                copyText(text) {{
                    if (!text || text === '-') return;
                    navigator.clipboard.writeText(text).then(() => {{ this.notify(`已複製: ${{text}}`); }});
                }},

                notify(msg) {{
                    this.toastMsg = msg;
                    this.showToast = true;
                    setTimeout(() => this.showToast = false, 2000);
                }},

                sortData(type) {{
                    if (type === 'pr') {{
                        this.prSortAsc = !this.prSortAsc;
                        this.prItems.sort((a, b) => this.prSortAsc ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
                    }} else if (type === 'trans') {{
                        this.transSortAsc = !this.transSortAsc;
                        this.transItems.sort((a, b) => this.transSortAsc ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
                    }} else {{
                        this.otherSortAsc = !this.otherSortAsc;
                        this.otherItems.sort((a, b) => this.otherSortAsc ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
                    }}
                    this.saveToLocal();
                }}
            }}
        }}
    </script>
</body>
</html>
"""

    html_path = os.path.join(month_dir, "Reimbursement.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"成功生成網頁儀表板: '{html_path}'")
    print(f"已載入 {len(pr_items)} 筆公關費單據，{len(trans_items)} 筆交通費單據，{len(other_items)} 筆其他費用單據。")

    # 4. Report files needing manual check
    manual_reviews = []
    for directory in [pr_dir, trans_dir, other_dir]:
        if os.path.exists(directory):
            for file_in_dir in os.listdir(directory):
                if file_in_dir.startswith("[需要手動確認]_"):
                    manual_reviews.append((directory, file_in_dir))

    if manual_reviews:
        print("\n⚠️ 待辦清單：以下檔案仍需要人工/AI代理進行多模態視覺辨識與手動重命名：")
        for idx, (directory, f_name) in enumerate(manual_reviews, 1):
            category = "公關費" if "Public Relations" in directory else ("交通費" if "Transportation" in directory else "其他費用")
            print(f"  {idx}. [{category}] {f_name}")
    else:
        print("\n🎉 所有單據皆已成功解析並完成標準化命名！")

if __name__ == "__main__":
    main()
