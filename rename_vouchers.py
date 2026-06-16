import os
import re
import sys
import glob
import shutil
import fitz  # PyMuPDF
from datetime import datetime
from PIL import Image

# Ensure output encoding is UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def parse_date(date_str):
    date_str = date_str.strip().replace(',', '')
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    formats = [
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
    ]
    # Clean up time if any (e.g. 07:09 AM or 6:58 PM)
    date_str = re.sub(r'\s+\d{1,2}:\d{2}\s*[AP]M', '', date_str, flags=re.IGNORECASE).strip()
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%b-%y")
        except ValueError:
            pass
    return None

def convert_images_to_pdf(target_dir, backup_dir):
    """
    Find all .jpg, .jpeg, .png files in the target directory,
    convert them to PDF format, rename to [需要手動確認]_<original_name>.pdf,
    and move the original image to backup_dir.
    """
    image_extensions = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
    images = []
    for ext in image_extensions:
        images.extend(glob.glob(os.path.join(target_dir, ext)))
    images = list(set(images))
        
    if not images:
        return

    print(f"\n--- 正在轉換 {os.path.basename(target_dir)} 中的圖片為 PDF ---")
    for img_path in images:
        img_name = os.path.basename(img_path)
        base_name, _ = os.path.splitext(img_name)
        
        # Determine the target PDF name
        pdf_name = f"[需要手動確認]_{base_name}.pdf"
        pdf_path = os.path.join(target_dir, pdf_name)
        
        try:
            img = Image.open(img_path)
            # Convert to RGB mode if necessary (PDF does not support RGBA or palette modes)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(pdf_path, "PDF")
            img.close()
            
            # Check if PDF exists and is not empty before moving original image
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                backup_path = os.path.join(backup_dir, img_name)
                # Handle filename collisions in backup folder
                if os.path.exists(backup_path):
                    timestamp = datetime.now().strftime("%H%M%S")
                    backup_path = os.path.join(backup_dir, f"{base_name}_{timestamp}{_}")
                shutil.move(img_path, backup_path)
                print(f"成功轉換並備份: {img_name} -> {pdf_name}")
        except Exception as e:
            print(f"轉換圖片 {img_name} 失敗: {e}")

