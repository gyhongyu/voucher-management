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

STANDARD_PATTERN = re.compile(r'^\d{2}-[A-Za-z]{3}-\d{2}-.+-(\d+)\.(pdf|jpg|jpeg|png)$', re.IGNORECASE)

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
                amount_val = int(float(amount_str))

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
    dashboard_script = root / "generate_dashboard.py"
    if dashboard_script.exists():
        import subprocess
        res = subprocess.run([sys.executable, str(dashboard_script), month_name], cwd=str(root), capture_output=True, text=True, encoding="utf-8")
        print(f"   {res.stdout.strip()}")
    else:
        print("⚠️ 未找到根目錄 generate_dashboard.py，跳過總表生成。")

    print("\n" + "=" * 70)
    print(f"🎉 '{month_name}' 單據管線處理完畢！")
    print(f"💡 AI 代理人後續行動指引：")
    print(f"   若仍有帶 [需要手動確認]_ 的發票圖片，請調用多模態視覺工具開眼識別並修改標準檔名！")
    print("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Voucher Management Pipeline Master")
    parser.add_argument("month", help="目標月份資料夾名稱 (例如: 'Sep 2026')")
    parser.add_argument("--path", help="專案根目錄 (預設為當前專案根目錄)")
    args = parser.parse_args()

    root = Path(args.path).resolve() if args.path else None
    run_pipeline(args.month, root)

if __name__ == "__main__":
    main()
