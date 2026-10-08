#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""繁简混排检查：确保仓库内所有文本文件统一使用简体中文。

背景
----
本项目所有文档、图表标签与代码注释均面向中文读者。若日后编辑时误用繁体字，
会出现「同一份文档简繁并存」的情况，影响专业观感。本脚本用于自动拦截。

原理
----
使用 OpenCC 的 ``t2s``（繁体转简体）规则做逐文件转换比对：
若转换结果与原文完全一致，说明原文不含任何可转换的繁体字形。

用法
----
    python scripts/check_chinese.py           # 检查全仓库
    python scripts/check_chinese.py --strict  # 发现繁体时以非 0 退出码结束（可用于 CI）

退出码
------
    0 = 全部通过
    1 = 发现繁体字（仅 --strict 模式下返回 1）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 只检查这些后缀；二进制与数据文件不需要
TEXT_SUFFIXES = {".md", ".html", ".txt", ".py", ".csv", ".ipynb", ".json"}

# 这些目录不检查：原始数据、图片、第三方或生成产物
SKIP_DIR_PARTS = {".git", "raw", "figures", "__pycache__", ".ipynb_checkpoints", ".workbuddy"}


def _load_converter():
    """加载 OpenCC 转换器；缺少依赖时给出明确指引而非直接崩溃。"""
    try:
        from opencc import OpenCC
    except ImportError:
        print("缺少依赖 opencc-python-reimplemented，请先安装：")
        print("    pip install opencc-python-reimplemented")
        print("或直接安装本项目全部依赖：")
        print("    pip install -r requirements.txt")
        sys.exit(2)
    return OpenCC("t2s")


def iter_text_files(root: Path):
    """递归产出需要检查的文本文件路径。"""
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if SKIP_DIR_PARTS & set(p.parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield p


def check_file(path: Path, root: Path, converter) -> dict | None:
    """检查单个文件；若无繁体返回 None，否则返回统计信息字典。"""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # 非 UTF-8 或读不了，跳过
    if not text.strip():
        return None

    converted = converter.convert(text)
    if converted == text:
        return None

    # 统计每个繁体字出现的次数
    counter: dict[str, int] = {}
    for trad, simp in zip(text, converted):
        if trad != simp:
            counter[trad] = counter.get(trad, 0) + 1

    return {
        "path": path.relative_to(root).as_posix(),
        "count": sum(counter.values()),
        "chars": counter,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="检查仓库内是否存在繁体字")
    ap.add_argument("--strict", action="store_true",
                    help="发现繁体字时以退出码 1 结束（可用于持续集成）")
    args = ap.parse_args()

    converter = _load_converter()
    files = list(iter_text_files(ROOT))

    print("=" * 66)
    print("繁简混排检查")
    print("=" * 66)
    print(f"扫描目录：{ROOT}")
    print(f"检查文件：{len(files)} 个\n")

    problems = []
    for p in files:
        r = check_file(p, ROOT, converter)
        if r:
            problems.append(r)

    if not problems:
        print("✅ 全部文件均为简体中文，未发现繁体字。")
        print()
        print("覆盖范围：文档（.md）、报告（.html）、代码（.py）、")
        print("          指标表（.csv）、配置（.txt / .json）、Notebook（.ipynb）")
        return 0

    print(f"❌ 发现 {len(problems)} 个文件含繁体字：\n")
    for r in sorted(problems, key=lambda z: -z["count"]):
        detail = "  ".join(f"{k}×{v}" for k, v in sorted(r["chars"].items(), key=lambda z: -z[1]))
        print(f"  {r['path']}  —— {r['count']} 处")
        print(f"      {detail}\n")
    print("建议：将其改为对应简体字后重新运行本脚本。")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
