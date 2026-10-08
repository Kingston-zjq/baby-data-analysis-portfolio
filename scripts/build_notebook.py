"""构建 notebooks/mum_baby_analysis.ipynb（供生成后执行）。

用法：
    python scripts/build_notebook.py
"""

import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "notebooks" / "mum_baby_analysis.ipynb"


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


CELLS = [
    md("""
# 母婴电商购物行为分析

**数据来源**：阿里云天池 · 淘宝母婴购物数据集（Baby Goods Info Data）

**分析目标**：在一个真实的电商交易数据集上，完成从数据质量体检、业务指标分析、
可视化到机器学习建模的完整链路。

**使用说明**：本 notebook 直接调用 `src/` 下的模块，与 `scripts/run_all.py` 保持同一套逻辑，
所有结果可复现。

---

## 0. 环境准备
"""),
    code("""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 让 notebook 能 import 到 src 包
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))

from src import analysis, data_loader, modeling, preprocess, visualize
from src.config import FIGURE_DIR, TABLE_DIR, apply_style

apply_style()
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.max_columns", 50)

from IPython.display import Image, display


def show(path):
    # 重新加载 PNG 显示（绘图函数内部会关闭 figure，因此不能依赖 inline 输出）
    display(Image(filename=str(path)))


print("工作目录:", ROOT)
"""),

    md("""
---

## 1. 数据加载与质量体检

分析的第一步不是算指标，而是**搞清楚这份数据能回答什么问题**。
"""),
    code("""
trade_raw = data_loader.load_trade()
baby_raw = data_loader.load_baby()

print(f"交易明细：{trade_raw.shape[0]:,} 行 × {trade_raw.shape[1]} 列")
print(f"宝宝信息：{baby_raw.shape[0]:,} 行 × {baby_raw.shape[1]} 列")
trade_raw.head()
"""),
    code("""
quality = data_loader.quality_report(trade_raw, baby_raw)
quality
"""),
    md("""
### 1.1 关键判断：这是一份「按行抽样」的数据

从体检表可以看到：**29,971 笔交易对应 29,944 个用户，人均仅 1.0009 笔**，只有 25 个用户有复购。

这意味着这份样本不是用户行为序列，而是随机抽取的交易行。由此得出一个重要的分析边界：

> **不能做**：RFM 分层、复购周期、用户生命周期、基于用户行为序列的性别预测
> **可以做**：交易分析、品类结构、时间趋势、商品属性、宝宝画像

主动划清边界，比硬做出一堆无效结论更有价值。
"""),

    md("""
---

## 2. 数据清洗与特征工程
"""),
    code("""
pack = preprocess.run(trade_raw, baby_raw)

trade = pack["trade"]           # 交易明细 + 时间特征 + 属性特征
baby = pack["baby"]             # 宝宝档案
user_profile = pack["user_profile"]   # 宝宝档案 ⋈ 交易聚合

print(f"清洗后交易：{len(trade):,} 行")
print(f"宝宝档案：{len(baby):,} 行")
print(f"用户画像：{len(user_profile):,} 行")
trade[["user_id", "cat1_name", "buy_mount", "day", "year_month",
       "weekday_name", "is_promo", "n_props", "is_bulk"]].head()
"""),

    md("""
---

## 3. 时间维度分析

### 3.1 月度趋势
"""),
    code("""
monthly = analysis.monthly_trend(trade)
show(visualize.plot_monthly_trend(monthly))
monthly.tail(12)[["year_month", "交易笔数", "购买件数", "活跃用户"]]
"""),
    md("""
### 3.2 季节性：只在数据完整的年度内比较

2012 年只有 7–12 月数据、2015 年只有 1–2 月数据，直接做行归一化会产生
「2015 年 1 月占全年 88%」的假象。因此只使用 2013–2014 两个完整年度。
"""),
    code("""
share = analysis.monthly_share_by_year(trade)
show(visualize.plot_seasonality(share))
share.round(1)
"""),
    md("""
### 3.3 大促拉动效果
"""),
    code("""
promo = analysis.promo_effect(trade)
show(visualize.plot_promo(promo))
promo
"""),
    md("""
**结论**：双11 拉动 5.19 倍、双12 拉动 2.26 倍，而 **618 只有 0.64 倍**（低于平日）。

在 2012–2014 年的淘系母婴品类中，618 尚未形成大促心智。这提醒我们：
**行业常识需要被数据验证，不能直接照搬**。
"""),
    code("""
show(visualize.plot_weekday(analysis.weekday_distribution(trade)))
analysis.top_promo_days(trade, 10)
"""),

    md("""
---

## 4. 品类结构分析
"""),
    code("""
cat1 = analysis.category_breakdown(trade, "cat1_name")
show(visualize.plot_cat1_share(cat1))
cat1
"""),
    code("""
pareto = analysis.category_pareto(trade, "cat_id")
show(visualize.plot_pareto(pareto))
analysis.concentration_metrics(pareto)
"""),
    md("""
**结论**：CR10 = 44.5%、HHI = 394.8，属于「中等集中度 + 长尾厚」的结构。
头部没有绝对垄断品类，662 个二级类目中的长尾依然贡献近半销量。
"""),

    md("""
---

## 5. 购买量分布与异常订单识别

### 5.1 购买量分布
"""),
    code("""
analysis.buy_mount_stats(trade)
"""),
    code("""
show(visualize.plot_buy_mount_dist(trade))
show(visualize.plot_bulk_by_cat(analysis.bulk_by_category(trade)))
"""),
    md("""
### 5.2 异常订单识别（本项目最重要的数据质量发现）

购买量最大值达到 10,000 件，明显不属于正常消费行为。需要量化它对整体指标的影响。
"""),
    code("""
top_orders = analysis.outlier_orders(trade, 10)
top_orders
"""),
    code("""
impact = analysis.outlier_impact(trade, 10)
show(visualize.plot_outliers(top_orders, analysis.long_tail_curve(trade)))
impact
"""),
    md("""
**结论**：单笔最大 10,000 件（童装/童鞋），一笔即占全部件数的 **13.1%**；Top10 大单合计占 **27.5%**。

- 剔除 Top10 大单后，平均单笔件数从 **2.54 件 → 1.85 件**
- 这类订单更可能是批发或非真实消费行为
- 建议核心 KPI 改用**订单数 / 用户数**为主口径
"""),

    md("""
---

## 6. 宝宝画像与品类偏好
"""),
    code("""
show(visualize.plot_baby_profile(analysis.baby_birth_year(baby), baby))
"""),
    code("""
lift = analysis.age_category_correlation(user_profile)
counts = analysis.age_stage_preference(user_profile)
show(visualize.plot_age_category(lift, counts))
lift
"""),
    md("""
**结论**：月龄是有效的偏好维度 —— 7–12 月龄的玩具偏好指数达 2.85，
0–6 月龄的洗护偏好指数达 2.70，6 岁以上仍可推成长奶粉（1.49）。
"""),
    md("""
### 6.1 性别与品类偏好：卡方独立性检验
"""),
    code("""
trade_with_baby = trade.merge(
    baby[["user_id", "gender", "gender_name"]], on="user_id", how="inner")

ct, chi2_res = analysis.gender_category_test(trade_with_baby)
show(visualize.plot_gender_category(ct, chi2_res))
chi2_res
"""),
    md("""
**结论：无显著差异**。p = 0.79（远大于 0.05），Cramér's V = 0.051（效应量接近 0）。

这是一个「没有差异」的结论，但它同样有价值：它直接否定了
**「按宝宝性别做差异化推荐」**这一运营假设，避免把资源投在无效维度上。
"""),

    md("""
---

## 7. 商品属性挖掘
"""),
    code("""
show(visualize.plot_property(
    analysis.property_value_diversity(pack["kv_detail"], pack["key_freq"]),
    trade,
))
analysis.property_stats(trade)
"""),
    md("""
属性键与取值均被平台脱敏，无法还原「品牌/尺码」等具体语义。
但**属性维度数**本身携带了「商品描述丰富度」这一信号，
并在后续建模中成为最重要的特征。
"""),

    md("""
---

## 8. 机器学习：囤货订单识别

### 8.1 为什么不做经典的「性别预测」？

天池该数据集最经典的赛题是用购买行为预测宝宝性别，但那需要**单个用户的多条记录**。
先实测一下这份数据能否支撑该任务。
"""),
    code("""
feasibility = modeling.evaluate_gender_feasibility(trade, baby)
feasibility
"""),
    md("""
实测 **ROC-AUC = 0.4931**，与随机猜测（0.5）无异，验证了前面的判断。
因此转向数据能够支撑的任务。

### 8.2 正式任务：预测订单是否会囤货（购买 ≥ 3 件）
"""),
    code("""
result = modeling.run_bulk_model(trade)
result["summary"]
"""),
    code("""
show(visualize.plot_model_results(result))
result["model_comparison"]
"""),
    code("""
result["report"]
"""),
    code("""
show(visualize.plot_feature_importance(result["importance"]))
result["importance"].head(10)
"""),
    md("""
**结论**：5 折交叉验证下 ROC-AUC = 0.778、PR-AUC = 0.210（随机基线 0.061，提升 3.4 倍）。

- 首要预测信号是**商品属性维度数**（重要性 0.304），即商品描述越丰富越可能是大包装
- 时间特征影响有限，说明囤货更多由「买什么」而非「什么时候买」决定
- 逻辑回归略优于随机森林，最终选择更简单、更可解释的模型
"""),

    md("""
---

## 9. 小结

| 分析方向 | 核心结论 |
| :--- | :--- |
| 时间维度 | 2014 年件数同比 +19.9%；双11 拉动 5.19 倍；618 无拉动；11 月占全年约 31% |
| 品类结构 | 尿裤/湿巾贡献 37.4% 件数（单笔 4.1 件）；奶粉贡献 41.7% 笔数（单笔 1.5 件）；CR10 = 44.5% |
| 购买量 | 87.9% 订单只买 1 件，极端长尾（偏度 133） |
| 异常识别 | 0.03% 订单贡献 27.5% 件数，最大单笔 10,000 件 |
| 宝宝画像 | 月龄显著影响品类偏好；性别无显著影响（p=0.79） |
| 机器学习 | 囤货预测 ROC-AUC 0.778、PR-AUC 0.210 |

**完整图表与报告**：见 `reports/report.html`
"""),
]


def main():
    nb = nbf.v4.new_notebook(cells=CELLS)
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.13"},
    }
    nbf.write(nb, str(OUT))
    print(f"已生成：{OUT}")


if __name__ == "__main__":
    main()
