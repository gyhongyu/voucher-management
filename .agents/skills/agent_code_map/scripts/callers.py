"""
query_symbol.py - 軌道 B：微觀符號定位與調用鏈穿透引擎 (Micro Symbol & Caller Hierarchy)
支援秒查指定符號的「原始定義位置 (def)」與「所有被呼叫點 (callers)」。
輸出攜帶父層 Scope 與調用語句片段，徹底杜絕同名函式張冠李戴與全局 grep 盲目摸象。
"""

import os
import sys
import ast
import re
import argparse

try:
    from ignore_filter import prune_walk
except ImportError:
    from .ignore_filter import prune_walk

PYTHON_EXTS = {".py"}

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
        call_expr = ""

        # 比對直接函式呼叫 func_name(...)
        if isinstance(node.func, ast.Name) and node.func.id == self.target_symbol:
            is_match = True
            call_expr = self.target_symbol
        # 比對物件方法呼叫 obj.method_name(...)
        elif isinstance(node.func, ast.Attribute) and node.func.attr == self.target_symbol:
            is_match = True
            call_expr = f".{self.target_symbol}"

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
                "snippet": snippet
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
                "snippet": snippet
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
        if action == "callers" and pattern_caller.search(line_strip):
            # 排除自我定義行
            if not pattern_def.search(line_strip):
                matches.append({
                    "rel_path": rel_path,
                    "lineno": idx,
                    "scope": "<polyglot context>",
                    "snippet": line_strip
                })
        elif action == "def" and pattern_def.search(line_strip):
            matches.append({
                "type": "symbol",
                "name": target_symbol,
                "rel_path": rel_path,
                "lineno": idx,
                "scope": "<polyglot context>",
                "snippet": line_strip
            })
    return matches

def run_query(action: str, symbol: str, root_dir: str):
    all_results = []

    for current_root, _, files in prune_walk(root_dir):
        for f in files:
            full_path = os.path.join(current_root, f)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            _, ext = os.path.splitext(f.lower())

            if ext in PYTHON_EXTS:
                if action == "callers":
                    res = query_callers_python(full_path, rel_path, symbol)
                else:
                    res = query_defs_python(full_path, rel_path, symbol)
                all_results.extend(res)
            elif ext in {".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp"}:
                res = query_polyglot_regex(full_path, rel_path, symbol, action)
                all_results.extend(res)

    print("=" * 80)
    if action == "callers":
        print(f"🎯 [Callers Search] 正在定位呼叫符號 '{symbol}' 的所有位置 (共發現 {len(all_results)} 處呼叫點)：")
        print("=" * 80)
        if not all_results:
            print(f"  ℹ️ 未在專案中找到任何呼叫 '{symbol}' 的代碼位置。")
        else:
            for item in all_results:
                print(f"📍 {item['rel_path']}:{item['lineno']}")
                print(f"   ├─ Scope  : {item['scope']}")
                print(f"   └─ Snippet: {item['snippet']}\n")
    else:
        print(f"🔍 [Definition Search] 正在定位符號 '{symbol}' 的定義宣告 (共發現 {len(all_results)} 處定義)：")
        print("=" * 80)
        if not all_results:
            print(f"  ℹ️ 未在專案中找到符號 '{symbol}' 的定義位置。")
        else:
            for item in all_results:
                print(f"📌 {item['rel_path']}:{item['lineno']} ({item.get('type', 'symbol')})")
                print(f"   ├─ Scope  : {item['scope']}")
                print(f"   └─ Snippet: {item['snippet']}\n")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="專案符號微觀定位與呼叫者穿透查詢器 (Micro Symbol & Caller Tracing)",
        usage="%(prog)s [action] <symbol> [target_dir] 或 %(prog)s --def <symbol> [target_dir]"
    )
    parser.add_argument("positional_args", nargs="*", help="查詢參數: [<callers|def>] <symbol> [target_dir]")
    parser.add_argument("--def", dest="is_def", action="store_true", help="定位符號原始定義宣告 (等同於 def 動作)")
    args = parser.parse_args()

    pos = args.positional_args
    action = "def" if args.is_def else "callers"
    symbol = None
    target_dir = "."

    if not pos and not args.is_def:
        parser.print_help()
        sys.exit(1)

    if pos:
        first = pos[0].lower()
        if first in ("callers", "def"):
            action = first
            if len(pos) < 2:
                print(f"❌ 錯誤: 請指定要查詢的符號名稱！範例: py {os.path.basename(sys.argv[0])} {action} <symbol>", file=sys.stderr)
                sys.exit(1)
            symbol = pos[1]
            if len(pos) >= 3:
                target_dir = pos[2]
        else:
            # 智慧模式：第一個參數直接作為符號名稱
            symbol = pos[0]
            if len(pos) >= 2:
                target_dir = pos[1]

    if not symbol:
        print("❌ 錯誤: 請指定要查詢的符號名稱！", file=sys.stderr)
        sys.exit(1)

    resolved_target = os.path.abspath(target_dir)
    run_query(action, symbol, resolved_target)

if __name__ == "__main__":
    main()

