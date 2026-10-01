/**
 * =========================================================================
 * 🌐 Universal Google Drive JSON Gateway (Voucher Management Edition)
 * =========================================================================
 * 包含完整 Google Drive 讀取、下載與遍歷 API。
 * 支援透過 action 參數呼叫：
 *   - list_folder : 遍歷資料夾 (回傳 subfolders 與 files)
 *   - get_file    : 獲取檔案中繼資料
 *   - get_file_b64: 讀取檔案 Base64
 *   - get_quota   : 查詢容量配額
 */

const DEFAULT_ROOT_FOLDER = "Business Trip";

function doGet(e) {
  try {
    const p = (e && e.parameter) ? e.parameter : {};
    const action = p.action || "get_quota";

    if (action === "get_quota") {
      return createJsonResponse(getStorageQuota());
    }
    if (action === "get_file") {
      return createJsonResponse(getFileMetadata(p));
    }
    if (action === "get_file_b64") {
      return createJsonResponse(getFileBase64(p));
    }
    if (action === "get_folder") {
      return createJsonResponse(getFolderMetadata(p));
    }
    if (action === "list_folder") {
      return createJsonResponse(listFolderContents(p));
    }
    if (action === "search") {
      return createJsonResponse(searchDriveFiles(p));
    }

    return createJsonResponse({ status: "error", message: "Unknown GET action: " + action });
  } catch (err) {
    return createJsonResponse({ status: "error", message: err.toString() });
  }
}

function doPost(e) {
  try {
    let payload = {};
    if (e && e.postData && e.postData.contents) {
      payload = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      payload = e.parameter;
    }

    const action = payload.action || "list_folder";

    if (action === "list_folder") {
      return createJsonResponse(listFolderContents(payload));
    }
    if (action === "get_file_b64") {
      return createJsonResponse(getFileBase64(payload));
    }
    if (action === "get_file") {
      return createJsonResponse(getFileMetadata(payload));
    }
    if (action === "get_quota") {
      return createJsonResponse(getStorageQuota());
    }

    return createJsonResponse({ status: "error", message: "Unknown POST action: " + action });
  } catch (err) {
    return createJsonResponse({ status: "error", message: err.toString() });
  }
}

function listFolderContents(p) {
  let folder;
  if (p.folder_id) {
    folder = DriveApp.getFolderById(p.folder_id);
  } else {
    folder = DriveApp.getRootFolder();
  }

  const files = [];
  const fileIter = folder.getFiles();
  while (fileIter.hasNext()) {
    const f = fileIter.next();
    files.push({
      type: "file",
      id: f.getId(),
      name: f.getName(),
      size: f.getSize(),
      mime_type: f.getMimeType(),
      view_url: f.getUrl(),
      download_url: "https://drive.google.com/uc?export=download&id=" + f.getId(),
      updated_at: Utilities.formatDate(f.getLastUpdated(), "Asia/Taipei", "yyyy-MM-dd HH:mm:ss")
    });
  }

  const subfolders = [];
  const folderIter = folder.getFolders();
  while (folderIter.hasNext()) {
    const sub = folderIter.next();
    subfolders.push({
      type: "folder",
      id: sub.getId(),
      name: sub.getName(),
      url: sub.getUrl()
    });
  }

  return {
    status: "success",
    folder_id: folder.getId(),
    folder_name: folder.getName(),
    folder_url: folder.getUrl(),
    total_files: files.length,
    total_subfolders: subfolders.length,
    files: files,
    subfolders: subfolders
  };
}

function getFileMetadata(p) {
  if (!p.file_id) return { status: "error", message: "Missing file_id" };
  const file = DriveApp.getFileById(p.file_id);
  return {
    status: "success",
    file_id: file.getId(),
    name: file.getName(),
    size: file.getSize(),
    mime_type: file.getMimeType(),
    view_url: file.getUrl(),
    download_url: "https://drive.google.com/uc?export=download&id=" + file.getId()
  };
}

function getFileBase64(p) {
  if (!p.file_id) return { status: "error", message: "Missing file_id" };
  const file = DriveApp.getFileById(p.file_id);
  const b64 = Utilities.base64Encode(file.getBlob().getBytes());
  return {
    status: "success",
    file_id: file.getId(),
    name: file.getName(),
    mime_type: file.getMimeType(),
    size: file.getSize(),
    file_b64: b64
  };
}

function getStorageQuota() {
  const used = DriveApp.getStorageUsed();
  const limit = DriveApp.getStorageLimit();
  return {
    status: "success",
    storage_used_bytes: used,
    storage_used_mb: (used / (1024 * 1024)).toFixed(2),
    storage_limit_bytes: limit,
    storage_limit_mb: limit > 0 ? (limit / (1024 * 1024)).toFixed(2) : "Unlimited"
  };
}

function createJsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function authorizeUniversalDrive() {
  const testFolder = DriveApp.createFolder("_auth_test_temp_");
  testFolder.setTrashed(true);
  Logger.log("✅ Universal Google Drive Gateway 權限授權成功！");
}
