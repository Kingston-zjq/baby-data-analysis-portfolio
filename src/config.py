"""
项目全局配置：路径、绘图风格、中文字体、业务字典。

所有脚本通过 from src.config import ... 复用这里的设置，
保证全项目图表风格统一。
"""

from pathlib import Path

# --------------------------------------------------------------------------
# 路径配置
# --------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
REPORT_DIR = ROOT_DIR / "reports"
FIGURE_DIR = REPORT_DIR / "figures"
TABLE_DIR = REPORT_DIR / "tables"

BABY_RAW_FILE = DATA_RAW_DIR / "mum_baby.csv"
TRADE_RAW_FILE = DATA_RAW_DIR / "mum_baby_trade_history.csv"

TRADE_CLEAN_FILE = DATA_PROCESSED_DIR / "trade_clean.csv"
BABY_CLEAN_FILE = DATA_PROCESSED_DIR / "baby_clean.csv"
USER_PROFILE_FILE = DATA_PROCESSED_DIR / "user_profile.csv"

for _d in (DATA_PROCESSED_DIR, FIGURE_DIR, TABLE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 绘图风格（浅色、干净、适合放进 GitHub README）
# --------------------------------------------------------------------------
PALETTE = {
    "primary": "#4C7DF0",   # 主蓝
    "accent": "#FF7A9C",    # 母婴粉
    "teal": "#3DC7A0",      # 青绿
    "amber": "#FFB020",     # 琥珀
    "violet": "#8B7BF0",    # 紫
    "coral": "#FF8A65",     # 珊瑚
    "grey": "#8C9BAB",      # 中性灰
    "dark": "#2C3E50",      # 深色文字
}

# 多系列图表使用的循环配色
CAT_COLORS = [
    PALETTE["primary"], PALETTE["accent"], PALETTE["teal"], PALETTE["amber"],
    PALETTE["violet"], PALETTE["coral"], PALETTE["grey"],
]

GRID_COLOR = "#E6EAF0"
TEXT_COLOR = PALETTE["dark"]

FIGURE_DPI = 150
FIGURE_SIZE = (10, 5.5)

# --------------------------------------------------------------------------
# 业务字典：一级品类编码 -> 中文名称
# 编码含义依据天池该数据集公开的类目体系整理
# --------------------------------------------------------------------------
# 注意：编码含义依据天池该数据集附带的 meaning 对照表与社区资料整理，
# 该对照表未包含在本次样本中，仅供理解参考。报告中所有图表均同时标注原始编码。
CAT1_NAME = {
    "50008168": "奶粉/辅食",
    "28": "尿裤/湿巾",
    "50014815": "童装/童鞋",
    "50022520": "喂养/洗护",
    "122650008": "妈妈专区",
    "38": "玩具/童车",
}

# 目标人群的核心品类（用于业务结论）
CORE_CATEGORIES = ["奶粉/辅食", "尿裤/湿巾"]

# 性别编码：依据天池官方 Overview 说明
# （"0" denotes female, "1" denotes male, "2" denotes unknown）
# 说明：部分中文二手资料编码相反，故本报告性别相关结论均做对称表述，不依赖映射方向。
GENDER_NAME = {0: "女宝(0)", 1: "男宝(1)", 2: "未知(2)"}

# 由宝宝生日划分的月龄分段
AGE_BINS = [-1, 6, 12, 24, 36, 72, 999]
AGE_LABELS = ["0-6月", "7-12月", "13-24月", "25-36月", "3-6岁", "6岁以上"]


def apply_style():
    """应用统一的 matplotlib 样式，自动处理中文字体。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # Windows / macOS / Linux 常见中文字体，取第一个可用的
    candidates = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
        "Source Han Sans CN", "PingFang SC", "WenQuanYi Zen Hei",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates if c in available), None)
    if chosen:
        plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False

    plt.rcParams.update({
        "figure.dpi": FIGURE_DPI,
        "savefig.dpi": FIGURE_DPI,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "axes.titlecolor": TEXT_COLOR,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    return chosen
