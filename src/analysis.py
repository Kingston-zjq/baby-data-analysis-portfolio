"""
业务分析指标计算。

每个函数只负责算数，返回 DataFrame / dict，不负责画图，
保证指标可复用到 notebook、报告和脚本中。
"""

import numpy as np
import pandas as pd
from scipy import stats

from src.config import AGE_LABELS, TABLE_DIR


def save_table(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """把中间结果落盘到 reports/tables，方便报告引用与人工核对。"""
    df.to_csv(TABLE_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
    return df


# --------------------------------------------------------------------------
# A. 规模概览
# --------------------------------------------------------------------------
def overview(trade: pd.DataFrame, baby: pd.DataFrame) -> pd.DataFrame:
    valid = trade[trade["day"] < "2015-02-01"]  # 末月数据不完整，单独剔除
    return pd.DataFrame([
        {"指标": "交易笔数", "数值": len(trade)},
        {"指标": "购买总件数", "数值": int(trade["buy_mount"].sum())},
        {"指标": "覆盖用户数", "数值": trade["user_id"].nunique()},
        {"指标": "覆盖商品数", "数值": trade["auction_id"].nunique()},
        {"指标": "一级类目数", "数值": trade["cat1"].nunique()},
        {"指标": "二级类目数", "数值": trade["cat_id"].nunique()},
        {"指标": "时间跨度", "数值": f"{trade['day'].min():%Y-%m-%d} ~ {trade['day'].max():%Y-%m-%d}"},
        {"指标": "平均单笔件数", "数值": round(trade["buy_mount"].mean(), 2)},
        {"指标": "单笔件数中位数", "数值": int(trade["buy_mount"].median())},
        {"指标": "有宝宝档案的用户", "数值": baby["user_id"].nunique()},
        {"指标": "完整年度交易笔数(2013-2014)", "数值": len(valid[(valid["year"] >= 2013) & (valid["year"] <= 2014)])},
    ])


# --------------------------------------------------------------------------
# B. 时间维度
# --------------------------------------------------------------------------
def monthly_trend(trade: pd.DataFrame) -> pd.DataFrame:
    """月度交易笔数与购买件数趋势。"""
    g = trade.groupby("year_month").agg(
        交易笔数=("auction_id", "count"),
        购买件数=("buy_mount", "sum"),
        活跃用户=("user_id", "nunique"),
    ).reset_index()
    g["年月"] = pd.to_datetime(g["year_month"], format="%Y-%m")
    return g.sort_values("年月").reset_index(drop=True)


def year_season_matrix(trade: pd.DataFrame) -> pd.DataFrame:
    """年 × 月 的购买件数矩阵。"""
    m = trade.pivot_table(index="year", columns="month", values="buy_mount",
                          aggfunc="sum", fill_value=0)
    m = m.reindex(columns=range(1, 13), fill_value=0)
    return m


# 数据完整的年份（2012 仅含 7–12 月，2015 仅含 1–2 月）
COMPLETE_YEARS = [2013, 2014]


def monthly_share_by_year(trade: pd.DataFrame,
                          years=None) -> pd.DataFrame:
    """只在数据完整的年份内，计算各月件数占该年总件数的比重（%）。

    直接对不完整年份做行归一化会产生「2015年1月占88%」这类假象，
    因此这里默认只保留 2013–2014 两个完整年度。
    """
    years = years or COMPLETE_YEARS
    base = trade[trade["year"].isin(years)]
    m = base.pivot_table(index="year", columns="month", values="buy_mount",
                         aggfunc="sum", fill_value=0).reindex(columns=range(1, 13), fill_value=0)
    return (m.div(m.sum(axis=1), axis=0) * 100).round(2)


def weekday_distribution(trade: pd.DataFrame) -> pd.DataFrame:
    order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    g = trade.groupby("weekday_name").agg(
        交易笔数=("auction_id", "count"),
        购买件数=("buy_mount", "sum"),
    ).reindex(order).reset_index()
    g["占比"] = (g["交易笔数"] / g["交易笔数"].sum() * 100).round(2)
    return g


def promo_effect(trade: pd.DataFrame) -> pd.DataFrame:
    """量化大促节点的拉动效果：大促日均件数 / 平日日均件数。"""
    base = trade[trade["day"] < "2015-02-01"]
    total_days = base["day"].nunique()
    total_qty = base["buy_mount"].sum()
    daily_avg = total_qty / total_days

    rows = []
    for promo in ["双11", "双12", "618"]:
        sub = base[base["promo"] == promo]
        if sub.empty:
            continue
        days = sub["day"].nunique()
        qty = sub["buy_mount"].sum()
        rows.append({
            "大促": promo,
            "覆盖天数": days,
            "总件数": int(qty),
            "大促日均件数": round(qty / days, 1),
            "平日日均件数": round(daily_avg, 1),
            "拉动倍数": round((qty / days) / daily_avg, 2),
            "件数占全期比重(%)": round(qty / total_qty * 100, 2),
        })
    return pd.DataFrame(rows).sort_values("拉动倍数", ascending=False).reset_index(drop=True)


def top_promo_days(trade: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    g = trade.groupby("day").agg(
        交易笔数=("auction_id", "count"),
        购买件数=("buy_mount", "sum"),
    ).reset_index()
    g["日期"] = g["day"].dt.strftime("%Y-%m-%d")
    g["星期"] = g["day"].dt.dayofweek.map(
        {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"})
    return g.nlargest(n, "购买件数")[["日期", "星期", "交易笔数", "购买件数"]].reset_index(drop=True)


# --------------------------------------------------------------------------
# C. 品类维度
# --------------------------------------------------------------------------
def category_breakdown(trade: pd.DataFrame, level: str = "cat1_name") -> pd.DataFrame:
    g = trade.groupby(level).agg(
        交易笔数=("auction_id", "count"),
        购买件数=("buy_mount", "sum"),
        商品数=("auction_id", "nunique"),
    ).reset_index().rename(columns={level: "品类"})
    g["笔数占比(%)"] = (g["交易笔数"] / g["交易笔数"].sum() * 100).round(2)
    g["件数占比(%)"] = (g["购买件数"] / g["购买件数"].sum() * 100).round(2)
    g["单笔平均件数"] = (g["购买件数"] / g["交易笔数"]).round(2)
    return g.sort_values("购买件数", ascending=False).reset_index(drop=True)


def category_pareto(trade: pd.DataFrame, level: str = "cat_id") -> pd.DataFrame:
    g = trade.groupby(level)["buy_mount"].sum().sort_values(ascending=False).reset_index()
    g.columns = ["品类编码", "购买件数"]
    g["累计件数"] = g["购买件数"].cumsum()
    g["累计占比(%)"] = (g["累计件数"] / g["购买件数"].sum() * 100).round(2)
    g["排名"] = np.arange(1, len(g) + 1)
    return g


def concentration_metrics(pareto: pd.DataFrame) -> pd.DataFrame:
    """集中度：CR5 / CR10 / CR20 与赫芬达尔指数 HHI。"""
    total = pareto["购买件数"].sum()
    def cr(k):
        return round(pareto["购买件数"].head(k).sum() / total * 100, 2)
    share = pareto["购买件数"] / total
    hhi = round((share ** 2).sum() * 10000, 1)
    return pd.DataFrame([
        {"指标": "CR5（前5类目件数占比）", "数值": f"{cr(5)}%"},
        {"指标": "CR10", "数值": f"{cr(10)}%"},
        {"指标": "CR20", "数值": f"{cr(20)}%"},
        {"指标": "类目总数", "数值": len(pareto)},
        {"指标": "HHI（赫芬达尔指数）", "数值": hhi},
        {"指标": "贡献后50%件数的类目数", "数值": int((pareto["累计占比(%)"] < 50).sum() + 1)},
    ])


# --------------------------------------------------------------------------
# D. 购买量 / 囤货行为
# --------------------------------------------------------------------------
def buy_mount_stats(trade: pd.DataFrame) -> pd.DataFrame:
    s = trade["buy_mount"]
    return pd.DataFrame([
        {"指标": "平均数", "数值": round(s.mean(), 2)},
        {"指标": "中位数", "数值": s.median()},
        {"指标": "众数", "数值": s.mode().iloc[0]},
        {"指标": "标准差", "数值": round(s.std(), 2)},
        {"指标": "P90", "数值": s.quantile(0.9)},
        {"指标": "P99", "数值": s.quantile(0.99)},
        {"指标": "最大值", "数值": s.max()},
        {"指标": "单件购买占比(%)", "数值": round((s == 1).mean() * 100, 2)},
        {"指标": "囤货(≥3件)占比(%)", "数值": round((s >= 3).mean() * 100, 2)},
        {"指标": "偏度", "数值": round(s.skew(), 2)},
        {"指标": "峰度", "数值": round(s.kurt(), 2)},
    ])


def bulk_by_category(trade: pd.DataFrame) -> pd.DataFrame:
    g = trade.groupby("cat1_name").agg(
        交易笔数=("auction_id", "count"),
        平均单笔件数=("buy_mount", "mean"),
        囤货笔数=("is_bulk", "sum"),
    ).reset_index().rename(columns={"cat1_name": "品类"})
    g["囤货笔数占比(%)"] = (g["囤货笔数"] / g["交易笔数"] * 100).round(2)
    g["平均单笔件数"] = g["平均单笔件数"].round(2)
    return g.sort_values("平均单笔件数", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# E. 异常订单识别
# --------------------------------------------------------------------------
def outlier_orders(trade: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """识别件数最大的若干笔订单，用于判断是否存在批发/异常账号。

    这些「超级大单」会把平均单笔件数、月度趋势等指标整体抬高，
    必须在结论中显式剥离，否则会得出错误判断。
    """
    d = trade.nlargest(n, "buy_mount").copy()
    total = trade["buy_mount"].sum()
    d = d.reset_index(drop=True)
    d["排名"] = np.arange(1, len(d) + 1)
    d["占全部件数比重(%)"] = (d["buy_mount"] / total * 100).round(2)
    d["累计占比(%)"] = d["占全部件数比重(%)"].cumsum().round(2)
    d["日期"] = d["day"].dt.strftime("%Y-%m-%d")
    return d[["排名", "user_id", "auction_id", "cat1_name", "buy_mount",
              "日期", "占全部件数比重(%)", "累计占比(%)"]]


def outlier_impact(trade: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """量化「剔除头部大单」对核心指标的影响。"""
    s = trade["buy_mount"]
    top_sum = s.nlargest(n).sum()
    rest = trade[~trade.index.isin(s.nlargest(n).index)]
    return pd.DataFrame([
        {"指标": "全部订单平均单笔件数", "数值": round(s.mean(), 2)},
        {"指标": f"剔除 Top{n} 大单后的平均单笔件数", "数值": round(rest["buy_mount"].mean(), 2)},
        {"指标": f"Top{n} 大单合计件数", "数值": int(top_sum)},
        {"指标": f"Top{n} 大单占全部件数比重", "数值": f"{top_sum / s.sum() * 100:.1f}%"},
        {"指标": f"Top{n} 大单笔数占比", "数值": f"{n / len(trade) * 100:.3f}%"},
        {"指标": "最大单笔件数", "数值": int(s.max())},
        {"指标": "最大单笔所属品类", "数值": trade.loc[s.idxmax(), "cat1_name"]},
        {"指标": "最大单笔日期", "数值": f"{trade.loc[s.idxmax(), 'day']:%Y-%m-%d}"},
    ])


def long_tail_curve(trade: pd.DataFrame) -> pd.DataFrame:
    """按单笔件数从大到小排序的累计贡献曲线（洛伦兹曲线思想）。"""
    d = trade["buy_mount"].sort_values(ascending=False).reset_index(drop=True)
    n = len(d)
    return pd.DataFrame({
        "订单占比(%)": (np.arange(1, n + 1) / n * 100),
        "累计件数占比(%)": d.cumsum() / d.sum() * 100,
    })


# --------------------------------------------------------------------------
# F. 商品属性
# --------------------------------------------------------------------------
def property_stats(trade: pd.DataFrame) -> pd.DataFrame:
    s = trade["n_props"]
    return pd.DataFrame([
        {"指标": "无属性记录的交易占比(%)", "数值": round((s == 0).mean() * 100, 2)},
        {"指标": "平均属性维度数", "数值": round(s.mean(), 2)},
        {"指标": "属性维度数中位数", "数值": int(s.median())},
        {"指标": "属性维度数最大值", "数值": int(s.max())},
    ])


def property_value_diversity(kv_detail: pd.DataFrame, key_freq: pd.DataFrame) -> pd.DataFrame:
    """每个高频属性键的取值丰富度，用于区分「型号类」与「枚举类」属性。"""
    g = kv_detail.groupby("prop_key").agg(
        取值数=("prop_value", "nunique"),
        出现次数=("prop_value", "size"),
    ).reset_index()
    freq = key_freq.rename(columns={"出现次数": "出现次数_ref"})
    g = g.merge(freq, on="prop_key", how="outer")
    g["出现次数"] = g["出现次数"].fillna(g["出现次数_ref"]).fillna(0).astype(int)
    g = g.drop(columns=["出现次数_ref"])
    g["平均每值出现次数"] = (g["出现次数"] / g["取值数"].replace(0, np.nan)).round(1)
    return g.sort_values("出现次数", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# G. 宝宝画像
# --------------------------------------------------------------------------
def baby_birth_year(baby: pd.DataFrame) -> pd.DataFrame:
    g = baby.groupby("birth_year").size().reset_index(name="宝宝数")
    g["占比(%)"] = (g["宝宝数"] / g["宝宝数"].sum() * 100).round(2)
    return g


def age_stage_preference(user_profile: pd.DataFrame) -> pd.DataFrame:
    """月龄段 × 主营品类 的用户分布。"""
    if user_profile.empty:
        return pd.DataFrame()
    m = user_profile.pivot_table(index="age_stage", columns="主营品类",
                                 values="user_id", aggfunc="count", fill_value=0)
    return m


def gender_category_test(trade_with_baby: pd.DataFrame) -> tuple:
    """性别 vs 品类偏好 的卡方独立性检验。

    仅使用有明确性别（0/1）的用户，返回 (交叉表, 检验结果)。
    """
    d = trade_with_baby[trade_with_baby["gender"].isin([0, 1])]
    if d.empty:
        return pd.DataFrame(), pd.DataFrame()
    ct = pd.crosstab(d["cat1_name"], d["gender"])
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    # Cramér's V 效应量
    n = ct.values.sum()
    v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    res = pd.DataFrame([
        {"指标": "卡方统计量", "数值": round(chi2, 2)},
        {"指标": "自由度", "数值": dof},
        {"指标": "p 值", "数值": f"{p:.4f}"},
        {"指标": "结论", "数值": "存在显著差异 (p<0.05)" if p < 0.05 else "无显著差异 (p>=0.05)"},
        {"指标": "Cramér's V（效应量）", "数值": round(v, 3)},
        {"指标": "样本量", "数值": n},
    ])
    return ct, res


def age_category_correlation(user_profile: pd.DataFrame) -> pd.DataFrame:
    """月龄段 × 品类 的偏好指数（该单元格占比 / 整体占比）。"""
    if user_profile.empty:
        return pd.DataFrame()
    pivot = pd.crosstab(user_profile["age_stage"], user_profile["主营品类"], normalize="index")
    overall = user_profile["主营品类"].value_counts(normalize=True)
    lift = pivot.div(overall, axis=1)
    return lift.round(2)


# --------------------------------------------------------------------------
# H. 口径说明：活跃用户数不等于新客数
# --------------------------------------------------------------------------
def new_vs_returning(trade: pd.DataFrame) -> pd.DataFrame:
    """按用户首单月份统计「当月新增用户」与「当月回访用户」。

    注意：本样本按行抽样、复购用户极少，此处仅用于演示口径，
    真实全量数据上该指标才有业务意义。
    """
    first = trade.groupby("user_id")["day"].min().rename("first_day")
    d = trade.merge(first, on="user_id")
    d["is_new"] = d["day"] == d["first_day"]
    g = d.groupby("year_month").agg(
        活跃用户=("user_id", "nunique"),
        新增用户=("is_new", "sum"),
    ).reset_index()
    g["回访用户"] = g["活跃用户"] - g["新增用户"]
    return g.sort_values("year_month").reset_index(drop=True)


def run_all(trade: pd.DataFrame, baby: pd.DataFrame, kv_detail: pd.DataFrame,
            key_freq: pd.DataFrame, user_profile: pd.DataFrame,
            trade_with_baby: pd.DataFrame) -> dict:
    out = {}
    out["overview"] = save_table(overview(trade, baby), "01_overview")
    out["monthly"] = save_table(monthly_trend(trade), "02_monthly_trend")
    out["weekday"] = save_table(weekday_distribution(trade), "03_weekday")
    out["promo"] = save_table(promo_effect(trade), "04_promo_effect")
    out["top_days"] = save_table(top_promo_days(trade), "05_top_days")
    out["cat1"] = save_table(category_breakdown(trade, "cat1_name"), "06_category_cat1")
    out["cat2"] = save_table(category_breakdown(trade, "cat_id").head(20), "07_category_cat2_top20")
    pareto = category_pareto(trade, "cat_id")
    out["pareto"] = save_table(pareto.head(50), "08_pareto_cat2")
    out["concentration"] = save_table(concentration_metrics(pareto), "09_concentration")
    out["buy_mount"] = save_table(buy_mount_stats(trade), "10_buy_mount_stats")
    out["bulk_cat"] = save_table(bulk_by_category(trade), "11_bulk_by_category")
    out["outliers"] = save_table(outlier_orders(trade, 10), "18_top_orders")
    out["outlier_impact"] = save_table(outlier_impact(trade, 10), "19_outlier_impact")
    out["long_tail"] = long_tail_curve(trade)
    out["prop_stats"] = save_table(property_stats(trade), "12_property_stats")
    out["prop_div"] = save_table(property_value_diversity(kv_detail, key_freq).head(20),
                                 "13_property_diversity")
    out["baby_year"] = save_table(baby_birth_year(baby), "14_baby_birth_year")
    out["buy_mount_dist"] = trade["buy_mount"].value_counts().sort_index()
    return out
