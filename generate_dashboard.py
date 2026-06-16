import os
import re
import json
import sys

# Ensure output encoding is UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def parse_filename(filepath):
    filename = os.path.basename(filepath)
    # Match standard format: DD-MMM-YY-desc-amount.pdf/jpg
    match = re.match(r'^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$', filename, re.IGNORECASE)
    if match:
        day, month_str, year, desc, amount, ext = match.groups()
        months = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
                  'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
        month = months.get(month_str.capitalize(), '01')
        date_str = f"20{year}-{month}-{day}"
        return {
            "date": date_str,
            "desc": desc,
            "amount": amount,
            "customer": "",
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
    month_dir = os.path.join(workspace_root, month_name)

    if not os.path.exists(month_dir) or not os.path.isdir(month_dir):
        print(f"錯誤: 找不到目標資料夾 '{month_dir}'")
        sys.exit(1)

    pr_dir = os.path.join(month_dir, "Public Relations")
    trans_dir = os.path.join(month_dir, "Transportation")

    pr_items = []
    if os.path.exists(pr_dir):
        for f in os.listdir(pr_dir):
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                parsed = parse_filename(os.path.join(pr_dir, f))
                if parsed:
                    pr_items.append(parsed)

    trans_items = []
    if os.path.exists(trans_dir):
        for f in os.listdir(trans_dir):
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                parsed = parse_filename(os.path.join(trans_dir, f))
                if parsed:
                    trans_items.append(parsed)

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
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
            --success: #22c55e;
        }}
        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            margin: 0;
            padding: 2rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }}
        h1 {{
            font-weight: 700; font-size: 2rem; margin: 0;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .section-card {{
            background: var(--card-bg); backdrop-filter: blur(12px);
            border: 1px solid var(--border); border-radius: 1rem;
            padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }}
        .section-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem;
        }}
        .section-title {{ font-size: 1.25rem; font-weight: 600; color: #818cf8; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ color: var(--text-dim); font-weight: 500; padding: 0.75rem; font-size: 0.825rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ padding: 1rem 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.95rem; }}
        .editable {{ transition: all 0.2s; padding: 0.2rem 0.4rem; border-radius: 0.25rem; cursor: text; }}
        .editable:hover {{ background: rgba(255, 255, 255, 0.05); }}
        .editable:focus {{ outline: 2px solid var(--primary); background: rgba(255, 255, 255, 0.1); }}
        .copy-target {{ cursor: pointer; user-select: none; }}
        .copy-target:active {{ opacity: 0.7; }}
        .amount {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #4ade80; }}
        .btn-main {{
            background: var(--primary); color: white; border: none; padding: 0.6rem 1.2rem;
            border-radius: 0.6rem; font-weight: 600; cursor: pointer; transition: transform 0.2s;
            display: flex; align-items: center; gap: 0.5rem;
        }}
        .btn-main:hover {{ opacity: 0.9; transform: translateY(-1px); }}
        .btn-icon {{
            background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border); color: var(--text-dim);
            padding: 0.4rem 0.8rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.8rem; margin-right: 0.5rem;
        }}
        .btn-icon:hover {{ background: rgba(255, 255, 255, 0.1); color: white; }}
        .date-badge {{ background: rgba(255, 255, 255, 0.05); padding: 0.2rem 0.5rem; border-radius: 0.4rem; font-size: 0.85rem; color: var(--text-dim); }}
        .copy-toast {{
            position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
            background: var(--success); color: white; padding: 0.75rem 1.5rem; border-radius: 2rem;
            box-shadow: 0 10px 15px rgba(0,0,0,0.3); z-index: 1000; font-weight: 600;
        }}
        [x-cloak] {{ display: none !important; }}
    </style>
</head>
<body x-data="reimbursementApp()" @mouseup="clearTimer()" @touchend="clearTimer()">
    <div class="container">
        <div class="header">
            <h1>{dashboard_header}</h1>
            <button class="btn-main" @click="exportData()">💾 導出數據 (JSON)</button>
        </div>
        <div style="margin-bottom: 1rem; font-size: 0.85rem; color: var(--text-dim);">
            💡 提示：點擊內容即可 **修改**；長按日期/描述/金額 0.5 秒即可 **複製**。所有更改將自動保存到瀏覽器。
        </div>

        <!-- 公關費 Section -->
        <div class="section-card">
            <div class="section-header">
                <div class="section-title">🏢 公關費 (Public Relations)</div>
                <div>
                    <button class="btn-icon" @click="sortData('pr')">📅 排序切換</button>
                    <span class="date-badge" x-text="`共 ${{prItems.length}} 筆`"></span>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th width="15%">日期 (長按複製)</th>
                        <th width="20%">描述 (長按複製)</th>
                        <th width="20%">客戶 (長按複製)</th>
                        <th width="15%">金額 (長按複製)</th>
                        <th width="30%">文件操作</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="(item, index) in prItems" :key="index">
                        <tr>
                            <td>
                                <span class="date-badge copy-target" x-text="item.date" @mousedown="startTimer(item.date)" @touchstart="startTimer(item.date)"></span>
                            </td>
                            <td>
                                <div contenteditable="true" class="editable copy-target" x-text="item.desc" @blur="updateItem('pr', index, 'desc', $event.target.innerText)" @mousedown="startTimer(item.desc)" @touchstart="startTimer(item.desc)"></div>
                            </td>
                            <td>
                                <div contenteditable="true" class="editable copy-target" x-text="item.customer || '-'" @blur="updateItem('pr', index, 'customer', $event.target.innerText)" @mousedown="startTimer(item.customer)" @touchstart="startTimer(item.customer)" style="color: var(--text-dim);"></div>
                            </td>
                            <td>
                                <div class="amount"><span contenteditable="true" class="editable copy-target" x-text="item.amount" @blur="updateItem('pr', index, 'amount', $event.target.innerText)" @mousedown="startTimer(item.amount)" @touchstart="startTimer(item.amount)"></span></div>
                            </td>
                            <td>
                                <button class="btn-icon" @click="copyText(item.path)">📎 複製路徑</button>
                                <a :href="'file:///' + item.path.replace(/\\\\/g, '/')" target="_blank" class="btn-icon" style="text-decoration: none;">👁️ 預覽</a>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>

        <!-- 交通費 Section -->
        <div class="section-card">
            <div class="section-header">
                <div class="section-title">🚖 交通費 (Transportation)</div>
                <div>
                    <button class="btn-icon" @click="sortData('trans')">📅 排序切換</button>
                    <span class="date-badge" x-text="`共 ${{transItems.length}} 筆`"></span>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th width="15%">日期</th>
                        <th width="20%">路線描述</th>
                        <th width="20%">客戶 (長按複製)</th>
                        <th width="15%">金額</th>
                        <th width="30%">文件操作</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="(item, index) in transItems" :key="index">
                        <tr>
                            <td>
                                <span class="date-badge copy-target" x-text="item.date" @mousedown="startTimer(item.date)" @touchstart="startTimer(item.date)"></span>
                            </td>
                            <td>
                                <div contenteditable="true" class="editable copy-target" x-text="item.desc" @blur="updateItem('trans', index, 'desc', $event.target.innerText)" @mousedown="startTimer(item.desc)" @touchstart="startTimer(item.desc)"></div>
                            </td>
                            <td>
                                <div contenteditable="true" class="editable copy-target" x-text="item.customer || '-'" @blur="updateItem('trans', index, 'customer', $event.target.innerText)" @mousedown="startTimer(item.customer)" @touchstart="startTimer(item.customer)" style="color: var(--text-dim);"></div>
                            </td>
                            <td>
                                <div class="amount"><span contenteditable="true" class="editable copy-target" x-text="item.amount" @blur="updateItem('trans', index, 'amount', $event.target.innerText)" @mousedown="startTimer(item.amount)" @touchstart="startTimer(item.amount)"></span></div>
                            </td>
                            <td>
                                <button class="btn-icon" @click="copyText(item.path)">📎 複製路徑</button>
                                <a :href="'file:///' + item.path.replace(/\\\\/g, '/')" target="_blank" class="btn-icon" style="text-decoration: none;">👁️ 預覽</a>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>

    <div x-show="showToast" x-transition class="copy-toast" x-text="toastMsg" x-cloak></div>

    <script>
        function reimbursementApp() {{
            const STORAGE_KEY = '{storage_key}';
            
            const defaultData = {{
                prItems: {json.dumps(pr_items, ensure_ascii=False)},
                transItems: {json.dumps(trans_items, ensure_ascii=False)}
            }};

            const saved = localStorage.getItem(STORAGE_KEY);
            let initialData;
            
            if (saved) {{
                initialData = JSON.parse(saved);
                
                // --- 無損合併邏輯 (Merge without destroying cache) ---
                const defaultPaths = new Set([
                    ...defaultData.prItems.map(i => i.path),
                    ...defaultData.transItems.map(i => i.path)
                ]);

                // 1. 清理：移除快取中已經不存在於硬碟的檔案
                const originalPrLen = initialData.prItems.length;
                const originalTransLen = initialData.transItems.length;

                initialData.prItems = initialData.prItems.filter(i => defaultPaths.has(i.path));
                initialData.transItems = initialData.transItems.filter(i => defaultPaths.has(i.path));
                
                let isUpdated = (originalPrLen !== initialData.prItems.length) || (originalTransLen !== initialData.transItems.length);

                // 2. 新增：找出快取中保留下來的路徑
                const existingPaths = new Set([
                    ...initialData.prItems.map(i => i.path),
                    ...initialData.transItems.map(i => i.path)
                ]);
                
                // 檢查硬碟上的新單據，將其加入快取
                defaultData.prItems.forEach(item => {{
                    if (!existingPaths.has(item.path)) {{
                        initialData.prItems.push(item);
                        isUpdated = true;
                    }}
                }});
                
                defaultData.transItems.forEach(item => {{
                    if (!existingPaths.has(item.path)) {{
                        initialData.transItems.push(item);
                        isUpdated = true;
                    }}
                }});
                
                if (isUpdated) {{
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialData));
                    console.log('Detected new voucher files! Merged into cache.');
                }}
            }} else {{
                initialData = defaultData;
            }}

            return {{
                prItems: initialData.prItems,
                transItems: initialData.transItems,
                prSortAsc: false,
                transSortAsc: false,
                showToast: false,
                toastMsg: '',
                pressTimer: null,

                updateItem(type, index, field, value) {{
                    const list = type === 'pr' ? this.prItems : this.transItems;
                    list[index][field] = value;
                    this.saveToLocal();
                }},

                saveToLocal() {{
                    localStorage.setItem(STORAGE_KEY, JSON.stringify({{
                        prItems: this.prItems,
                        transItems: this.transItems
                    }}));
                }},

                exportData() {{
                    const data = JSON.stringify({{
                        prItems: this.prItems,
                        transItems: this.transItems
                    }}, null, 4);
                    const blob = new Blob([data], {{ type: 'application/json' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `{month_name.replace(" ", "_")}_Vouchers_${{new Date().toISOString().slice(0,10)}}.json`;
                    a.click();
                    this.notify('數據已導出為 JSON');
                }},

                startTimer(text) {{
                    this.clearTimer();
                    this.pressTimer = setTimeout(() => {{ this.copyText(text); }}, 500);
                }},

                clearTimer() {{ if (this.pressTimer) clearTimeout(this.pressTimer); }},

                copyText(text) {{
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
                    }} else {{
                        this.transSortAsc = !this.transSortAsc;
                        this.transItems.sort((a, b) => this.transSortAsc ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
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
    print(f"已載入 {len(pr_items)} 筆公關費單據，{len(trans_items)} 筆交通費單據。")

    # 4. Report files needing manual check
    manual_reviews = []
    for directory in [pr_dir, trans_dir]:
        if os.path.exists(directory):
            for file_in_dir in os.listdir(directory):
                if file_in_dir.startswith("[需要手動確認]_"):
                    manual_reviews.append((directory, file_in_dir))

    if manual_reviews:
        print("\n⚠️ 待辦清單：以下檔案仍需要人工/AI代理進行多模態視覺辨識與手動重命名：")
        for idx, (directory, f_name) in enumerate(manual_reviews, 1):
            category = "公關費" if "Public Relations" in directory else "交通費"
            print(f"  {idx}. [{category}] {f_name}")
    else:
        print("\n🎉 所有單據皆已成功解析並完成標準化命名！")

if __name__ == "__main__":
    main()
