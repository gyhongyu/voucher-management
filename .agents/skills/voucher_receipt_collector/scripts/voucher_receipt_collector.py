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


def collect_uber_notes(month_str, output_dir, dry_run=False):
    """從 NotesMaster 收集 Uber 收據"""
    print(f"🔍 正在從 NotesMaster 檢索 Uber 收據...")
    code, out, _ = _run_cmd(["py", str(NOTES_CLIENT), "mail", "search", "Uber"])
    if code != 0:
        print("❌ Notes 郵件檢索失敗！")
        return []

    # 解析 UNID 與 NoteID
    # 格式: 【#1 】 📎 [2026-09-25 17:05] Your Friday afternoon trip with Uber ("Uber Receipts")
    #       UNID: FF587EC4B057E8E8E1EF92A01BEC3B65 | NoteID: 1094A
    entries = []
    current_entry = {}
    for line in out.splitlines():
        line = line.strip()
        m_date = re.search(r'\[(\d{4}-\d{2}-\d{2})\s+[^\]]+\]\s+(.+)', line)
        if m_date:
            current_entry["date"] = m_date.group(1)
            current_entry["subject"] = m_date.group(2)
        m_id = re.search(r'NoteID:\s*([0-9A-Fa-f]+)', line)
        if m_id:
            current_entry["note_id"] = m_id.group(1)
            entries.append(current_entry)
            current_entry = {}

    collected = []
    for item in entries:
        dt_str = item.get("date", "")
        note_id = item.get("note_id")
        if not dt_str or not note_id:
            continue

        # 比對月份 (如 2026-09 vs Sep-26 或 2026-09)
        dt = datetime.strptime(dt_str, "%Y-%m-%d")
        month_label_1 = dt.strftime("%b-%y")  # Sep-26
        month_label_2 = dt.strftime("%Y-%m")  # 2026-09

        if month_str and month_str.lower() not in [month_label_1.lower(), month_label_2.lower()]:
            continue

        target_name = f"{dt.strftime('%d-%b-%y')}-Uber-Notes-{note_id}.pdf"
        target_file = output_dir / target_name
        if target_file.exists():
            print(f"   ⏩ [跳過] 檔案已存在: {target_name}")
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
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print(f"🚗 [voucher_receipt_collector] 開始收集收據 (來源: {source}, 月份: {month or '全量'})")
    print(f"🎯 存放目錄 : {out_dir}")
    print("=" * 65)

    all_files = []
    if source in ["notes", "all"]:
        all_files.extend(collect_uber_notes(month, out_dir, args.dry_run))

    if source in ["gmail", "all"]:
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
    p_col.add_argument("--source", choices=["notes", "gmail", "all"], default="all", help="指定來源 (預設: all)")
    p_col.add_argument("--month", "-m", help="指定月份篩選 (如 Sep-26 或 2026-09)")
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
