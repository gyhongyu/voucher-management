"""
generate_map.py - 軌道 A：極速宏觀代碼地圖與拓撲抽取引擎 (Macro Code Map Generator)
零外部依賴、純 Python 原生 AST + 多語言正則降級，輸出 ≤100 行高密度骨架圖，杜絕 Token 截斷與摸象。
"""

import os
import sys
import ast
import re
import argparse
from collections import defaultdict

# 引用同一目錄下的安全過濾器
try:
    from ignore_filter import prune_walk
except ImportError:
    from .ignore_filter import prune_walk

# 支援的程式語言擴展名分類
PYTHON_EXTS = {".py"}
POLYGLOT_EXTS = {".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".cpp", ".cs"}

class ModuleInfo:
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classes = []       # [(class_name, [method_names])]
        self.functions = []     # [func_name]
        self.imports = set()    # {imported_module_name}
        self.inbound_refs = 0   # 被其他模組引用的權重次數 (Centrality)

def parse_python_ast(file_path: str, rel_path: str) -> ModuleInfo:
    """使用 Python 原生 C 語言 AST 極速抽取類別、函式與引用關係 (5~10ms)"""
    info = ModuleInfo(rel_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception:
        # 若語法有重大錯誤或特殊編碼，標記並平穩返回
        info.functions.append("<!ParseError>")
        return info

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info.functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not item.name.startswith("__") or item.name == "__init__":
                        methods.append(item.name)
            info.classes.append((node.name, methods))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info.imports.add(node.module.split(".")[0])

    return info

def parse_polyglot_regex(file_path: str, rel_path: str) -> ModuleInfo:
    """多語言通用容錯抽取 (TS/JS/Go/Rust)，保證非 Python 專案 100% 零崩潰"""
    info = ModuleInfo(rel_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return info

    for line in lines:
        line_strip = line.strip()
        # 函式抽取
        m_func = re.match(r'^(?:export\s+)?(?:async\s+)?(?:function|def|func)\s+([a-zA-Z0-9_]+)', line_strip)
        if m_func:
            info.functions.append(m_func.group(1))
            continue
        # 類別/介面抽取
        m_class = re.match(r'^(?:export\s+)?(?:class|interface|struct|type)\s+([a-zA-Z0-9_]+)', line_strip)
        if m_class:
            info.classes.append((m_class.group(1), []))
            continue
        # Import 抽取
        m_imp = re.match(r'^(?:import|from|use)\s+["\']?([a-zA-Z0-9_./-]+)', line_strip)
        if m_imp:
            mod = os.path.basename(m_imp.group(1)).split(".")[0]
            info.imports.add(mod)

    return info

def scan_repository(root_dir: str) -> dict:
    """安全掃描專案並計算中心度 (Inbound Reference Centrality)"""
    modules = {}
    
    for current_root, _, files in prune_walk(root_dir):
        for f in files:
            full_path = os.path.join(current_root, f)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            _, ext = os.path.splitext(f.lower())

            if ext in PYTHON_EXTS:
                info = parse_python_ast(full_path, rel_path)
                modules[rel_path] = info
            elif ext in POLYGLOT_EXTS:
                info = parse_polyglot_regex(full_path, rel_path)
                modules[rel_path] = info

    # 計算被引用權重 (Inbound References)
    module_basenames = {os.path.splitext(os.path.basename(p))[0]: p for p in modules.keys()}
    for rel_path, info in modules.items():
        for imp in info.imports:
            if imp in module_basenames:
                target_path = module_basenames[imp]
                if target_path != rel_path:
                    modules[target_path].inbound_refs += 1

    return modules

def format_code_map(modules: dict, root_dir: str, budget_lines: int = 100) -> str:
    """格式化輸出高密度代碼地圖，實施硬性預算控制防止截斷"""
    if not modules:
        return "⚠️ 未在專案中探測到有效的源碼檔案 (已過濾數據與二進位檔案)。"

    # 按中心度 (被引用次數) 降序排序
    sorted_modules = sorted(modules.values(), key=lambda m: (m.inbound_refs, len(m.classes) + len(m.functions)), reverse=True)

    lines = []
    lines.append(f"🗺️ [Code Map] 專案代碼拓撲總覽 (共掃描 {len(modules)} 個核心模組，已按引用中心度權重排序)")
    lines.append("=" * 80)

    line_count = 2
    rendered_count = 0

    for m in sorted_modules:
        if line_count >= budget_lines - 10 and (len(sorted_modules) - rendered_count) > 3:
            # 觸發預算封頂，啟動聚合折疊
            remaining = len(sorted_modules) - rendered_count
            lines.append(f"\n... ⚡ [預算封頂保護] 其餘 {remaining} 個低引用邊緣模組已自動折疊，以防止 Token 溢出。")
            lines.append("   (可使用 `py generate_map.py <subpath>` 針對特定子目錄深入展開)")
            break

        # 模組標題列
        ref_badge = f" [★ 被引用 {m.inbound_refs} 次]" if m.inbound_refs > 0 else ""
        lines.append(f"\n📄 {m.rel_path}{ref_badge}")
        line_count += 2

        # 輸出內部 Class
        for cname, methods in m.classes[:4]: # 單一模組最多列 4 個主要 class
            m_str = f" ➔ methods: {', '.join(methods[:5])}{'...' if len(methods) > 5 else ''}" if methods else ""
            lines.append(f"   ├─ class {cname}{m_str}")
            line_count += 1

        # 輸出內部獨立函式
        if m.functions:
            fn_preview = ", ".join(m.functions[:6])
            fn_more = f" ... (+{len(m.functions)-6} more)" if len(m.functions) > 6 else ""
            lines.append(f"   └─ defs: {fn_preview}{fn_more}")
            line_count += 1

        rendered_count += 1

    lines.append("\n" + "=" * 80)
    current_file_path = os.path.abspath(__file__)
    if ".agents" in current_file_path:
        lines.append(r"💡 提示：若要追蹤某個函式被誰呼叫，請執行：py .agents\skills\agent_code_map\scripts\callers.py <symbol>")
    else:
        lines.append(r"💡 提示：若要追蹤某個函式被誰呼叫，請執行：py skills\agent_code_map\scripts\query_symbol.py callers <symbol>")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="專案極速宏觀代碼地圖生成器")
    parser.add_argument("target_dir", nargs="?", default=".", help="目標專案路徑 (預設為當前目錄)")
    parser.add_argument("--budget", type=int, default=100, help="輸出最大行數預算 (預設 100 行，防截斷)")
    parser.add_argument("--out", nargs="?", const="docs/CODE_MAP.md", default=None,
                        help="同時將地圖寫入指定文件 (不指定路徑時預設為 docs/CODE_MAP.md)")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.target_dir)
    modules = scan_repository(target_dir)
    output = format_code_map(modules, target_dir, budget_lines=args.budget)
    print(output)

    if args.out:
        out_path = os.path.join(target_dir, args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"```\n{output}\n```\n")
        print(f"\n✅ 地圖已寫入：{out_path}")

if __name__ == "__main__":
    main()
