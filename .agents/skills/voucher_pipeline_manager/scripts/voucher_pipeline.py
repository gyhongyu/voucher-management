# -*- coding: utf-8 -*-
"""
voucher_pipeline.py - Voucher Management 全流程流水線整合總管
=============================================================================
職責：
  1. 智能目錄初始化: 確保目標月份目錄具備 Transportation, Public Relations, Other Expenses, .backup_images
  2. 智能分流 (Triaging): 若根目錄有散落單據，依檔案特徵 (Uber/Cab ➔ Trans, 發票圖片 ➔ PR, 其它 ➔ Other) 安全歸位
  3. 圖片轉檔與備份: 調用 Pillow 將圖片轉換為 [需要手動確認]_xxx.pdf，原圖移入 .backup_images
  4. 電子單據自動命名: 提取文字並以正則命名為 {DD-MMM-YY}-{Route}-{Amount}.pdf
  5. 待確認單據標記: 無法自動辨識之單據自動加上 [需要手動確認]_ 前綴，提示 AI 視覺辨識
  6. 儀表板總表產出: 調用 generate_dashboard 產生該月份獨立的 Reimbursement.html
=============================================================================
"""

import os
import re
import sys
import glob
import json
import shutil
import io
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# 設定 Windows 控制台 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

STANDARD_PATTERN = re.compile(r'^(\d{2})-([A-Za-z]{3})-(\d{2})-(.+)-(\d+)\.(pdf|jpg|jpeg|png)$', re.IGNORECASE)

KNOWN_LOCATIONS = ["gurugram", "gurgaon", "delhi", "noida", "bengaluru", "bangalore", "hyderabad", "manesar", "indore", "mumbai", "chennai"]

def parse_date(date_str: str) -> Optional[str]:
    date_str = date_str.strip().replace(',', '')
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    formats = [
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
        "%Y-%m-%d"
    ]
    date_str = re.sub(r'\s+\d{1,2}:\d{2}\s*[AP]M', '', date_str, flags=re.IGNORECASE).strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%b-%y")
        except ValueError:
            pass
    return None

