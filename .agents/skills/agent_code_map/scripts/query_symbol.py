"""
query_symbol.py - 軌道 B：微觀符號定位、高精語意跳轉與調用鏈穿透引擎 (Dual-Core Micro Symbol & Caller Tracing)
支援：
1. 雙軌自適應：Jedi 語意推導 (可選高精加速器) ＋ Python 原生 C-AST (零依賴鋼鐵保底)。
2. 秒查定義位置 (def)、呼叫層次 (callers)、函式文檔/簽名 (doc)、前端 DOM 錨點 (dom)。
3. 自動嗅探專案虛擬環境 (.venv / venv)，杜絕型別解析失明。
4. 輸出標準點擊鏈接 (file:///...) 與下游代理人引導提示，徹底杜絕暴力讀檔。
"""

import os
import sys
import ast
import re
import argparse
from pathlib import Path

# Windows console encoding defense
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from ignore_filter import prune_walk
except ImportError:
    from .ignore_filter import prune_walk

# 嘗試載入 Jedi (高精語意引擎)
try:
    import jedi
    HAS_JEDI = True
except ImportError:
    HAS_JEDI = False

PYTHON_EXTS = {".py"}
POLYGLOT_EXTS = {".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".cs"}
WEB_EXTS = {".html", ".htm", ".vue", ".svelte", ".js", ".ts", ".jsx", ".tsx"}


def detect_virtualenv(root_dir: str) -> str:
    """自動偵測目標專案根目錄下的虛擬環境 (.venv / venv / env)"""
    root = Path(root_dir)
    candidates = [root / ".venv", root / "venv", root / "env", root / ".env"]
    for c in candidates:
        if c.is_dir() and (c / "Scripts" / "python.exe").is_file():
            return str(c / "Scripts" / "python.exe")
        elif c.is_dir() and (c / "bin" / "python").is_file():
            return str(c / "bin" / "python")
    return ""


def get_jedi_project(root_dir: str):
    """建立帶虛擬環境感知的 Jedi Project"""
    if not HAS_JEDI:
        return None
    try:
        venv_py = detect_virtualenv(root_dir)
        if venv_py:
            env = jedi.create_environment(venv_py, safe=False)
            return jedi.Project(root_dir, environment=env)
        return jedi.Project(root_dir)
    except Exception:
        try:
            return jedi.Project(root_dir)
        except Exception:
            return None


class CallSiteVisitor(ast.NodeVisitor):
    def __init__(self, target_symbol: str, file_lines: list, rel_path: str):
        self.target_symbol = target_symbol
        self.file_lines = file_lines
        self.rel_path = rel_path
        self.scope_stack = []
        self.matches = []

    def visit_ClassDef(self, node):
        self.scope_stack.append(f"class {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        self.scope_stack.append(f"def {node.name}()")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.scope_stack.append(f"async def {node.name}()")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node):
        is_match = False
        if isinstance(node.func, ast.Name) and node.func.id == self.target_symbol:
            is_match = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == self.target_symbol:
            is_match = True

        if is_match:
            lineno = getattr(node, "lineno", 0)
            snippet = self.file_lines[lineno - 1].strip() if 0 < lineno <= len(self.file_lines) else ""
            scope_str = " -> ".join(self.scope_stack) if self.scope_stack else "<module level>"
            self.matches.append({
                "rel_path": self.rel_path,
                "lineno": lineno,
                "scope": scope_str,
                "snippet": snippet
            })

        self.generic_visit(node)


class DefVisitor(ast.NodeVisitor):
    def __init__(self, target_symbol: str, file_lines: list, rel_path: str):
        self.target_symbol = target_symbol
        self.file_lines = file_lines
        self.rel_path = rel_path
        self.scope_stack = []
        self.matches = []

    def visit_ClassDef(self, node):
        if node.name == self.target_symbol:
            snippet = self.file_lines[node.lineno - 1].strip() if 0 < node.lineno <= len(self.file_lines) else ""
            self.matches.append({
                "type": "class",
                "name": node.name,
                "rel_path": self.rel_path,
                "lineno": node.lineno,
                "scope": " -> ".join(self.scope_stack) if self.scope_stack else "<module level>",
                "snippet": snippet,
                "doc": ast.get_docstring(node) or ""
            })
        self.scope_stack.append(f"class {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        if node.name == self.target_symbol:
            snippet = self.file_lines[node.lineno - 1].strip() if 0 < node.lineno <= len(self.file_lines) else ""
            self.matches.append({
                "type": "def",
                "name": node.name,
                "rel_path": self.rel_path,
                "lineno": node.lineno,
                "scope": " -> ".join(self.scope_stack) if self.scope_stack else "<module level>",
                "snippet": snippet,
                "doc": ast.get_docstring(node) or ""
            })
        self.scope_stack.append(f"def {node.name}()")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)


def query_callers_python(full_path: str, rel_path: str, target_symbol: str) -> list:
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tree = ast.parse("".join(lines), filename=full_path)
        visitor = CallSiteVisitor(target_symbol, lines, rel_path)
        visitor.visit(tree)
        return visitor.matches
    except Exception:
        return []


def query_defs_python(full_path: str, rel_path: str, target_symbol: str) -> list:
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tree = ast.parse("".join(lines), filename=full_path)
        visitor = DefVisitor(target_symbol, lines, rel_path)
        visitor.visit(tree)
        return visitor.matches
    except Exception:
        return []


def query_polyglot_regex(full_path: str, rel_path: str, target_symbol: str, action: str) -> list:
    """非 Python 檔案的正則平穩降級處理"""
    matches = []
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return matches

    pattern_caller = re.compile(rf'(?:\.|\b){re.escape(target_symbol)}\s*\(')
    pattern_def = re.compile(rf'^\s*(?:export\s+)?(?:async\s+)?(?:function|def|func|class|interface|struct)\s+{re.escape(target_symbol)}\b')

    for idx, line in enumerate(lines, 1):
        line_strip = line.strip()
        if action in ("callers", "both") and pattern_caller.search(line_strip):
            if not pattern_def.search(line_strip):
                matches.append({
                    "rel_path": rel_path,
                    "lineno": idx,
                    "scope": "<polyglot context>",
                    "snippet": line_strip
                })
        elif action in ("def", "both") and pattern_def.search(line_strip):
            matches.append({
                "type": "symbol",
                "name": target_symbol,
                "rel_path": rel_path,
                "lineno": idx,
                "scope": "<polyglot context>",
                "snippet": line_strip,
                "doc": ""
            })
    return matches


def query_dom_anchors(root_dir: str, query: str) -> list:
    """查詢 Web 前端 HTML / JS 中的 DOM 元素錨點 (ID, Class, 選擇器綁定)"""
    results = []
    id_pattern = re.compile(rf'id=["\']{re.escape(query)}["\']', re.IGNORECASE)
    class_pattern = re.compile(rf'class=["\'][^"\']*\b{re.escape(query)}\b[^"\']*["\']', re.IGNORECASE)
    js_elem_pattern = re.compile(rf'(?:getElementById|querySelector(?:All)?)\s*\(\s*["\'][^"\']*{re.escape(query)}[^"\']*["\']\s*\)')

    for current_root, _, files in prune_walk(root_dir):
        for f in files:
            _, ext = os.path.splitext(f.lower())
            if ext in WEB_EXTS:
                full_path = os.path.join(current_root, f)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for idx, line in enumerate(fp, 1):
                            line_strip = line.strip()
                            tag = None
                            if id_pattern.search(line_strip):
                                tag = "HTML ID 錨點"
                            elif class_pattern.search(line_strip):
                                tag = "HTML Class 樣式"
                            elif js_elem_pattern.search(line_strip):
                                tag = "JS DOM 選擇器"

                            if tag:
                                results.append({
                                    "tag": tag,
                                    "rel_path": rel_path,
                                    "lineno": idx,
                                    "snippet": line_strip
                                })
                except Exception:
                    continue
    return results


def run_jedi_search(project, symbol: str, root_dir: str):
    """使用 Jedi 進行全專案高精符號檢索"""
    if not project:
        return []
    results = []
    try:
        names = project.search(symbol, all_scopes=True)
        for name in names:
            if name.name == symbol:
                m_path = name.module_path
                if m_path:
                    try:
                        rel = os.path.relpath(str(m_path), root_dir).replace("\\", "/")
                    except ValueError:
                        rel = str(m_path).replace("\\", "/")
                    # 排除外部 site-packages
                    if "site-packages" in rel or "dist-packages" in rel:
                        continue
                    results.append({
                        "type": name.type,
                        "name": name.name,
                        "rel_path": rel,
                        "lineno": name.line or 1,
                        "scope": name.full_name or "<module level>",
                        "snippet": f"{name.type} {name.name}",
                        "doc": name.docstring(raw=True) or ""
                    })
    except Exception:
        pass
    return results


def run_query(action: str, symbol: str, root_dir: str):
    root_dir = os.path.abspath(root_dir)
    jedi_proj = get_jedi_project(root_dir) if HAS_JEDI else None

    # DOM 錨點查詢模式
    if action == "dom":
        print("=" * 80)
        print(f"🌐 [DOM Search] 正在定位前端 Web 錨點 '{symbol}' (ID / Class / JS Selector)：")
        print("=" * 80)
        dom_matches = query_dom_anchors(root_dir, symbol)
        if not dom_matches:
            print(f"  ℹ️ 未在 HTML/JS 檔案中找到與 '{symbol}' 匹配的 DOM 標籤或選擇器。")
        else:
            for item in dom_matches:
                print(f"📍 {item['rel_path']}:{item['lineno']} [{item['tag']}]")
                print(f"   └─ Snippet: {item['snippet']}\n")
        print_footer_hints(root_dir)
        return

    # Docstring / 簽名專用模式
    if action == "doc":
        print("=" * 80)
        print(f"📖 [Doc & Signature] 正在提取符號 '{symbol}' 的宣告簽名與 Docstring：")
        print("=" * 80)
        doc_found = False
        if jedi_proj:
            jedi_defs = run_jedi_search(jedi_proj, symbol, root_dir)
            for d in jedi_defs:
                if d["doc"]:
                    doc_found = True
                    print(f"📌 {d['rel_path']}:{d['lineno']} ({d['type']} {d['name']})")
                    print(f"   Scope: {d['scope']}")
                    print("   --- [Docstring] ---")
                    for dline in d["doc"].strip().splitlines()[:15]:
                        print(f"   {dline}")
                    print()
        if not doc_found:
            # AST Fallback
            for current_root, _, files in prune_walk(root_dir):
                for f in files:
                    if f.endswith(".py"):
                        full_path = os.path.join(current_root, f)
                        rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                        defs = query_defs_python(full_path, rel_path, symbol)
                        for d in defs:
                            if d.get("doc"):
                                doc_found = True
                                print(f"📌 {rel_path}:{d['lineno']} ({d['type']} {d['name']})")
                                print(f"   Scope: {d['scope']}")
                                print("   --- [Docstring] ---")
                                for dline in d["doc"].strip().splitlines()[:15]:
                                    print(f"   {dline}")
                                print()
        if not doc_found:
            print(f"  ℹ️ 未找到符號 '{symbol}' 的 Docstring 文檔或註解。")
        print_footer_hints(root_dir)
        return

    # 定義 (def) 與 呼叫者 (callers) 查詢
    defs_results = []
    callers_results = []

    # 1. 查找定義 (Def)
    if action in ("def", "both"):
        # 優先嘗試 Jedi 高精推導
        if jedi_proj:
            defs_results = run_jedi_search(jedi_proj, symbol, root_dir)

        # 若 Jedi 無結果或未安裝，走 AST + Polyglot 保底
        if not defs_results:
            for current_root, _, files in prune_walk(root_dir):
                for f in files:
                    full_path = os.path.join(current_root, f)
                    rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                    _, ext = os.path.splitext(f.lower())
                    if ext in PYTHON_EXTS:
                        defs_results.extend(query_defs_python(full_path, rel_path, symbol))
                    elif ext in POLYGLOT_EXTS:
                        defs_results.extend(query_polyglot_regex(full_path, rel_path, symbol, "def"))

    # 2. 查找呼叫者 (Callers)
    if action in ("callers", "both"):
        for current_root, _, files in prune_walk(root_dir):
            for f in files:
                full_path = os.path.join(current_root, f)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                _, ext = os.path.splitext(f.lower())
                if ext in PYTHON_EXTS:
                    callers_results.extend(query_callers_python(full_path, rel_path, symbol))
                elif ext in POLYGLOT_EXTS:
                    callers_results.extend(query_polyglot_regex(full_path, rel_path, symbol, "callers"))

    # 印出結果
    print("=" * 80)
    if action in ("def", "both"):
        mode_tag = "Jedi 高精" if (HAS_JEDI and defs_results and jedi_proj) else "AST 原生"
        print(f"🔍 [Definition Search - {mode_tag}] 定位符號 '{symbol}' 的定義宣告 (共 {len(defs_results)} 處)：")
        print("=" * 80)
        if not defs_results:
            print(f"  ℹ️ 未在專案中找到符號 '{symbol}' 的定義位置。")
        else:
            for item in defs_results:
                print(f"📌 {item['rel_path']}:{item['lineno']} ({item.get('type', 'symbol')})")
                print(f"   ├─ Scope  : {item['scope']}")
                print(f"   └─ Snippet: {item['snippet']}\n")

    if action in ("callers", "both"):
        print("=" * 80)
        print(f"🎯 [Callers Search] 定位呼叫符號 '{symbol}' 的所有位置 (共 {len(callers_results)} 處)：")
        print("=" * 80)
        if not callers_results:
            print(f"  ℹ️ 未在專案中找到任何呼叫 '{symbol}' 的代碼位置。")
        else:
            for item in callers_results:
                print(f"📍 {item['rel_path']}:{item['lineno']}")
                print(f"   ├─ Scope  : {item['scope']}")
                print(f"   └─ Snippet: {item['snippet']}\n")

    print_footer_hints(root_dir)


def print_footer_hints(root_dir: str):
    print("=" * 80)
    print("🎯 [AI 代理人行動指引]:")
    print(" • 閱讀實作：請精準針對目標行號區間調用 view_file (例如 view_file file:///...#L40-L70)，嚴禁整檔暴力切片！")
    print(" • 調用鏈反查：若需追蹤呼叫來源，請執行：py query_symbol.py callers <symbol>")
    print(" • 函式簽名：若僅需確認參數簽名，請執行：py query_symbol.py doc <symbol>")
    if not HAS_JEDI:
        print(" • [💡 提示]: 目前運行於標準 AST 模式。運行 '環境依賴自檢.bat' 可自動安裝 jedi 解鎖深度型別推導。")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="專案符號微觀定位、高精語意跳轉與呼叫者穿透查詢器 (Dual-Core Symbol & Caller Tracing)",
        usage="%(prog)s [action] <symbol> [target_dir] 或 %(prog)s <symbol>"
    )
    parser.add_argument("positional_args", nargs="*", help="查詢參數: [<def|callers|doc|dom>] <symbol> [target_dir]")
    parser.add_argument("--def", dest="is_def", action="store_true", help="定位符號定義宣告")
    parser.add_argument("--callers", dest="is_callers", action="store_true", help="查找所有呼叫點")
    parser.add_argument("--doc", dest="is_doc", action="store_true", help="提取函式文檔與簽名")
    parser.add_argument("--dom", dest="is_dom", action="store_true", help="查找前端 DOM ID/Class 錨點")
    args = parser.parse_args()

    pos = args.positional_args
    action = "both"
    if args.is_def:
        action = "def"
    elif args.is_callers:
        action = "callers"
    elif args.is_doc:
        action = "doc"
    elif args.is_dom:
        action = "dom"

    symbol = None
    target_dir = "."

    if not pos and action == "both":
        parser.print_help()
        sys.exit(1)

    if pos:
        first = pos[0].lower()
        if first in ("callers", "def", "doc", "dom"):
            action = first
            if len(pos) < 2:
                print(f"❌ 錯誤: 請指定要查詢的名稱！範例: py {os.path.basename(sys.argv[0])} {action} <symbol>", file=sys.stderr)
                sys.exit(1)
            symbol = pos[1]
            if len(pos) >= 3:
                target_dir = pos[2]
        else:
            # 智慧雙查模式 (Unified Search): 同時查定義與呼叫點
            symbol = pos[0]
            if len(pos) >= 2:
                target_dir = pos[1]

    if not symbol:
        print("❌ 錯誤: 請指定要查詢的符號名稱！", file=sys.stderr)
        sys.exit(1)

    run_query(action, symbol, target_dir)


if __name__ == "__main__":
    main()
