"""
一键跑完整个分析流程。

用法（在项目根目录执行）：
    python scripts/run_all.py

流程：加载 → 质量体检 → 清洗与特征 → 业务指标 → 绘图 → 建模 → 落盘
"""

import sys
import time
import warnings
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")

from src import analysis, data_loader, modeling, preprocess, visualize  # noqa: E402
from src.config import TABLE_DIR  # noqa: E402


def banner(text: str):
    print(f"\n{'=' * 68}\n  {text}\n{'=' * 68}")


def main():
    t0 = time.time()

    banner("STEP 1 / 6  加载原始数据")
    trade_raw = data_loader.load_trade()
    baby_raw = data_loader.load_baby()
    print(f"  交易明细  {trade_raw.shape[0]:,} 行 × {trade_raw.shape[1]} 列")
    print(f"  宝宝信息  {baby_raw.shape[0]:,} 行 × {baby_raw.shape[1]} 列")

    banner("STEP 2 / 6  数据质量体检")
    qr = data_loader.quality_report(trade_raw, baby_raw)
    qr.to_csv(TABLE_DIR / "00_quality_report.csv", index=False, encoding="utf-8-sig")
    print(qr.to_string(index=False, max_colwidth=40))

    banner("STEP 3 / 6  清洗与特征工程")
    pack = preprocess.run(trade_raw, baby_raw)
    trade, baby = pack["trade"], pack["baby"]
    user_profile = pack["user_profile"]
    print(f"  清洗后交易    {len(trade):,} 行")
    print(f"  宝宝档案      {len(baby):,} 行")
    print(f"  用户画像      {len(user_profile):,} 行（有档案且能对齐交易）")

    banner("STEP 4 / 6  业务指标计算")
    trade_with_baby = trade.merge(
        baby[["user_id", "gender", "gender_name"]], on="user_id", how="inner")
    res = analysis.run_all(trade, baby, pack["kv_detail"], pack["key_freq"],
                           user_profile, trade_with_baby)
    for key in ("overview", "concentration", "promo", "buy_mount"):
        print(f"\n  [{key}]\n{res[key].to_string(index=False)}")

    banner("STEP 5 / 6  生成图表")
    figs = []
    figs.append(visualize.plot_monthly_trend(res["monthly"]))
    figs.append(visualize.plot_year_compare(trade))
    figs.append(visualize.plot_seasonality(
        analysis.monthly_share_by_year(trade)))
    figs.append(visualize.plot_weekday(res["weekday"]))
    figs.append(visualize.plot_promo(res["promo"]))
    figs.append(visualize.plot_cat1_share(res["cat1"]))
    figs.append(visualize.plot_pareto(res["pareto"]))
    figs.append(visualize.plot_buy_mount_dist(trade))
    figs.append(visualize.plot_bulk_by_cat(res["bulk_cat"]))
    figs.append(visualize.plot_outliers(res["outliers"], res["long_tail"]))
    figs.append(visualize.plot_baby_profile(res["baby_year"], baby))
    figs.append(visualize.plot_property(res["prop_div"], trade))

    ct, gender_res = analysis.gender_category_test(trade_with_baby)
    if not ct.empty:
        analysis.save_table(
            ct.reset_index().rename(columns={"cat1_name": "品类"}), "15_gender_crosstab")
        analysis.save_table(gender_res, "16_gender_chi2")
        f = visualize.plot_gender_category(ct, gender_res)
        if f:
            figs.append(f)
        print(f"\n  [性别 × 品类 卡方检验]\n{gender_res.to_string(index=False)}")

    lift = analysis.age_category_correlation(user_profile)
    counts = analysis.age_stage_preference(user_profile)
    if not lift.empty:
        analysis.save_table(lift.reset_index().rename(columns={"age_stage": "月龄段"}),
                            "17_age_category_lift")
        f = visualize.plot_age_category(lift, counts)
        if f:
            figs.append(f)

    print(f"\n  已生成 {len(figs)} 张图表 -> reports/figures/")

    banner("STEP 6 / 6  建模")
    model_res = modeling.run_bulk_model(trade)
    print(f"\n  [囤货预测建模]\n{model_res['summary'].to_string(index=False)}")
    print(f"\n  [模型对比]\n{model_res['model_comparison'].to_string(index=False)}")
    print(f"\n  [特征重要性 Top10]\n{model_res['importance'].head(10).to_string(index=False)}")
    figs.append(visualize.plot_model_results(model_res))
    figs.append(visualize.plot_feature_importance(model_res["importance"]))

    feas = modeling.evaluate_gender_feasibility(trade, baby)
    print(f"\n  [性别预测可行性评估]\n{feas.to_string(index=False)}")

    banner("附加检查  繁简字一致性")
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_chinese.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    # 只打印结论行，避免刷屏
    for line in rc.stdout.splitlines():
        if "✅" in line or "❌" in line:
            print(f"  {line.strip()}")
    if rc.returncode != 0:
        print("  ⚠️  检测到繁体字，请运行 python scripts/check_chinese.py 查看详情")

    # notebook 内嵌图片会让文件膨胀到 GitHub 无法渲染，每次生成后必须压缩
    nb = ROOT / "notebooks" / "mum_baby_analysis.ipynb"
    if nb.exists():
        banner("附加步骤  压缩 notebook（保证 GitHub 可渲染）")
        rc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "optimize_notebook.py")],
            capture_output=True, text=True, cwd=ROOT,
        )
        print("  " + (rc.stdout.strip() or rc.stderr.strip()).replace("\n", "\n  "))

    print(f"\n完成，总耗时 {time.time() - t0:.1f}s")
    print(f"图表目录：{ROOT / 'reports' / 'figures'}")
    print(f"数据表目录：{ROOT / 'reports' / 'tables'}")


if __name__ == "__main__":
    main()