def triage_files(month_dir: Path) -> Tuple[int, int, int]:
    """
    智能分流：將散落在月份資料夾根目錄的單據，自動分流至三大分類目錄
    """
    pr_dir = month_dir / "Public Relations"
    trans_dir = month_dir / "Transportation"
    other_dir = month_dir / "Other Expenses"
    backup_dir = month_dir / ".backup_images"

    for d in [pr_dir, trans_dir, other_dir, backup_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 掃描散落在月份根目錄的單據
    scattered_files = [f for f in month_dir.iterdir() if f.is_file() and f.name.lower() != "reimbursement.html" and not f.name.endswith(".json")]

    trans_count = 0
    pr_count = 0
    other_count = 0

    for file_path in scattered_files:
        ext = file_path.suffix.lower()
        fname = file_path.name

        # 圖片一律視為發票/公關單據，分流至 PR
        if ext in ['.jpg', '.jpeg', '.png']:
            dest = pr_dir / fname
            shutil.move(str(file_path), str(dest))
            pr_count += 1
            continue

        # PDF 探測文字內容
        if ext == '.pdf':
            is_trans = False
            is_scanned = False
            try:
                doc = fitz.open(str(file_path))
                full_text = ""
                for page in doc:
                    full_text += page.get_text() + "\n"
                doc.close()

                text_lower = full_text.lower()

                # 交通收據關鍵詞 (Uber, Cab, Ride, Distance, MCD Toll)
                if any(k in text_lower for k in ["thanks for riding", "cab_receipt", "trip fare", "uber", "driver", "toll", "total fare", "booking fee"]):
                    is_trans = True
                elif len(full_text.strip()) == 0:
                    # 無文字層之純掃描 PDF，優先歸入 PR 待 AI 視覺辨識
                    is_scanned = True
            except Exception:
                pass

            if is_trans or "cab" in fname.lower() or "receipt" in fname.lower() and not "pr" in fname.lower():
                dest = trans_dir / fname
                shutil.move(str(file_path), str(dest))
                trans_count += 1
            elif is_scanned or "scan" in fname.lower() or "invoice" in fname.lower():
                dest = pr_dir / fname
                shutil.move(str(file_path), str(dest))
                pr_count += 1
            else:
                dest = other_dir / fname
                shutil.move(str(file_path), str(dest))
                other_count += 1

    return trans_count, pr_count, other_count

def convert_images_in_dir(target_dir: Path, backup_dir: Path) -> int:
    """轉換資料夾內所有圖片為 PDF 並安全備份原圖"""
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        images.extend(list(target_dir.glob(ext)))
    images = list(set(images))

    converted = 0
    for img_path in images:
        base_name = img_path.stem
        pdf_name = f"[需要手動確認]_{base_name}.pdf"
        pdf_path = target_dir / pdf_name

        try:
            img = Image.open(str(img_path))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(str(pdf_path), "PDF")
            img.close()

            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                backup_path = backup_dir / img_path.name
                if backup_path.exists():
                    timestamp = datetime.now().strftime("%H%M%S")
                    backup_path = backup_dir / f"{base_name}_{timestamp}{img_path.suffix}"
                shutil.move(str(img_path), str(backup_path))
                converted += 1
        except Exception as e:
            print(f"⚠️ 轉換圖片 {img_path.name} 失敗: {e}")

    return converted

def parse_single_trans_pdf(file_path: Path) -> Tuple[Optional[str], Optional[int], str]:
    """解析單張交通 PDF 單據的日期、金額與路線"""
    try:
        doc = fitz.open(str(file_path))
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()

        date_val = None
        amount_val = None
        desc_val = "Gurgaon to Gurgaon"

        # 1. 解析日期
        date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{2,9}\s+\d{4})|([A-Za-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?(?:,)?\s*\d{4})', text)
        if date_match:
            matched_str = date_match.group(1) if date_match.group(1) else date_match.group(2)
            date_val = parse_date(matched_str)

        # 2. 解析金額
        amount_match = re.search(r'(?:₹|Rs\.|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text, re.IGNORECASE)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            amount_val = int(round(float(amount_str)))

        # 3. 解析路線
        text_lower = text.lower()
        locs = []
        for word in KNOWN_LOCATIONS:
            if word in text_lower:
                if word in ["gurugram", "gurgaon"]:
                    locs.append("Gurgaon")
                elif word in ["bangalore", "bengaluru"]:
                    locs.append("Bengaluru")
                else:
                    locs.append(word.capitalize())

        unique_locs = []
        for loc in locs:
            if loc not in unique_locs:
                unique_locs.append(loc)

        if len(unique_locs) >= 2:
            desc_val = f"{unique_locs[0]} to {unique_locs[1]}"
        elif len(unique_locs) == 1:
            desc_val = f"{unique_locs[0]} to {unique_locs[0]}"

        return date_val, amount_val, desc_val
    except Exception as e:
        print(f"      ❌ 解析 PDF {file_path.name} 失敗: {e}")
        return None, None, "Gurgaon to Gurgaon"

def process_trans_pdfs(trans_dir: Path) -> Tuple[int, int]:
    """解析 Transportation 中的 PDF 並自動更名為標準格式"""
    pdf_files = list(trans_dir.glob("*.pdf"))
    success = 0
    tagged = 0

    for file_path in pdf_files:
        file_name = file_path.name
        if STANDARD_PATTERN.match(file_name):
            continue

        clean_file_name = file_name
        is_manual_tagged = False
        if file_name.startswith("[需要手動確認]_"):
            clean_file_name = file_name[len("[需要手動確認]_"):]
            is_manual_tagged = True

        try:
            date_val, amount_val, desc_val = parse_single_trans_pdf(file_path)

            if date_val and amount_val:
                new_name = f"{date_val}-{desc_val}-{amount_val}.pdf"
                new_path = trans_dir / new_name
                if new_path.exists() and new_path != file_path:
                    base = new_path.stem
                    new_name = f"{base}_dup_{int(datetime.now().timestamp())}.pdf"
                    new_path = trans_dir / new_name
                os.rename(str(file_path), str(new_path))
                print(f"      ✅ 自動辨識並更名: {file_name} ➔ {new_name}")
                success += 1
            else:
                if not is_manual_tagged:
                    new_name = f"[需要手動確認]_{file_name}"
                    os.rename(str(file_path), str(trans_dir / new_name))
                    print(f"      ⚠️ 無法完全解析文字，已標記: {file_name} ➔ {new_name}")
                tagged += 1
        except Exception as e:
            print(f"      ❌ 解析 PDF {file_name} 失敗: {e}")
            if not is_manual_tagged:
                new_name = f"[需要手動確認]_{file_name}"
                try:
                    os.rename(str(file_path), str(trans_dir / new_name))
                except Exception:
                    pass
            tagged += 1

    return success, tagged

def patch_single_voucher(file_input: str, month_name: str, category: str = "trans", workspace_root: Optional[Path] = None) -> bool:
    """
    微創補件管線 (Incremental Patching Pipeline)
    =============================================================================
    職責：針對漏上傳的單張單據，直接辨識、標準歸位、生成預覽圖，並精準微創插入
    Reimbursement.html 的 defaultData 與本地 Vouchers.json，徹底避免推倒整份 HTML！
    """
    root = workspace_root or Path(__file__).resolve().parent.parent.parent.parent.parent
    candidate_dirs = [
        root / "Business Trip" / month_name,
        root / month_name,
        Path(month_name)
    ]
    month_dir = None
    for cd in candidate_dirs:
        if cd.exists() and cd.is_dir():
            month_dir = cd
            break

    if not month_dir:
        print(f"❌ 錯誤: 找不到月份資料夾: {month_name}")
        return False

    src_path = Path(file_input)
    if not src_path.is_absolute():
        if (month_dir / file_input).exists():
            src_path = month_dir / file_input
        elif (root / file_input).exists():
            src_path = root / file_input
        else:
            src_path = (Path.cwd() / file_input).resolve()

    if not src_path.exists():
        print(f"❌ 錯誤: 找不到待補單據檔案: {src_path}")
        return False

    print("=" * 70)
    print(f"⚡ [微創補登管線] 處理漏上傳單據: {src_path.name}")
    print(f"📍 目標月份: {month_name} ({month_dir})")
    print("=" * 70)

    # 1. 決定目標子目錄
    cat_dir_name = "Transportation" if category == "trans" else ("Public Relations" if category == "pr" else "Other Expenses")
    dest_dir = month_dir / cat_dir_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    previews_dir = month_dir / ".previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    # 2. 自動辨識與更名
    final_filename = src_path.name
    if category == "trans" and src_path.suffix.lower() == ".pdf":
        date_val, amount_val, desc_val = parse_single_trans_pdf(src_path)
        if date_val and amount_val:
            final_filename = f"{date_val}-{desc_val}-{amount_val}.pdf"
            print(f"   ✅ 自動辨識文字成功: 日期={date_val} | 路線={desc_val} | 金額=₹{amount_val}")
        else:
            final_filename = f"[需要手動確認]_{src_path.name}"
            print(f"   ⚠️ 無法完整提取文字特徵，暫時標記: {final_filename}")

    dest_file = dest_dir / final_filename
    if dest_file.exists() and dest_file.resolve() != src_path.resolve():
        base = dest_file.stem
        final_filename = f"{base}_dup_{int(datetime.now().timestamp())}{dest_file.suffix}"
        dest_file = dest_dir / final_filename

    if src_path.resolve() != dest_file.resolve():
        shutil.move(str(src_path), str(dest_file))
        print(f"   🚚 檔案已安全歸位至: {dest_file.relative_to(month_dir)}")

    # 3. 渲染多頁垂直拼接預覽圖
    preview_filename = f"{dest_file.stem}.png"
    preview_path = previews_dir / preview_filename
    try:
        doc = fitz.open(str(dest_file))
        num_pages = len(doc)
        if num_pages == 1:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            pix.save(str(preview_path))
        elif num_pages > 1:
            page_images = []
            for i in range(num_pages):
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                page_images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
            total_w = max(im.width for im in page_images)
            total_h = sum(im.height for im in page_images)
            combined_img = Image.new("RGB", (total_w, total_h), (255, 255, 255))
            curr_y = 0
            for im in page_images:
                combined_img.paste(im, (0, curr_y))
                curr_y += im.height
            combined_img.save(str(preview_path), "PNG")
        doc.close()
        print(f"   🖼️ 高清預覽圖生成完畢: .previews/{preview_filename}")
    except Exception as e:
        print(f"   ⚠️ 預覽圖渲染跳過: {e}")

    # 4. 解析該項目的結構化記錄
    match = STANDARD_PATTERN.match(final_filename)
    if match:
        day, month_str, year, desc, amount, ext = match.groups()
        months = {'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
                  'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
        m_num = months.get(month_str.capitalize(), '01')
        date_str = f"20{year}/{m_num}/{day}"
    else:
        date_str = datetime.now().strftime("%Y/%m/%d")
        desc = dest_file.stem
        amount = "0"

    rel_p = str(dest_file.relative_to(month_dir)).replace("\\", "/")
    new_item = {
        "date": date_str,
        "desc": desc,
        "amount": str(amount),
        "customer": "",
        "summary": desc,
        "path": str(dest_file.resolve()),
        "rel_path": rel_p,
        "preview_img": f".previews/{preview_filename}" if preview_path.exists() else rel_p
    }

    # 5. 微創插入 Reimbursement.html 中的 defaultData
    html_file = month_dir / "Reimbursement.html"
    if html_file.exists():
        html_text = html_file.read_text(encoding="utf-8")
        target_key = f"{category}Items:"
        idx = html_text.find(target_key)
        if idx != -1:
            arr_start = html_text.find("[", idx)
            arr_end = html_text.find("]", arr_start)
            existing_arr_str = html_text[arr_start:arr_end+1]
            try:
                existing_list = json.loads(existing_arr_str)
                # 檢查是否已存在
                if not any(it.get("path") == new_item["path"] for it in existing_list):
                    existing_list.append(new_item)
                    new_arr_str = json.dumps(existing_list, ensure_ascii=False)
                    html_text = html_text[:arr_start] + new_arr_str + html_text[arr_end+1:]
                    html_file.write_text(html_text, encoding="utf-8")
                    print(f"   🎯 微創更新: 已將新單據無損追加至 Reimbursement.html ({len(existing_list)} 筆)")
                else:
                    print(f"   ℹ️ 單據已存在於 HTML 中，無須重複追加。")
            except Exception as e:
                print(f"   ⚠️ 微創替換 HTML 失敗: {e}")

    # 6. 同步更新/產生本地 Vouchers.json
    json_path = month_dir / f"{month_name.replace(' ', '_')}_Vouchers.json"
    data = {"prItems": [], "transItems": [], "otherItems": []}
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    target_list_key = f"{category}Items"
    if not any(it.get("path") == new_item["path"] for it in data.get(target_list_key, [])):
        data.setdefault(target_list_key, []).append(new_item)
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
        print(f"   💾 同步更新本地總帳: {json_path.name}")

    print("=" * 70)
    print(f"🎉 補登完畢！瀏覽器刷新 Reimbursement.html 即可看見新單據！")
    return True

def run_pipeline(month_name: str, workspace_root: Optional[Path] = None) -> None:
    """執行全流程管線處理"""
    root = workspace_root or Path(__file__).resolve().parent.parent.parent.parent.parent
    
    # 優先在 Business Trip 下尋找月份目錄，兼顧直接路徑與舊根目錄
    candidate_dirs = [
        root / "Business Trip" / month_name,
        root / month_name,
        Path(month_name)
    ]
    month_dir = None
    for cd in candidate_dirs:
        if cd.exists() and cd.is_dir():
            month_dir = cd
            break

    if not month_dir:
        print(f"❌ 錯誤: 目標月份資料夾不存在: {root / 'Business Trip' / month_name}")
        print(f"   (已檢查候選路徑: {[str(p) for p in candidate_dirs]})")
        sys.exit(1)

    print("=" * 70)
    print(f"🚀 出差報銷單據全自動化處理管線 (Pipeline Master)")
    print(f"📍 目標目錄: {month_dir.name} ({month_dir})")
    print("=" * 70)

    # 階段 1: 智能分流
    print("\n📂 [階段 1/4] 執行單據智能分類與目錄分流 (Auto-Triaging)...")
    trans_c, pr_c, other_c = triage_files(month_dir)
    print(f"   分流結果: 交通 (Transportation): {trans_c} | 公關 (Public Relations): {pr_c} | 其他 (Other): {other_c}")

    pr_dir = month_dir / "Public Relations"
    trans_dir = month_dir / "Transportation"
    other_dir = month_dir / "Other Expenses"
    backup_dir = month_dir / ".backup_images"

    # 階段 2: 圖片轉檔與備份
    print("\n🖼️ [階段 2/4] 掃描圖片並轉換為 PDF (Pillow Engine)...")
    total_converted = 0
    for d in [pr_dir, trans_dir, other_dir]:
        if d.exists():
            c = convert_images_in_dir(d, backup_dir)
            total_converted += c
    print(f"   共轉換並備份 {total_converted} 張圖片為標準 PDF。")

    # 階段 3: 電子單據自動更名
    print("\n📝 [階段 3/4] 交通單據文字萃取與標準化命名 (PyMuPDF Engine)...")
    success_renamed, tagged_count = process_trans_pdfs(trans_dir)

    # 標記 PR 與 Other 的非標準單據
    for d in [pr_dir, other_dir]:
        if d.exists():
            for f in d.glob("*.pdf"):
                if not STANDARD_PATTERN.match(f.name) and not f.name.startswith("[需要手動確認]_"):
                    new_name = f"[需要手動確認]_{f.name}"
                    os.rename(str(f), str(d / new_name))
                    tagged_count += 1

    print(f"   辨識結果: 自動標準更名: {success_renamed} 筆 | 待 AI 視覺確認: {tagged_count} 筆")

    # 階段 4: 總表儀表板產出
    print("\n📊 [階段 4/4] 掃描單據並生成總表儀表板 (Reimbursement.html)...")
    internal_dashboard = Path(__file__).resolve().parent / "generate_dashboard.py"
    root_dashboard = root / "generate_dashboard.py"
    dashboard_script = internal_dashboard if internal_dashboard.exists() else root_dashboard

    if dashboard_script.exists():
        import subprocess
        res = subprocess.run([sys.executable, str(dashboard_script), month_name], cwd=str(root), capture_output=True, text=True, encoding="utf-8")
        print(f"   {res.stdout.strip()}")
    else:
        print("⚠️ 未找到 generate_dashboard.py，跳過總表生成。")

    print("\n" + "=" * 70)
    print(f"🎉 '{month_name}' 單據管線處理完畢！")
    print(f"💡 AI 代理人後續行動指引：")
    print(f"   若仍有帶 [需要手動確認]_ 的發票圖片，請調用多模態視覺工具開眼識別並修改標準檔名！")
    print("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Voucher Management Pipeline Master")
    subparsers = parser.add_subparsers(dest="command", help="子指令模式")

    # 1. 補單子指令: patch
    patch_parser = subparsers.add_parser("patch", help="微創補登單張漏單據")
    patch_parser.add_argument("file", help="待補單據檔案路徑")
    patch_parser.add_argument("--month", required=True, help="目標月份資料夾名稱 (例如: 'Sep 2026')")
    patch_parser.add_argument("--type", choices=["trans", "pr", "other"], default="trans", help="單據類別 (預設: trans)")
    patch_parser.add_argument("--path", help="專案根目錄")

    # 2. 全量管線子指令: run
    run_p = subparsers.add_parser("run", help="全量執行月份管線")
    run_p.add_argument("month", help="目標月份資料夾名稱 (例如: 'Sep 2026')")
    run_p.add_argument("--path", help="專案根目錄")

    # 相容傳統位置參數調用 (若第一個參數不是 patch/run，預設為月份名執行全量管線)
    if len(sys.argv) > 1 and sys.argv[1] not in ["patch", "run", "-h", "--help"]:
        month_arg = sys.argv[1]
        path_arg = None
        if len(sys.argv) > 2 and sys.argv[2] == "--path" and len(sys.argv) > 3:
            path_arg = sys.argv[3]
        root = Path(path_arg).resolve() if path_arg else None
        run_pipeline(month_arg, root)
        return

    args = parser.parse_args()
    root = Path(args.path).resolve() if getattr(args, "path", None) else None

    if args.command == "patch":
        patch_single_voucher(args.file, args.month, args.type, root)
    elif args.command == "run":
        run_pipeline(args.month, root)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
