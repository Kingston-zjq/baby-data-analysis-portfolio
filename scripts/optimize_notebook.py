"""压缩 notebooks/mum_baby_analysis.ipynb，让 GitHub 能正常渲染。

背景：
    GitHub 内置 notebook 渲染器对文件体积敏感，超大文件会整页报
    "Unable to render code block"。本项目notebook 内嵌 15 张图表，
    base64 图片约占文件体积的 96%，是渲染失败的直接原因。

处理动作：
    1. 解码每张 image/png，等比缩放到最大宽度 MAX_WIDTH
    2. 按面积自适应选择 PNG 调色板模式或 JPEG，尽量减小体积
    3. 把 nbformat 降级为 4.4 并去掉 cell id（兼容性最好的组合）
    4. 清理 execution 时间戳等无用元数据

用法（在项目根目录执行）：
    python scripts/optimize_notebook.py

说明：
    本脚本只改notebook 文件，不重新执行分析。
    图表内容与 src/ 逻辑不变，压缩后仍可在本地 Jupyter 正常打开。
"""

import base64
import io
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("缺少 Pillow，请先安装：pip install pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
NB_PATH = ROOT / "notebooks" / "mum_baby_analysis.ipynb"

MAX_WIDTH = 1000        # 显示宽度上限（像素）
SIZE_LIMIT = 1_500_000  # 压缩后仍超此体积则继续降质
JPEG_QUALITY = 82


def encode_png(img: Image.Image, colors: int) -> str:
    """按指定色数导出 8 位调色板 PNG。"""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    quantized = img.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    buf = io.BytesIO()
    quantized.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def encode_jpeg(img: Image.Image, quality: int) -> str:
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def shrink(data_b64: str, max_width: int) -> tuple[str, str, int]:
    """返回 (base64, mime, 字节数)。"""
    raw = base64.b64decode(data_b64)
    img = Image.open(io.BytesIO(raw))
    img.load()

    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, max(1, round(img.height * ratio))), Image.LANCZOS)

    # 先试高色数 PNG；体积仍大则退到低色数，再不行改用 JPEG
    candidates = [
        ("image/png", encode_png(img, 256)),
        ("image/png", encode_png(img, 128)),
        ("image/jpeg", encode_jpeg(img, JPEG_QUALITY)),
        ("image/jpeg", encode_jpeg(img, 68)),
    ]
    mime, best = min(candidates, key=lambda x: len(x[1]))
    return best, mime, len(base64.b64decode(best))


def scrub(node) -> None:
    """清理 execution 时间戳等噪音元数据。"""
    if isinstance(node, dict):
        node.pop("execution", None)
        for value in node.values():
            scrub(value)
    elif isinstance(node, list):
        for item in node:
            scrub(item)


def main() -> int:
    if not NB_PATH.exists():
        print(f"未找到 notebook：{NB_PATH}")
        return 1

    before = NB_PATH.stat().st_size
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))

    images = 0
    saved = 0
    for cell in nb["cells"]:
        for output in cell.get("outputs", []):
            data = output.get("data") or {}
            key = next((k for k in ("image/png", "image/jpeg") if k in data), None)
            if not key:
                continue
            value = data[key]
            if isinstance(value, list):
                value = "".join(value)
            new_b64, mime, raw_bytes = shrink(value, MAX_WIDTH)
            data.pop(key, None)
            data[mime] = new_b64
            output["output_type"] = "display_data"
            output.pop("execution_count", None)
            images += 1
            saved += len(base64.b64decode(value)) - raw_bytes

    scrub(nb)

    # nbformat 4.4 是兼容性最好的组合（4.5 起 cell 必须带 id）
    nb["nbformat"] = 4
    nb["nbformat_minor"] = 4
    for cell in nb["cells"]:
        cell.pop("id", None)
        cell.setdefault("metadata", {})

    NB_PATH.write_text(
        json.dumps(nb, ensure_ascii=False, indent=1, separators=(",", ": ")) + "\n",
        encoding="utf-8",
    )

    after = NB_PATH.stat().st_size
    pct = (1 - after / before) * 100
    print(f"图片处理：{images} 张，节省 {saved / 1024 / 1024:.2f} MB")
    print(f"文件体积：{before / 1024 / 1024:.2f} MB -> {after / 1024 / 1024:.2f} MB（-{pct:.1f}%）")

    if after > 1_000_000:
        print("⚠️  仍超过 1 MB，GitHub 渲染依然可能超时，建议进一步降低 MAX_WIDTH")
        return 1
    print("✅ 体积已处于 GitHub 可正常渲染的区间")
    return 0


if __name__ == "__main__":
    sys.exit(main())