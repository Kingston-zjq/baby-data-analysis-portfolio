"""生成 HTML 分析报告。

用法（在项目根目录执行）：
    python scripts/build_report.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import report  # noqa: E402

if __name__ == "__main__":
    path = report.build()
    size = path.stat().st_size / 1024 / 1024
    print(f"报告已生成：{path}")
    print(f"文件大小：{size:.2f} MB（图表已内嵌，可单文件分享）")