def process_pdf_vouchers(trans_dir):
    """
    Parse text from PDFs in Transportation folder, extract date, amount, and locations,
    and rename the files to standard format.
    """
    pdf_files = glob.glob(os.path.join(trans_dir, "*.pdf"))
    if not pdf_files:
        return

    print(f"\n--- 正在解析 {os.path.basename(trans_dir)} 中的交通 PDF 單據 ---")
    
    # Precompiled regex for standard filename format: e.g. 08-Apr-26-Bengaluru-1690.pdf
    standard_pattern = re.compile(r'^\d{2}-[A-Za-z]{3}-\d{2}-.+-(\d+)\.(pdf|jpg)$', re.IGNORECASE)

    for file_path in pdf_files:
        file_name = os.path.basename(file_path)
        
        # Skip files that are already named correctly
        if standard_pattern.match(file_name):
            continue

        clean_file_name = file_name
        is_manual_tagged = False
        if file_name.startswith("[需要手動確認]_"):
            clean_file_name = file_name[len("[需要手動確認]_"):]
            is_manual_tagged = True

        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            
            date_val = None
            amount_val = None
            desc_val = "Gurgaon to Gurgaon"
            
            # 1. Parse Date: look for typical formats
            date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{2,9}\s+\d{4})|([A-Za-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?(?:,)?\s*\d{4})', text)
            if date_match:
                matched_str = date_match.group(1) if date_match.group(1) else date_match.group(2)
                date_val = parse_date(matched_str)

            # 2. Parse Amount: Look for currency symbols (₹, Rs., INR) and figures
            amount_match = re.search(r'(?:₹|Rs\.|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                amount_val = int(float(amount_str))

            # 3. Parse Route/Locations
            text_lower = text.lower()
            locs = []
            known_locations = ["gurugram", "gurgaon", "delhi", "noida", "bengaluru", "hyderabad", "manesar", "indore"]
            for word in known_locations:
                if word in text_lower:
                    locs.append("Gurgaon" if word in ["gurugram", "gurgaon"] else word.capitalize())
            
            unique_locs = []
            for loc in locs:
                if loc not in unique_locs:
                    unique_locs.append(loc)
                    
            if len(unique_locs) >= 2:
                desc_val = f"{unique_locs[0]} to {unique_locs[1]}"
            elif len(unique_locs) == 1:
                desc_val = f"{unique_locs[0]} to {unique_locs[0]}"

            # Determine renaming target
            if date_val and amount_val:
                new_name = f"{date_val}-{desc_val}-{amount_val}.pdf"
                new_path = os.path.join(trans_dir, new_name)
                
                # Check for collision
                if os.path.exists(new_path) and new_path != file_path:
                    # Append a unique suffix if name already exists
                    base, ext = os.path.splitext(new_name)
                    new_name = f"{base}_dup_{int(datetime.now().timestamp())}{ext}"
                    new_path = os.path.join(trans_dir, new_name)
                    
                os.rename(file_path, new_path)
                print(f"解析成功並重命名: {file_name} -> {new_name}")
            else:
                # If we cannot parse text and it's not tagged, mark it
                if not is_manual_tagged:
                    new_name = f"[需要手動確認]_{file_name}"
                    os.rename(file_path, os.path.join(trans_dir, new_name))
                    print(f"無法解析文字，已標記: {file_name} -> {new_name}")
                else:
                    print(f"仍需手動確認的檔案: {file_name} (解析結果 - 日期: {date_val}, 金額: {amount_val})")

        except Exception as e:
            print(f"處理 PDF {file_name} 發生錯誤: {e}")
            if not is_manual_tagged:
                new_name = f"[需要手動確認]_{file_name}"
                try:
                    os.rename(file_path, os.path.join(trans_dir, new_name))
                    print(f"處理出錯，已標記為手動確認: {file_name} -> {new_name}")
                except:
                    pass

def main():
    if len(sys.argv) < 2:
        print("錯誤: 未指定目標月份資料夾名稱！")
        print("用法: python rename_vouchers.py <月份資料夾名稱>")
        print("範例: python rename_vouchers.py \"May to Jun\"")
        sys.exit(1)

    month_name = sys.argv[1]
    workspace_root = r"E:\Projects\Voucher management"
    month_dir = os.path.join(workspace_root, month_name)

    if not os.path.exists(month_dir) or not os.path.isdir(month_dir):
        print(f"錯誤: 找不到目標資料夾 '{month_dir}'")
        sys.exit(1)

    pr_dir = os.path.join(month_dir, "Public Relations")
    trans_dir = os.path.join(month_dir, "Transportation")
    backup_dir = os.path.join(month_dir, ".backup_images")

    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    # 1. Convert any image files (.jpg, .png) to PDF in both directories
    for directory in [pr_dir, trans_dir]:
        if os.path.exists(directory):
            convert_images_to_pdf(directory, backup_dir)

    # 2. For Public Relations directory, tag any non-standard PDFs with [需要手動確認]_
    # (PR doesn't have an auto-naming rule based on content, so they must be manually named)
    if os.path.exists(pr_dir):
        standard_pattern = re.compile(r'^\d{2}-[A-Za-z]{3}-\d{2}-.+-(\d+)\.(pdf|jpg)$', re.IGNORECASE)
        for f in os.listdir(pr_dir):
            f_path = os.path.join(pr_dir, f)
            if os.path.isfile(f_path) and f.endswith('.pdf'):
                if not standard_pattern.match(f) and not f.startswith("[需要手動確認]_"):
                    new_name = f"[需要手動確認]_{f}"
                    os.rename(f_path, os.path.join(pr_dir, new_name))
                    print(f"已將非標準 PR 單據標記為手動確認: {f} -> {new_name}")

    # 3. For Transportation directory, auto-rename PDFs
    if os.path.exists(trans_dir):
        process_pdf_vouchers(trans_dir)

    print("\n單據重命名與圖片轉換程序已執行完畢。")

if __name__ == "__main__":
    main()
