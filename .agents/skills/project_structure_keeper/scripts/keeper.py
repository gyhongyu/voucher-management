#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_structure_keeper - 專案現場拓撲守護、同步與目錄衛生審計腳本
"""

import os
import sys
import re
import subprocess
from pathlib import Path

IGNORE_DIRS = {
    ".git", ".svn", ".hg", ".agents", ".agent_profiles",
    "node_modules", "bower_components", "__pycache__", ".pytest_cache",
    ".venv", "venv", "env", ".env", ".tox",
    ".idea", ".vscode", ".vs",
    "dist", "build", "out", ".next", ".nuxt", ".output",
    "coverage", ".cache", "logs", "tmp", "temp"
}

def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".agents").is_dir():
            return parent
    if len(current.parents) >= 5:
        return current.parents[4]
    return current.parent.parent.parent.parent.parent

def extract_registered_modules(topology_file: Path) -> set:
    registered = set()
    if not topology_file.is_file():
        return registered
    try:
        content = topology_file.read_text(encoding="utf-8")
        matches = re.findall(r"\|\s*`([^`]+)`\s*\|", content)
        for m in matches:
            cleaned = m.strip().rstrip("/").lstrip("./")
            if cleaned and not cleaned.startswith("("):
                registered.add(cleaned)
    except Exception:
        pass
    return registered

def audit_topology():
    proj_root = get_project_root()
    top_file = proj_root / "docs" / "TOPOLOGY.md"
    print("=" * 60)
    print(f"🛡️ 專案現場拓撲與衛生審計: {proj_root.name}")
    print(f"📍 專案根目錄: {proj_root}")
    print("=" * 60)
    
    if not top_file.is_file():
        print("⚠️ docs/TOPOLOGY.md 不存在，請由全域母技能重新生成。")
        print("   建議指令: py skills/project_topology_architect/scripts/topology_engine.py scaffold")
        return

    registered_modules = extract_registered_modules(top_file)
    try:
        cur_dirs = [d.name for d in proj_root.iterdir() if d.is_dir() and d.name not in IGNORE_DIRS]
    except Exception as e:
        print(f"⚠️ 無法讀取目錄: {e}")
        return

    unregistered_dirs = [d for d in cur_dirs if d not in registered_modules and f"{d}/" not in registered_modules]
    
    # 嗅探 git status --porcelain
    orphan_root_files = []
    known_root_files = {
        "readme.md", "handoff.md", "agents.md", "gemini.md", "claude.md", ".gitignore",
        "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
        "pyproject.toml", "requirements.txt", "setup.py", "poetry.lock",
        "cargo.toml", "cargo.lock", "go.mod", "go.sum", "dockerfile",
        "docker-compose.yml", "license", "license.md", "makefile", "index.html",
        "切換為生產模式.bat", "切換為開發模式.bat", "generate_dashboard.py", "rename_vouchers.py", "github_repositories.md"
    }

    if (proj_root / ".git").exists():
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(proj_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=False
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    item = line.strip()
                    if not item:
                        continue
                    status = item[:2].strip()
                    rel_file = item[3:].strip().strip('"')
                    p = Path(rel_file)
                    target_path = proj_root / p
                    if len(p.parts) == 1 and (status == "??" or status == "A"):
                        if target_path.is_dir():
                            dname = p.name
                            if dname not in IGNORE_DIRS and dname not in registered_modules and dname not in unregistered_dirs:
                                unregistered_dirs.append(dname)
                        elif p.name.lower() not in known_root_files and not p.name.startswith("."):
                            orphan_root_files.append(p.name)
                    elif len(p.parts) > 1 and status == "??" and p.parts[0] not in IGNORE_DIRS and p.parts[0] not in registered_modules:
                        unregistered_dirs.append(p.parts[0])
        except Exception:
            pass

    has_issues = False
    if unregistered_dirs:
        has_issues = True
        print("⚠️ 【新增模組未登記】發現頂層模組目錄尚未在 docs/TOPOLOGY.md 登錄職責:")
        for d in sorted(set(unregistered_dirs)):
            print(f"   - 📁 `{d}/`")
        print("   👉 處置建議: 執行 `py .agents/skills/project_structure_keeper/scripts/keeper.py sync` 同步拓撲地圖。")

    if orphan_root_files:
        has_issues = True
        print(f"⚠️ 【根目錄孤兒檔案】發現未納管或疑似臨時散落檔案 ({len(orphan_root_files)} 個):")
        for f in sorted(orphan_root_files)[:8]:
            print(f"   - 📄 `{f}`")
        if len(orphan_root_files) > 8:
            print(f"   - ... 其餘 {len(orphan_root_files) - 8} 個檔案")
        print("   👉 處置建議: 交接或 Git 提交前，請確認：A. 歸位至 `docs/`、`specs/` 或 `.scratch/`；B. 刪除廢棄臨時檔；C. 加入 `.gitignore`。")

    if not has_issues:
        print("✅ 【專案拓撲純淨】頂層模組全數在冊，無根目錄孤兒雜檔，結構非常健康！")
        print("   可放心進行工作交接或代碼提交。")
    print("=" * 60)

def sync_topology():
    proj_root = get_project_root()
    top_file = proj_root / "docs" / "TOPOLOGY.md"
    print("=" * 60)
    print(f"🔄 專案拓撲守護同步: {proj_root.name}")
    print(f"📍 專案根目錄: {proj_root}")
    print(f"📄 拓撲活地圖: {top_file}")
    print("=" * 60)
    
    if not top_file.is_file():
        print("⚠️ docs/TOPOLOGY.md 不存在，請由全域母技能重新生成。")
        print("   建議指令: py skills/project_topology_architect/scripts/topology_engine.py scaffold")
        return
        
    try:
        cur_dirs = sorted([d.name for d in proj_root.iterdir() if d.is_dir() and d.name not in IGNORE_DIRS])
        print(f"📂 現存核心目錄 ({len(cur_dirs)}): {', '.join(cur_dirs)}")
        print("✅ 拓撲活地圖就緒，可作為架構真理查閱。")
    except Exception as e:
        print(f"⚠️ 檢查目錄時發生異常: {e}")

if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "audit"
    if action == "sync":
        sync_topology()
    elif action == "audit":
        audit_topology()
    else:
        print(f"未知指令: {action}。支援指令: audit (預設), sync")
