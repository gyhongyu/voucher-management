# -*- coding: utf-8 -*-
"""
google_drive_downloader - Voucher Management 專案專屬 Google Drive 單向增量下載引擎
=============================================================================
雙軌通訊機制 (Dual-Transport Pipeline):
  1. Primary: 官方 Google Drive REST API (OAuth2 Bearer Token from ~/.clasprc.json)
  2. Fallback: Google Apps Script Web App (無伺服器 Webhook)

核心鐵律:
  - 嚴禁覆蓋: 若本地已存在目標月份資料夾，嚴格拒絕下載並安全跳過！
  - 忽略雜檔: 自動忽略「說明」等非月份資料夾。
=============================================================================
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Business Trip 雲端資料夾 ID (單一真理源 SSOT)
BUSINESS_TRIP_FOLDER_ID = "1cHZL5SFj0O9V25gxLXsyuhJklF0x_F_S"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyM_CT4pdF8cynXG9-3REK_swM2U4DHVoCZv0K7eTLTcywdcOjhe8GnRioz3RRPCpt-VA/exec"

CLASPRC_PATH = Path.home() / ".clasprc.json"
TOKEN_URL = "https://oauth2.googleapis.com/token"

def get_drive_access_token() -> Optional[str]:
    """從 ~/.clasprc.json 讀取並自癒換票取得最新的 Google OAuth2 Token"""
    if not CLASPRC_PATH.exists():
        return None
    try:
        with open(CLASPRC_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        token_data = data.get("tokens", {}).get("default", {})
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        client_id = token_data.get("client_id")
        client_secret = token_data.get("client_secret")

        # 檢測當前 access_token 是否有效
        if access_token:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        return access_token
            except Exception:
                pass

        # 若過期則換票
        if refresh_token and client_id and client_secret:
            body = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }).encode("utf-8")
            refresh_req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(refresh_req, timeout=10) as resp:
                refreshed = json.loads(resp.read().decode("utf-8"))
                new_token = refreshed.get("access_token")
                if new_token:
                    token_data["access_token"] = new_token
                    with open(CLASPRC_PATH, "w", encoding="utf-8") as f_out:
                        json.dump(data, f_out, indent=2)
                    return new_token
    except Exception as e:
        print(f"⚠️ OAuth 憑證讀取失敗: {e}")
    return None

def list_cloud_months(token: str) -> List[Dict[str, str]]:
    """列出 Business Trip 下的所有子資料夾"""
    url = f"https://www.googleapis.com/drive/v3/files?q=%27{BUSINESS_TRIP_FOLDER_ID}%27+in+parents+and+mimeType=%27application/vnd.google-apps.folder%27+and+trashed=false"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        items = res.get("files", [])
        # 過濾說明文件夾
        valid_folders = [f for f in items if f.get("name") != "說明"]
        return valid_folders

def list_folder_files(folder_id: str, token: str) -> List[Dict[str, Any]]:
    """列出某月份資料夾內的所有單據檔案"""
    url = f"https://www.googleapis.com/drive/v3/files?q=%27{folder_id}%27+in+parents+and+trashed=false&fields=files(id,name,mimeType,size)"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("files", [])

def download_file(file_id: str, dest_path: Path, token: str) -> bool:
    """下載單一檔案二進位資料並寫入本地 (GAS Web App 與 Drive REST API 雙軌備援)"""
    # 軌道 1: GAS Web App (Base64)
    try:
        url = f"{WEB_APP_URL}?action=get_file_b64&file_id={file_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success" and "file_b64" in data:
                raw_bytes = base64.b64decode(data["file_b64"])
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(raw_bytes)
                return True
            else:
                print(f"      [GAS警報] {dest_path.name}: {data.get('message')}")
    except Exception as gas_err:
        print(f"      [GAS異常] {dest_path.name}: {gas_err}")

    # 軌道 2: 官方 Google Drive v3 REST API (alt=media)
    try:
        api_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        req = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_bytes = resp.read()
            if len(raw_bytes) > 0:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(raw_bytes)
                return True
    except Exception as drive_err:
        print(f"      [REST異常] {dest_path.name}: {drive_err}")

    return False

def auto_archive_processed_trips(business_trip_root: Path, archive_root: Path) -> int:
    """
    自動歸檔機制 (Auto-Archive Guard):
    若在 Business Trip 目錄下發現已經存在 Reimbursement.html 總表 (代表前次已處理完畢)，
    自動將整個月份目錄搬遷至 archive/ 資料夾中，等待使用者日後清理，保持工作區極簡衛生。
    """
    archived_count = 0
    if not business_trip_root.exists():
        return 0

    archive_root.mkdir(parents=True, exist_ok=True)

    for item in business_trip_root.iterdir():
        if item.is_dir() and item.name != "archive":
            # 檢查是否含有儀表板或數據標誌
            has_dashboard = (item / "Reimbursement.html").exists()
            has_json = (item / "Reimbursement_data.json").exists()
            if has_dashboard or has_json:
                dest = archive_root / item.name
                if dest.exists():
                    import time
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    dest = archive_root / f"{item.name}_{timestamp}"
                
                print(f"📦 [自動歸檔] 發現已完工歷史單據 '{item.name}' ➔ 自動移至 '{dest.relative_to(business_trip_root.parent)}'")
                import shutil
                shutil.move(str(item), str(dest))
                archived_count += 1

    return archived_count

def sync_vouchers(project_root: Path, force_target: Optional[str] = None) -> None:
    """
    執行單向增量下載
    """
    business_trip_root = project_root / "Business Trip"
    archive_root = project_root / "archive"

    print("=" * 70)
    print("📂 Google Drive 出差單據單向增量下載器 (Voucher Management Edition)")
    print(f"📍 本地單據專屬目錄: {business_trip_root}")
    print(f"☁️ 雲端目標目錄 ID: {BUSINESS_TRIP_FOLDER_ID}")
    print("=" * 70)

    # 1. 執行歷史已處理單據自動歸檔
    archived = auto_archive_processed_trips(business_trip_root, archive_root)
    if archived > 0:
        print(f"🧹 已完成 {archived} 個歷史完工月份的自動歸檔 (移入 archive/)。")

    token = get_drive_access_token()
    if not token:
        print("❌ 未能獲取有效的 Google Drive 憑證！請確認 ~/.clasprc.json 狀態。")
        sys.exit(1)

    cloud_folders = list_cloud_months(token)
    if not cloud_folders:
        print("ℹ️ 雲端 Business Trip 資料夾下未發現任何月份子目錄！")
        return

    print(f"🔍 雲端發現 {len(cloud_folders)} 個月份資料夾: {[f['name'] for f in cloud_folders]}")

    business_trip_root.mkdir(parents=True, exist_ok=True)

    for folder in cloud_folders:
        folder_name = folder["name"]
        folder_id = folder["id"]

        # 🚨 100% 忠實對齊 Google Drive 目錄真值，存放於 Business Trip/<folder_name>
        target_dir = business_trip_root / folder_name

        # 🚨 核心防覆蓋保護鐵律 (Zero-Overwrite Guard)
        # 若該目錄已存在，且已經有 Reimbursement.html，代表已處理完畢，安全跳過
        if target_dir.exists() and target_dir.is_dir():
            has_dashboard = (target_dir / "Reimbursement.html").exists()
            if has_dashboard:
                print(f"\n🛡️ [防覆蓋跳過] 目錄 '{target_dir.relative_to(project_root)}' 已包含完工儀表板，安全跳過。")
                continue

        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📥 [開始下載] 雲端目錄: '{folder_name}' ➔ 本地路徑: '{target_dir.relative_to(project_root)}/'")

        files = list_folder_files(folder_id, token)
        print(f"   📄 共計 {len(files)} 個單據檔案待下載 (啟用 5 線程高並發加速)...")

        pending_files = []
        for f in files:
            fname = f["name"]
            fid = f["id"]
            dest_file = target_dir / fname
            if dest_file.exists():
                print(f"      ⏭️ 檔案已存在: {fname}")
            else:
                pending_files.append((fid, fname, dest_file))

        success_count = 0
        failed_count = 0

        def _worker_download(item: Tuple[str, str, Path]):
            fid, fname, dest = item
            ok = download_file(fid, dest, token)
            return fname, dest, ok

        # 5 線程並發池，瞬間拉取完畢
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {executor.submit(_worker_download, item): item for item in pending_files}
            for future in as_completed(future_to_file):
                fname, dest, ok = future.result()
                if ok:
                    size_kb = dest.stat().st_size / 1024
                    print(f"      ✅ 下載成功: {fname} ({size_kb:.1f} KB)")
                    success_count += 1
                else:
                    print(f"      ❌ 下載失敗: {fname}")
                    failed_count += 1

        print(f"\n✨ '{folder_name}' 下載完畢！成功拉取 {success_count} 個新檔案至 '{target_dir.name}/' (失敗: {failed_count})")
        print(f"👉 下一步指引：請執行 `py rename_vouchers.py \"{target_dir.name}\"` 啟動圖片轉檔與自動命名管線！")

    print("\n" + "=" * 70)
    print("🎉 Google Drive 單向增量下載巡檢完成！")
    print("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Google Drive Voucher Downloader")
    parser.add_argument("--month", help="指定只下載特定月份")
    # scripts -> google_drive_downloader -> skills -> .agents -> Voucher management (4 parents)
    default_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    parser.add_argument("--path", default=str(default_root), help="專案根目錄")
    args = parser.parse_args()

    project_root = Path(args.path).resolve()
    sync_vouchers(project_root, args.month)

if __name__ == "__main__":
    main()
