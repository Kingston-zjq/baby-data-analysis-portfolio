"""
图表绘制。

统一风格：浅色底、无上/右边框、中文标注、留白充足，
输出为 150dpi PNG 到 reports/figures/，可直接嵌入 README 与报告。
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from src.config import CAT_COLORS, FIGURE_DIR, PALETTE, TEXT_COLOR, apply_style

apply_style()

C_PRIMARY = PALETTE["primary"]
C_ACCENT = PALETTE["accent"]
C_TEAL = PALETTE["teal"]
C_AMBER = PALETTE["amber"]
C_VIOLET = PALETTE["violet"]
C_GREY = PALETTE["grey"]


# --------------------------------------------------------------------------
# 排版工具：标题与副标题以「点」为单位控制间距，避免不同图高下发生重叠
# --------------------------------------------------------------------------
def _title(ax, title, subtitle=None):
    """单轴图表的标题 + 副标题（左对齐）。"""
    if subtitle:
        ax.set_title(title, loc="left", pad=34)
        ax.annotate(subtitle, xy=(0, 1), xycoords="axes fraction",
                    xytext=(0, 11), textcoords="offset points",
                    fontsize=9.2, color=C_GREY, va="bottom", ha="left")
    else:
        ax.set_title(title, loc="left", pad=10)


def _fig_title(fig, title, subtitle=None, rect_top=None):
    """多子图版式的整体标题，同时为标题预留顶部空间。"""
    h = fig.get_figheight()
    rect_top = rect_top if rect_top is not None else 1 - 0.72 / h
    fig.tight_layout(rect=[0, 0, 1, rect_top])
    gap = 0.30 / h                     # 标题与副标题间距（英寸 -> 图坐标）
    fig.text(0.008, 0.995, title, fontsize=13, fontweight="bold",
             color=TEXT_COLOR, va="top", ha="left")
    if subtitle:
        fig.text(0.008, 0.995 - gap, subtitle, fontsize=9.2,
                 color=C_GREY, va="top", ha="left")


def _save(fig, name: str) -> str:
    path = FIGURE_DIR / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _reverse_cat1():
    from src.config import CAT1_NAME
    return {v: k for k, v in CAT1_NAME.items()}


# --------------------------------------------------------------------------
# 1. 月度趋势
# --------------------------------------------------------------------------
def plot_monthly_trend(m: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12, 5.6))
    x = np.arange(len(m))
    ax.bar(x, m["购买件数"], color=C_PRIMARY, alpha=0.85, width=0.62, label="购买件数")
    ax.set_ylabel("购买件数")
    ax.set_xticks(x)
    ax.set_xticklabels(m["year_month"], rotation=90, fontsize=8)
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, p: f"{v/1000:.0f}k" if v >= 1000 else f"{v:.0f}"))

    ax2 = ax.twinx()
    ax2.plot(x, m["交易笔数"], color=C_ACCENT, lw=2.2, marker="o", ms=3.5, label="交易笔数")
    ax2.set_ylabel("交易笔数", color=C_ACCENT)
    ax2.tick_params(axis="y", colors=C_ACCENT)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(C_ACCENT)

    months = list(m["year_month"])
    for ym, qty in zip(months, m["购买件数"]):
        if ym.endswith("-11"):
            ax.annotate("双11", (months.index(ym), qty), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=8.5,
                        color="#C0392B", fontweight="bold")

    _title(ax, "月度交易趋势：2012.07 – 2015.02",
           "柱=购买件数（左轴），线=交易笔数（右轴）；首尾月份数据不完整，趋势判断以 2013–2014 为准")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    return _save(fig, "fig01_monthly_trend.png")


# --------------------------------------------------------------------------
# 2. 季节性：完整年度的月度占比曲线
# --------------------------------------------------------------------------
def plot_seasonality(share: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    months = list(share.columns)
    x = np.arange(len(months))

    # 大促月底纹
    for m in (6, 11, 12):
        ax.axvspan(m - 1 - 0.5, m - 1 + 0.5, color="#FFF3E0", zorder=0)

    line_colors = {2013: C_GREY, 2014: C_PRIMARY}
    for y in share.index:
        ax.plot(x, share.loc[y], marker="o", ms=5, lw=2.2,
                color=line_colors.get(y, C_ACCENT), label=f"{y} 年")
        ax.annotate(f"{share.loc[y].max():.0f}%",
                    xy=(int(share.loc[y].idxmax()) - 1, share.loc[y].max()),
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=9, color=line_colors.get(y, C_ACCENT), fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}月" for m in months])
    ax.set_ylabel("该月件数占全年比重 (%)")
    ax.set_ylim(0, share.values.max() * 1.25)
    ax.set_xlim(-0.6, len(months) - 0.4)
    ax.legend(loc="upper left", ncol=2)
    ax.text(5.55, share.values.max() * 1.16, "6月", fontsize=8.5, color="#B9770E", ha="center")
    ax.text(10.5, share.values.max() * 1.16, "11–12月", fontsize=8.5, color="#B9770E", ha="center")

    _title(ax, "季节性：年内销量分布（仅统计数据完整的 2013–2014 年）",
           "阴影为电商大促月；两个完整年度的曲线形态高度一致，说明季节性规律稳定，而非偶发波动")
    return _save(fig, "fig02_seasonality.png")


# --------------------------------------------------------------------------
# 3. 星期分布
# --------------------------------------------------------------------------
def plot_weekday(w: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    colors = [C_GREY if d not in ("周六", "周日") else C_PRIMARY for d in w["weekday_name"]]
    bars = ax.bar(w["weekday_name"], w["交易笔数"], color=colors, width=0.6)
    avg = w["交易笔数"].mean()
    ax.axhline(avg, color=C_ACCENT, ls="--", lw=1.5, label=f"日均 {avg:.0f} 笔")
    for b, v, p in zip(bars, w["交易笔数"], w["占比"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{p:.1f}%", ha="center",
                va="bottom", fontsize=9, color="#3A3A3A")
    ax.set_ylabel("交易笔数")
    ax.set_ylim(0, w["交易笔数"].max() * 1.16)
    ax.legend(loc="upper right")
    _title(ax, "一周内的下单分布", "周末下单量略高于工作日均值，但整体波动平缓，不具备明显周内节律")
    return _save(fig, "fig03_weekday.png")


# --------------------------------------------------------------------------
# 4. 大促拉动效果
# --------------------------------------------------------------------------
def plot_promo(p: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    d = p.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(d))
    cols = [C_TEAL, C_PRIMARY, C_ACCENT][-len(d):]
    bars = ax.barh(y, d["拉动倍数"], color=cols, height=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(d["大促"])
    ax.axvline(1, color=C_GREY, ls="--", lw=1.2)
    for b, v, share in zip(bars, d["拉动倍数"], d["件数占全期比重(%)"]):
        ax.text(v + d["拉动倍数"].max() * 0.025, b.get_y() + b.get_height() / 2,
                f"{v}×  （件数占全期 {share}%）", va="center", fontsize=9.5, color="#3A3A3A")
    ax.set_xlabel("大促当日日均件数 ÷ 平日日均件数（虚线 = 1× 平日水平）")
    ax.set_xlim(0, d["拉动倍数"].max() * 1.5)
    ax.grid(axis="y", visible=False)
    _title(ax, "大促节点对销量的拉动倍数",
           "双11 是唯一的强爆发点；618 在当时的淘系母婴品类尚无拉动（该时期 618 属竞对主场）")
    return _save(fig, "fig04_promo_effect.png")


# --------------------------------------------------------------------------
# 5. 一级品类结构
# --------------------------------------------------------------------------
def plot_cat1_share(c: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0), gridspec_kw={"width_ratios": [1, 1.1]})

    # 占比过小的扇区不标注名称，避免标签互相挤压（右图已列出全部品类）
    pie_labels = [n if v >= 6 else "" for n, v in zip(c["品类"], c["件数占比(%)"])]
    wedges, texts, autotexts = axes[0].pie(
        c["件数占比(%)"], labels=pie_labels, autopct="%1.1f%%", startangle=110,
        colors=CAT_COLORS[:len(c)], pctdistance=0.76, labeldistance=1.14,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.6),
        textprops=dict(fontsize=9.5),
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    axes[0].set_title("按购买件数占比", fontsize=11, pad=16)

    y = np.arange(len(c))[::-1]
    axes[1].barh(y, c["笔数占比(%)"], color=CAT_COLORS[:len(c)], height=0.6)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([f"{n}  ({_reverse_cat1().get(n,'')})" for n in c["品类"]], fontsize=9)
    for yy, v, bm in zip(y, c["笔数占比(%)"], c["单笔平均件数"]):
        axes[1].text(v + 0.8, yy, f"{v}%   均 {bm} 件", va="center", fontsize=9, color="#3A3A3A")
    axes[1].set_xlim(0, c["笔数占比(%)"].max() * 1.5)
    axes[1].set_xlabel("交易笔数占比 (%)")
    axes[1].grid(axis="y", visible=False)
    axes[1].set_title("按交易笔数占比 · 单笔件数", fontsize=11, pad=16)

    _fig_title(fig, "一级品类结构：尿裤/湿巾与奶粉/辅食构成绝对主力",
               "左=件数口径（反映消耗体量），右=笔数口径（反映购买频次）；括号内为原始类目编码")
    return _save(fig, "fig05_cat1_share.png")


# --------------------------------------------------------------------------
# 6. 帕累托图
# --------------------------------------------------------------------------
def plot_pareto(p: pd.DataFrame, top_n: int = 30):
    d = p.head(top_n)
    fig, ax = plt.subplots(figsize=(12, 5.4))
    x = np.arange(len(d))
    ax.bar(x, d["购买件数"], color=C_PRIMARY, alpha=0.88, width=0.68, label="购买件数")
    ax.set_ylabel("购买件数")
    ax.set_xticks(x)
    ax.set_xticklabels(d["品类编码"], rotation=90, fontsize=7.5)

    ax2 = ax.twinx()
    ax2.plot(x, d["累计占比(%)"], color=C_ACCENT, lw=2.2, marker="o", ms=3.5, label="累计占比")
    ax2.set_ylabel("累计占比 (%)", color=C_ACCENT)
    ax2.tick_params(axis="y", colors=C_ACCENT)
    ax2.set_ylim(0, 105)
    ax2.grid(False)
    ax2.axhline(80, color=C_GREY, ls="--", lw=1.1)
    ax2.text(len(d) - 1, 81.5, "80% 线", fontsize=9, color=C_GREY, ha="right")

    top10 = p["累计占比(%)"].iloc[9]
    _title(ax, f"二级类目销售额帕累托图（Top {top_n} / 共 {len(p)} 个类目）",
           f"前 10 个二级类目贡献 {top10:.1f}% 的件数；头部集中度中等，长尾依然贡献近半销量")
    return _save(fig, "fig06_pareto.png")


# --------------------------------------------------------------------------
# 7. 购买量分布
# --------------------------------------------------------------------------
def plot_buy_mount_dist(trade: pd.DataFrame):
    n = len(trade)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

    vc = trade["buy_mount"].value_counts().sort_index()
    axes[0].plot(vc.index, vc.values, color=C_PRIMARY, lw=1.8)
    axes[0].scatter(vc.index, vc.values, s=14, color=C_PRIMARY, zorder=3)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("单笔购买件数（对数刻度）")
    axes[0].set_ylabel("交易笔数（对数刻度）")
    axes[0].set_title("长尾分布：1 件是绝对主流，之后迅速衰减", fontsize=11, pad=12)
    axes[0].annotate(f"1 件：{vc.iloc[0]:,} 笔", xy=(1.15, vc.iloc[0] * 0.9),
                     fontsize=9.5, color="#3A3A3A")

    top = vc.head(10)
    axes[1].bar([str(i) for i in top.index], top.values, color=C_TEAL, width=0.62)
    for i, v in enumerate(top.values):
        axes[1].text(i, v, f"{v/n*100:.1f}%", ha="center", va="bottom", fontsize=9)
    axes[1].set_xlabel("单笔购买件数")
    axes[1].set_ylabel("交易笔数")
    axes[1].set_ylim(0, top.max() * 1.16)
    axes[1].set_title("Top10 购买量档位及占比", fontsize=11, pad=12)

    _fig_title(fig, "购买量分布：87.9% 的订单只买 1 件，大单极少但拉高了整体均值",
               f"众数与中位数均为 1 件，均值却被大额囤货单拉到 {trade['buy_mount'].mean():.2f} 件（偏度 133）")
    return _save(fig, "fig07_buy_mount_dist.png")


# --------------------------------------------------------------------------
# 8. 各品类囤货倾向
# --------------------------------------------------------------------------
def plot_bulk_by_cat(b: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    d = b.sort_values("平均单笔件数", ascending=True)
    y = np.arange(len(d))
    colors = [C_PRIMARY if v >= 2 else C_GREY for v in d["平均单笔件数"]]
    ax.barh(y, d["平均单笔件数"], color=colors, height=0.58)
    for yy, v, r in zip(y, d["平均单笔件数"], d["囤货笔数占比(%)"]):
        ax.text(v + 0.06, yy, f"{v} 件   囤货单占比 {r}%", va="center", fontsize=9, color="#3A3A3A")
    ax.set_yticks(y)
    ax.set_yticklabels(d["品类"])
    ax.set_xlabel("平均单笔购买件数")
    ax.set_xlim(0, d["平均单笔件数"].max() * 1.7)
    ax.grid(axis="y", visible=False)
    ax.axvline(1, color=C_GREY, ls="--", lw=1.1)
    _title(ax, "各品类的囤货倾向",
           "尿裤/湿巾平均每单 4.1 件，是唯一具备明显囤货特征的品类；其余品类均为即时性购买")
    return _save(fig, "fig08_bulk_by_cat.png")


# --------------------------------------------------------------------------
# 9. 宝宝画像
# --------------------------------------------------------------------------
def plot_baby_profile(year: pd.DataFrame, baby: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.55, 1]})

    axes[0].bar(year["birth_year"].astype(str), year["宝宝数"], color=C_PRIMARY, width=0.6)
    for i, v in enumerate(year["宝宝数"]):
        axes[0].text(i, v, str(v), ha="center", va="bottom", fontsize=9)
    axes[0].set_xlabel("宝宝出生年份")
    axes[0].set_ylabel("宝宝数")
    axes[0].set_ylim(0, year["宝宝数"].max() * 1.2)
    axes[0].set_title("有档案宝宝的出生年份分布", fontsize=11, pad=12)

    g = baby["gender_name"].value_counts()
    axes[1].pie(g.values, labels=g.index, autopct="%1.1f%%", startangle=90,
                colors=[C_ACCENT, C_PRIMARY, C_GREY][:len(g)],
                wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.6),
                textprops=dict(fontsize=10))
    axes[1].set_title("宝宝性别构成", fontsize=11, pad=12)

    _fig_title(fig, f"宝宝画像：{baby['user_id'].nunique()} 位有档案用户，集中在 2011–2014 年出生",
               "性别编码依天池官方说明（0=女宝 1=男宝 2=未知）；中文二手资料存在相反编码，故本报告性别结论均作对称表述")
    return _save(fig, "fig09_baby_profile.png")


# --------------------------------------------------------------------------
# 10. 月龄 × 品类偏好热力图
# --------------------------------------------------------------------------
def plot_age_category(lift: pd.DataFrame, counts: pd.DataFrame):
    if lift.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 4.6))
    span = max(0.8, float(np.abs(lift.values - 1).max()))
    im = ax.imshow(lift.values, cmap="RdBu_r", vmin=1 - span, vmax=1 + span, aspect="auto")
    ax.set_xticks(range(lift.shape[1]))
    ax.set_xticklabels(lift.columns, fontsize=9.5)
    ax.set_yticks(range(lift.shape[0]))
    ax.set_yticklabels(lift.index, fontsize=9.5)
    ax.grid(False)
    ax.tick_params(length=0)
    for i in range(lift.shape[0]):
        for j in range(lift.shape[1]):
            v = lift.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if abs(v - 1) > span * 0.62 else "#3A3A3A")
    cb = fig.colorbar(im, ax=ax, pad=0.018)
    cb.set_label("偏好指数（>1 表示高于平均）", fontsize=9)
    _title(ax, "月龄段 × 主营品类 偏好指数",
           "基于 810 位可对齐交易的有档案用户；指数 = 该月龄段该品类占比 ÷ 整体该品类占比")
    return _save(fig, "fig10_age_category_heatmap.png")


# --------------------------------------------------------------------------
# 11. 性别 × 品类
# --------------------------------------------------------------------------
def plot_gender_category(ct: pd.DataFrame, res: pd.DataFrame):
    if ct.empty:
        return None
    fig, ax = plt.subplots(figsize=(11, 4.8))
    pct = ct.div(ct.sum(axis=0), axis=1) * 100
    x = np.arange(len(pct))
    w = 0.36
    names = {0: "女宝(编码0)", 1: "男宝(编码1)"}
    for k, (col, color) in enumerate(zip(pct.columns, [C_ACCENT, C_PRIMARY])):
        bars = ax.bar(x + (k - 0.5) * w, pct[col], w, color=color, label=names.get(col, str(col)))
        for b, v in zip(bars, pct[col]):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.45, f"{v:.1f}%",
                    ha="center", fontsize=8.6, color="#3A3A3A")
    ax.set_xticks(x)
    ax.set_xticklabels(pct.index, fontsize=9.5)
    ax.set_ylabel("占该性别宝宝交易的比重 (%)")
    ax.set_ylim(0, pct.values.max() * 1.24)
    ax.legend(title="宝宝性别", loc="upper right")
    verdict = res.loc[res["指标"] == "结论", "数值"].iloc[0] if not res.empty else ""
    pval = res.loc[res["指标"] == "p 值", "数值"].iloc[0] if not res.empty else ""
    v = res.loc[res["指标"] == "Cramér's V（效应量）", "数值"].iloc[0] if not res.empty else ""
    _title(ax, "不同性别宝宝的品类偏好对比",
           f"卡方检验 p={pval} → {verdict}；Cramér's V={v}（接近 0 表示几乎无关联）")
    return _save(fig, "fig11_gender_category.png")


# --------------------------------------------------------------------------
# 12. 商品属性
# --------------------------------------------------------------------------
def plot_property(diversity: pd.DataFrame, trade: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})

    d = diversity.head(10).sort_values("出现次数")
    y = np.arange(len(d))
    axes[0].barh(y, d["出现次数"], color=C_TEAL, height=0.6)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([f"属性键 {k}" for k in d["prop_key"]], fontsize=9)
    axes[0].set_xlabel("出现次数")
    for yy, v, k in zip(y, d["出现次数"], d["取值数"]):
        axes[0].text(v + d["出现次数"].max() * 0.02, yy,
                     f"{int(v):,} 次 · {int(k)} 种取值", va="center", fontsize=8.6, color="#3A3A3A")
    axes[0].set_xlim(0, d["出现次数"].max() * 1.9)
    axes[0].grid(axis="y", visible=False)
    axes[0].set_title("高频商品属性维度 Top10", fontsize=11, pad=12)

    s = trade["n_props"].clip(upper=12)
    vc = s.value_counts().sort_index()
    axes[1].bar([str(i) for i in vc.index], vc.values, color=C_VIOLET, width=0.62)
    axes[1].set_xlabel("商品属性维度数量（≥12 归并到 12）")
    axes[1].set_ylabel("交易笔数")
    axes[1].set_title("每条交易的属性维度数分布", fontsize=11, pad=12)

    _fig_title(fig, "商品属性挖掘：属性键被平台脱敏，但可刻画商品的描述丰富度",
               "同一属性键的取值数差异极大——3–5 种的多为枚举型属性（如规格），上千种的更接近品牌或型号标识")
    return _save(fig, "fig12_property.png")


# --------------------------------------------------------------------------
# 13. 年度对比
# --------------------------------------------------------------------------
def plot_year_compare(trade: pd.DataFrame):
    base = trade[(trade["year"] >= 2013) & (trade["year"] <= 2014)]
    g = base.groupby("year").agg(
        购买件数=("buy_mount", "sum"),
        交易笔数=("auction_id", "count"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    x = np.arange(len(g))
    w = 0.34
    b1 = ax.bar(x - w / 2, g["购买件数"], w, color=C_PRIMARY, label="购买件数")
    b2 = ax.bar(x + w / 2, g["交易笔数"], w, color=C_ACCENT, label="交易笔数")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{int(b.get_height()):,}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{y} 年" for y in g["year"]])
    ax.set_ylabel("数量")
    ax.set_ylim(0, g["购买件数"].max() * 1.22)
    ax.legend(loc="upper left")
    growth = (g["购买件数"].iloc[1] / g["购买件数"].iloc[0] - 1) * 100
    _title(ax, "完整年度对比（2013 vs 2014）", f"2014 年购买件数同比 {growth:+.1f}%，处于高速增长期")
    return _save(fig, "fig13_year_compare.png")


# --------------------------------------------------------------------------
# 14. 模型评估
# --------------------------------------------------------------------------
def plot_model_results(res: dict):
    from sklearn.metrics import precision_recall_curve, roc_curve

    y = res["y"]
    proba = res["proba"]
    best = res["summary"].loc[res["summary"]["指标"] == "最优模型", "数值"].iloc[0]
    auc = res["results"][best]["ROC-AUC"]
    pr = res["results"][best]["PR-AUC"]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    fpr, tpr, _ = roc_curve(y, proba)
    axes[0].plot(fpr, tpr, color=C_PRIMARY, lw=2.2, label=f"{best}  AUC = {auc}")
    axes[0].plot([0, 1], [0, 1], color=C_GREY, ls="--", lw=1.2, label="随机基线")
    axes[0].set_xlabel("假正率 FPR")
    axes[0].set_ylabel("真正率 TPR")
    axes[0].set_title("ROC 曲线", fontsize=11, pad=12)
    axes[0].legend(loc="lower right")

    prec, rec, _ = precision_recall_curve(y, proba)
    base = y.mean()
    axes[1].plot(rec, prec, color=C_ACCENT, lw=2.2, label=f"PR-AUC = {pr}")
    axes[1].axhline(base, color=C_GREY, ls="--", lw=1.2, label=f"随机基线 = {base:.3f}")
    axes[1].set_xlabel("召回率 Recall")
    axes[1].set_ylabel("精确率 Precision")
    axes[1].set_title("精确率-召回率曲线", fontsize=11, pad=12)
    axes[1].legend(loc="upper right")

    cm = np.array(res["cm"])
    axes[2].imshow(cm, cmap="Blues")
    axes[2].set_xticks([0, 1]); axes[2].set_xticklabels(["预测:非囤货", "预测:囤货"], fontsize=9)
    axes[2].set_yticks([0, 1]); axes[2].set_yticklabels(["实际:非囤货", "实际:囤货"], fontsize=9)
    axes[2].grid(False); axes[2].tick_params(length=0)
    for i in range(2):
        for j in range(2):
            axes[2].text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=12.5,
                         color="white" if cm[i, j] > cm.max() * 0.55 else "#2C3E50",
                         fontweight="bold")
    axes[2].set_title("混淆矩阵（最佳 F1 阈值）", fontsize=11, pad=12)

    _fig_title(fig, "囤货订单识别模型评估（5 折交叉验证）",
               f"目标：预测单笔订单是否购买 ≥3 件；正类占比 6.13%，PR-AUC {pr} 显著高于随机基线 {base:.3f}")
    return _save(fig, "fig14_model_eval.png")


def plot_feature_importance(imp: pd.DataFrame):
    d = imp.head(12).sort_values("重要性")
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    y = np.arange(len(d))
    ax.barh(y, d["重要性"], color=C_VIOLET, height=0.6)
    for yy, v in zip(y, d["重要性"]):
        ax.text(v + d["重要性"].max() * 0.015, yy, f"{v:.3f}", va="center", fontsize=9, color="#3A3A3A")
    ax.set_yticks(y); ax.set_yticklabels(d["特征"], fontsize=9.5)
    ax.set_xlabel("特征重要性（Gini importance）")
    ax.set_xlim(0, d["重要性"].max() * 1.22)
    ax.grid(axis="y", visible=False)
    _title(ax, "哪些因素决定了订单是否会囤货",
           "商品属性维度数（描述越丰富越可能属大包装商品）与品类是首要信号；时间特征影响较弱")
    return _save(fig, "fig15_feature_importance.png")


# --------------------------------------------------------------------------
# 16. 大额异常订单与整体贡献集中度
# --------------------------------------------------------------------------
def plot_outliers(top: pd.DataFrame, long_tail: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8),
                             gridspec_kw={"width_ratios": [1.15, 1]})

    d = top.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(d))
    colors = [C_ACCENT if v >= 1000 else C_PRIMARY for v in d["buy_mount"]]
    axes[0].barh(y, d["buy_mount"], color=colors, height=0.6)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([f"#{int(r)}" for r in d["排名"]], fontsize=9)
    for yy, v, c in zip(y, d["buy_mount"], d["累计占比(%)"]):
        axes[0].text(v * 1.05, yy, f"{int(v):,} 件  （累计 {c}%）", va="center",
                     fontsize=8.8, color="#3A3A3A")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("单笔购买件数（对数刻度）")
    axes[0].set_xlim(50, 40000)
    axes[0].grid(axis="y", visible=False)
    axes[0].set_title("单笔件数 Top10 订单", fontsize=11, pad=12)

    lt = long_tail
    axes[1].plot(lt["订单占比(%)"], lt["累计件数占比(%)"], color=C_PRIMARY, lw=2.2)
    axes[1].plot([0, 100], [0, 100], color=C_GREY, ls="--", lw=1.2, label="完全均等线")
    for pct, label, dy in [(0.1, "前 0.1%", -26), (1, "前 1%", 4)]:
        v = np.interp(pct, lt["订单占比(%)"], lt["累计件数占比(%)"])
        axes[1].scatter([pct], [v], color="#C0392B", zorder=4, s=32)
        axes[1].annotate(f"{label} 订单贡献 {v:.0f}% 件数", xy=(pct, v),
                         xytext=(12, dy), textcoords="offset points",
                         fontsize=9, color="#C0392B")
    axes[1].set_xlabel("订单占比 (%)（按件数从大到小累计）")
    axes[1].set_ylabel("累计件数占比 (%)")
    axes[1].set_xlim(0, 100)
    axes[1].set_ylim(0, 100)
    axes[1].legend(loc="lower right")
    axes[1].set_title("大单贡献集中度", fontsize=11, pad=12)

    _fig_title(fig, "异常识别：极少数超级大单贡献了绝大多数件数",
               "排名第 1 的订单一次购买 10,000 件，单笔即占全部件数的 13.1%；这类订单更可能是批发或非真实消费行为")
    return _save(fig, "fig16_outliers.png")
