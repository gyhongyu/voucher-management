"""
ignore_filter.py - 高性能目錄修剪與忽略規則過濾器 (Path Pruning & Noise Filter)
專門防止代碼掃描器意外進入大型數據目錄 (如 9,000+ eml、日誌、虛擬環境) 引發假死與記憶體爆炸。
"""

import os
import sys

# 預設死穴黑名單目錄 (一律小寫比對)
DEFAULT_IGNORED_DIRS = {
    # 專案重度數據/快取陷阱
    "data",
    "logs",
    "log",
    "notes_data",
    "cache",
    ".cache",
    "tmp",
    "temp",
    # 虛擬環境與套件
    "venv",
    ".venv",
    "env",
    ".env",
    "virtualenv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # 版本控制與 IDE
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    ".agents",
    # 編譯產物與發布包
    "dist",
    "build",
    "target",
    "out",
    "bin",
    "obj",
    "dist_skills",
    # 治理與外掛工具雜項目錄
    "dev_dmc",
    ".system_generated",
    "artifacts",
}

# 預設忽略檔案副檔名 (二進位、數據、日誌、媒體)
DEFAULT_IGNORED_EXTS = {
    ".eml", ".msg", ".db", ".sqlite", ".sqlite3",
    ".log", ".pyc", ".pyo", ".pyd",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".map", ".min.js", ".min.css",
    ".csv", ".tsv", ".parquet",
}

def load_gitignore_patterns(root_dir: str) -> set:
    """載入專案根目錄的 .gitignore 規則 (簡易前綴/名稱過濾)"""
    patterns = set()
    gitignore_path = os.path.join(root_dir, ".gitignore")
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # 去除首尾斜線與空白
                        clean_pat = line.strip("/").strip("\\").lower()
                        if clean_pat:
                            patterns.add(clean_pat)
        except Exception:
            pass
    return patterns

def is_dir_ignored(dir_name: str, full_path: str, gitignore_patterns: set) -> bool:
    """判斷目錄是否應被原地修剪 (Pruned)"""
    name_lower = dir_name.lower()
    if name_lower in DEFAULT_IGNORED_DIRS:
        return True
    if name_lower.startswith("."):
        return True
    if name_lower in gitignore_patterns:
        return True
    return False

def is_file_ignored(file_name: str, full_path: str, gitignore_patterns: set) -> bool:
    """判斷單一檔案是否應被忽略"""
    name_lower = file_name.lower()
    _, ext = os.path.splitext(name_lower)
    if ext in DEFAULT_IGNORED_EXTS:
        return True
    if name_lower.startswith("."):
        return True
    if name_lower in gitignore_patterns:
        return True
    return False

def prune_walk(root_dir: str):
    """
    自適應安全遍歷生成器。
    核心安全保證：在進入子目錄前利用 dirs[:] 原地物理刪除黑名單目錄，
    徹底杜絕 os.walk 遞迴深入到 data/ 或 9,000+ 檔案陷阱中！
    """
    gitignore_patterns = load_gitignore_patterns(root_dir)
    
    for current_root, dirs, files in os.walk(root_dir, topdown=True):
        # 關鍵物理修剪：dirs[:] 原地切片過濾
        dirs[:] = [d for d in dirs if not is_dir_ignored(d, os.path.join(current_root, d), gitignore_patterns)]
        
        # 過濾檔案
        safe_files = [f for f in files if not is_file_ignored(f, os.path.join(current_root, f), gitignore_patterns)]
        
        yield current_root, dirs, safe_files
