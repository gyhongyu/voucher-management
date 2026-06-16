import os
import re
import fitz
import glob
from datetime import datetime
import sys

# Fix print encoding
sys.stdout.reconfigure(encoding='utf-8')

base_dir = r"E:\Projects\Voucher management\Apr\Transportation"

def parse_date(date_str):
    date_str = date_str.strip()
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    formats = [
        "%b %d %Y, %I:%M %p",
        "%B %d, %Y",
        "%d %B %Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d-%b-%y")
        except ValueError:
            pass
    return None

files = glob.glob(os.path.join(base_dir, "*.pdf"))
for file_path in files:
    file_name = os.path.basename(file_path)
    
    if re.match(r'^\d{2}-[A-Za-z]{3}-\d{2}-', file_name) or file_name.startswith("[需要手動確認]_"):
        continue

    new_name = None
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close() # MUST CLOSE TO RENAME
        
        date_val = None
        amount_val = None
        desc_val = "Gurgaon to Gurgaon"
        
        date_match1 = re.search(r'([A-Z][a-z]{2,8}\s+\d{1,2}(?:st|nd|rd|th)?\s*\d{4}(?:,\s*\d{1,2}:\d{2}\s*[AP]M)?)', text)
        if date_match1:
            date_val = parse_date(date_match1.group(1))

        amount_match = re.search(r'₹\s*(\d+(?:\.\d+)?)', text)
        if amount_match:
            amount_val = int(float(amount_match.group(1)))
            
        text_lower = text.lower()
        locs = []
        for word in ["gurugram", "gurgaon", "delhi", "noida"]:
            if word in text_lower:
                locs.append("Gurgaon" if word in ["gurugram", "gurgaon"] else word.capitalize())
                
        if len(set(locs)) >= 2:
            desc_val = f"{list(set(locs))[0]} to {list(set(locs))[1]}"
        elif len(set(locs)) == 1:
            desc_val = f"{list(set(locs))[0]} to {list(set(locs))[0]}"

        if date_val and amount_val:
            new_name = f"{date_val}-{desc_val}-{amount_val}.pdf"
        else:
            new_name = f"[需要手動確認]_{file_name}"
            
        new_path = os.path.join(base_dir, new_name)
        os.rename(file_path, new_path)
        print(f"Renamed: {file_name} -> {new_name}")

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        try:
            if 'doc' in locals():
                doc.close()
        except:
            pass
        new_name = f"[需要手動確認]_{file_name}"
        try:
            os.rename(file_path, os.path.join(base_dir, new_name))
        except:
            pass
