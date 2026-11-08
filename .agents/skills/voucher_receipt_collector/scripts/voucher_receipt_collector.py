#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
voucher_receipt_collector.py - Voucher Receipt Collector 核心控制 CLI
======================================================================
職責：從 Notes / Gmail 檢索各類交通/網頁收據（如 Uber），調用底座 export-pdf 轉檔為標準向量 PDF，
並按日期與格式儲存至指定月份的 Transportation 資料夾。
"""

import os
import sys
import io
import json
import re
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Windows 控制台編碼防禦
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NOTES_CLIENT = Path(r"C:\Users\9892\.gemini\config\skills\notes_master\scripts\client.py")
GMAIL_CLIENT = Path(r"C:\Users\9892\.gemini\config\skills\gas_gmail_bridge\scripts\gmail_manager.py")


def _run_cmd(cmd_list):
    res = subprocess.run(cmd_list, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout, res.stderr


def cmd_status(args):
    """檢查各底座連線與依賴環境"""
    print("=" * 60)
    print("🔍 [voucher_receipt_collector] 收集器依賴環境體檢")
    print("=" * 60)
    
    # 1. Notes Master 探測
    if NOTES_CLIENT.exists():
        code, out, _ = _run_cmd(["py", str(NOTES_CLIENT), "daemon", "status"])
        notes_ok = "🟢 就緒" if code == 0 else "🟡 守護進程未啟動"
    else:
        notes_ok = "🔴 找不到腳本"
    print(f" • NotesMaster 網關: {notes_ok}")

    # 2. Gmail Bridge 探測
    if GMAIL_CLIENT.exists():
        code, out, _ = _run_cmd(["py", str(GMAIL_CLIENT), "ping", "--json"])
        gmail_ok = "🟢 連線正常" if code == 0 and "success" in out else "🔴 連線失敗"
    else:
        gmail_ok = "🔴 找不到腳本"
    print(f" • GAS Gmail 網關 : {gmail_ok}")
    print("=" * 60)
    return 0


def parse_month_filter(month_str):
    """靈活解析月份篩選字串為標準 (year, month) 元組"""
    if not month_str:
        return None
    cleaned = month_str.strip().replace("-", " ")
    for fmt in ["%Y %m", "%b %y", "%B %Y", "%b %Y", "%Y %b", "%Y %B"]:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return (dt.year, dt.month)
        except ValueError:
            continue
    # 嘗試正規化匹配，例如 Oct 2026 或 2026-10
    m1 = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(\d{2,4})', cleaned, re.I)
    if m1:
        mon_name, yr = m1.group(1), m1.group(2)
        if len(yr) == 2:
            yr = "20" + yr
        try:
            dt = datetime.strptime(f"{mon_name} {yr}", "%b %Y")
            return (dt.year, dt.month)
        except Exception:
            pass
    return None


def is_date_in_window(dt: datetime, target_ym: tuple, span_days: int = 7) -> bool:
    """判斷日期是否在目標月份內，或在月底接續之跨月窗口 (如次月前 span_days 天)"""
    if not target_ym:
        return True
    target_year, target_month = target_ym
    # 1. 屬於目標月份
    if dt.year == target_year and dt.month == target_month:
        return True
    # 2. 判斷是否為次月前 span_days 天之連貫行程
    next_year = target_year if target_month < 12 else target_year + 1
    next_month = target_month + 1 if target_month < 12 else 1
    if dt.year == next_year and dt.month == next_month and dt.day <= span_days:
        return True
    return False


def collect_uber_notes(month_str, output_dir, dry_run=False, folder="Uber", span_days=7):
    """從 NotesMaster 收集 Uber 收據 (嚴格信匣隔離，杜絕跨匣翻垃圾桶)"""
    print(f"🔍 正在從 NotesMaster [{folder}] 匣檢索 Uber 收據...")
    code, out, _ = _run_cmd(["py", str(NOTES_CLIENT), "mail", "list", "--folder", folder, "--json", "--limit", "100"])
    if code != 0 or not out.strip().startswith("["):
        print(f"❌ Notes 郵件檢索失敗或 [{folder}] 信匣為空！嚴禁跨信匣全域搜尋以防翻出垃圾桶廢件。")
        return []

    try:
        raw_entries = json.loads(out)
        entries = []
        for item in raw_entries:
            sent_time = item.get("sent_time", "")
            dt_str = sent_time[:10] if sent_time else ""
            note_id = item.get("current_note_id", "")
            subject = item.get("subject", "")
            if dt_str and note_id:
                entries.append({"date": dt_str, "note_id": note_id, "subject": subject})
    except Exception as e:
        print(f"❌ 解析 Notes JSON 失敗: {e}")
        return []

    target_ym = parse_month_filter(month_str)
    collected = []
    for item in entries:
        dt_str = item.get("date", "")
        note_id = item.get("note_id")
        if not dt_str or not note_id:
            continue

        dt = datetime.strptime(dt_str, "%Y-%m-%d")
        if not is_date_in_window(dt, target_ym, span_days=span_days):
            continue

        target_name = f"{dt.strftime('%d-%b-%y')}-Uber-Notes-{note_id}.pdf"
        target_file = output_dir / target_name
        if target_file.exists():
            print(f"   ⏩ [跳過] 檔案已存在: {target_name}")
            collected.append(target_file)
            continue

        print(f"   📥 正在導出 [{dt_str}] NoteID:{note_id} ➔ {target_name}")
        if not dry_run:
            c, o, e = _run_cmd(["py", str(NOTES_CLIENT), "mail", "export-pdf", note_id, "-o", str(target_file)])
            if c == 0:
                collected.append(target_file)
            else:
                print(f"   ❌ 導出失敗: {e}")
        else:
            collected.append(target_file)

    return collected


def collect_uber_gmail(month_str, output_dir, dry_run=False):
    """從 Gmail Bridge 收集 Uber 收據"""
    print(f"🔍 正在從 Gmail 網關檢索 Uber 收據...")
    code, out, _ = _run_cmd(["py", str(GMAIL_CLIENT), "search", "Uber", "--limit", "20", "--json"])
    if code != 0:
        print("❌ Gmail 郵件檢索失敗！")
        return []

    try:
        data = json.loads(out)
    except Exception:
        print("❌ 解析 Gmail JSON 失敗！")
        return []

    threads = data.get("data", [])
    collected = []

    for t in threads:
        subj = t.get("subject", "")
        if "uber" not in subj.lower():
            continue

        dt_str = t.get("last_message_date", "")[:10]  # YYYY-MM-DD
        thread_id = t.get("thread_id")

        if not dt_str or not thread_id:
            continue

        dt = datetime.strptime(dt_str, "%Y-%m-%d")
        month_label_1 = dt.strftime("%b-%y")  # Jun-26
        month_label_2 = dt.strftime("%Y-%m")  # 2026-06

        if month_str and month_str.lower() not in [month_label_1.lower(), month_label_2.lower()]:
            continue

        target_name = f"{dt.strftime('%d-%b-%y')}-Uber-Gmail-{thread_id}.pdf"
        target_file = output_dir / target_name
        if target_file.exists():
            print(f"   ⏩ [跳過] 檔案已存在: {target_name}")
            continue

        print(f"   📥 正在導出 [{dt_str}] Gmail Thread:{thread_id} ➔ {target_name}")
        if not dry_run:
            c, o, e = _run_cmd(["py", str(GMAIL_CLIENT), "export-pdf", thread_id, "-o", str(target_file)])
            if c == 0:
                collected.append(target_file)
            else:
                print(f"   ❌ 導出失敗: {e}")
        else:
            collected.append(target_file)

    return collected


def cmd_collect(args):
    """執行收據收集"""
    source = args.source.lower()
    month = args.month
    span_days = args.span_days
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(f"🚗 [voucher_receipt_collector] 開始收集收據 (來源: {source}, 月份: {month or '全量'}, 跨月寬容: {span_days}天)")
    print(f"🎯 存放目錄 : {out_dir}")
    print("=" * 65)

    all_files = []
    if source == "notes":
        all_files.extend(collect_uber_notes(month, out_dir, args.dry_run, span_days=span_days))
    elif source == "gmail":
        all_files.extend(collect_uber_gmail(month, out_dir, args.dry_run))
    elif source == "all":
        all_files.extend(collect_uber_notes(month, out_dir, args.dry_run, span_days=span_days))
        all_files.extend(collect_uber_gmail(month, out_dir, args.dry_run))

    print("-" * 65)
    print(f"🎉 收集完成！本次共獲取 {len(all_files)} 份新收據 PDF。")
    print("=" * 65)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Voucher專案專用收據與發票收集轉檔大師")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # collect
    p_col = subparsers.add_parser("collect", help="檢索並收集外部收據轉檔為 PDF")
    p_col.add_argument("--source", choices=["notes", "gmail", "all"], default="notes", help="指定來源 (預設: notes，杜絕跨渠道無端搜索)")
    p_col.add_argument("--month", "-m", help="指定月份篩選 (如 Sep-26 或 2026-09)")
    p_col.add_argument("--span-days", type=int, default=7, help="跨月底連貫行程寬容天數 (預設: 7 天)")
    p_col.add_argument("-o", "--output", default="Transportation", help="存檔輸出資料夾 (預設: Transportation)")
    p_col.add_argument("--dry-run", action="store_true", help="僅列出欲收集項目，不實際下載")

    # status
    p_stat = subparsers.add_parser("status", help="檢查與測試底座連線狀態")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    if args.command == "collect":
        return cmd_collect(args)
    elif args.command == "status":
        return cmd_status(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
