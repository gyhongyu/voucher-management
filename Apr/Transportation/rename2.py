import os
import re
import fitz
import glob
from datetime import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')
base_dir = r"E:\Projects\Voucher management\Apr\Transportation"

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
    date_str = re.sub(r'\s+\d{1,2}:\d{2}\s*[AP]M', '', date_str, flags=re.IGNORECASE).strip()
    
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
    
    if not file_name.startswith("[需要手動確認]_"):
        continue

    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        
        date_val = None
        amount_val = None
        desc_val = "Gurgaon to Gurgaon"
        
        date_match = re.search(r'(\d{1,2}\s+[A-Z][a-z]{2,8}\s+\d{4})|([A-Z][a-z]{2,8}\s+\d{1,2}(?:st|nd|rd|th)?(?:,)?\s*\d{4})', text)
        if date_match:
            matched_str = date_match.group(1) if date_match.group(1) else date_match.group(2)
            date_val = parse_date(matched_str)

        amount_match = re.search(r'₹\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            amount_val = int(float(amount_str))
            
        text_lower = text.lower()
        locs = []
        for word in ["gurugram", "gurgaon", "delhi", "noida", "bengaluru", "hyderabad", "manesar", "indore"]:
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

        if date_val and amount_val:
            new_name = f"{date_val}-{desc_val}-{amount_val}.pdf"
            new_path = os.path.join(base_dir, new_name)
            os.rename(file_path, new_path)
            print(f"Fixed: {file_name} -> {new_name}")
        else:
            print(f"Still needs manual check: {file_name} (Date: {date_val}, Amount: {amount_val})")

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
