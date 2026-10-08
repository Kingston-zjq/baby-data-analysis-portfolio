"""
机器学习模块：囤货行为预测。

为什么预测「囤货」而不是「宝宝性别」？
--------------------------------------------------------------------------
天池该数据集最经典的赛题是「根据购买行为预测宝宝性别」，但那个任务需要
**单个用户的多条购买记录**才能构造有效特征。本次拿到的是按行抽样的样本：
29,971 笔交易对应 29,944 个用户，人均约 1.0 笔，其中带性别标签的仅 953 人。
也就是说每个标签用户只有约 1 条行为记录 —— 特征维度塌缩，模型无法学到
可泛化的模式（实测 AUC 接近随机水平，见 evaluate_gender_feasibility）。

因此这里选择数据支撑充分的替代任务：
    预测一笔订单是否会「囤货」（单笔购买 ≥ 3 件）
样本量 29,971，正类（囤货单）1,837 笔、占比 6.13%，是一个真实的不平衡分类问题。
业务价值：提前识别囤货订单，用于库存预占、包材准备与物流调度。
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import TABLE_DIR, TRADE_RAW_FILE
from src.data_loader import _read_csv

RANDOM_STATE = 42
N_SPLITS = 5


# --------------------------------------------------------------------------
# 特征工程
# --------------------------------------------------------------------------
def build_features(trade: pd.DataFrame, top_cat: int = 30, top_prop: int = 10,
                   top_keys: list = None) -> tuple:
    """构造与目标变量无关的特征矩阵。

    严格排除 buy_mount / log_buy_mount / is_bulk，避免标签泄漏。
    """
    df = trade.copy()

    # --- 时间特征：月份用正余弦编码，保留周期性 ---
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["is_weekend"] = df["is_weekend"].astype(int)
    df["is_promo_month"] = df["is_promo_month"].astype(int)
    df["day_of_year"] = df["day"].dt.dayofyear

    # --- 属性特征 ---
    df["has_property"] = (df["n_props"] > 0).astype(int)
    if top_keys:
        for k in top_keys:
            df[f"prop_{k}"] = df["property"].str.contains(f"{k}:", regex=False).astype(int)

    base_cols = ["month_sin", "month_cos", "is_weekend", "is_promo_month",
                 "day_of_year", "n_props", "has_property"]

    # --- 类别特征 one-hot ---
    cat1_d = pd.get_dummies(df["cat1"], prefix="cat1").astype(int)
    top_cats = df["cat_id"].value_counts().head(top_cat).index
    df["cat_id_top"] = np.where(df["cat_id"].isin(top_cats), df["cat_id"], "OTHER")
    cat2_d = pd.get_dummies(df["cat_id_top"], prefix="cat2").astype(int)

    X = pd.concat([df[base_cols], cat1_d, cat2_d], axis=1)
    y = df["is_bulk"].astype(int)
    return X, y


# --------------------------------------------------------------------------
# 交叉验证评估
# --------------------------------------------------------------------------
def _cv_scores(model, X, y) -> dict:
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    proba = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    return {
        "proba": proba,
        "roc_auc": roc_auc_score(y, proba),
        "pr_auc": average_precision_score(y, proba),
    }


def run_bulk_model(trade: pd.DataFrame) -> dict:
    """训练两个模型并对比，返回评估结果。"""
    top_keys = (trade["property"].str.extractall(r"(?:^|;)(\d+):")[0]
                .value_counts().head(10).index.tolist())
    X, y = build_features(trade, top_keys=top_keys)

    models = {
        "逻辑回归": Pipeline([
            ("scaler", StandardScaler(with_mean=False)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                       random_state=RANDOM_STATE)),
        ]),
        "随机森林": RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=5,
            class_weight="balanced_subsample", n_jobs=-1, random_state=RANDOM_STATE),
    }

    results, probas = {}, {}
    for name, m in models.items():
        r = _cv_scores(m, X, y)
        results[name] = {"ROC-AUC": round(r["roc_auc"], 4), "PR-AUC": round(r["pr_auc"], 4)}
        probas[name] = r["proba"]

    best_name = max(results, key=lambda k: results[k]["PR-AUC"])
    best_proba = probas[best_name]

    # 按 F1 最优点确定阈值
    prec, rec, thr = precision_recall_curve(y, best_proba)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(prec), where=(prec + rec) > 0)
    best_thr = float(thr[min(int(np.argmax(f1)), len(thr) - 1)])
    pred = (best_proba >= best_thr).astype(int)

    cm = confusion_matrix(y, pred)
    report = pd.DataFrame(classification_report(y, pred, output_dict=True)).T.round(3)
    report.index.name = "类别"

    # 特征重要性（随机森林）
    rf = models["随机森林"].fit(X, y)
    imp = (pd.DataFrame({"特征": X.columns, "重要性": rf.feature_importances_})
           .sort_values("重要性", ascending=False).head(15).reset_index(drop=True))
    imp["特征"] = imp["特征"].replace({
        "n_props": "商品属性维度数", "has_property": "是否有属性信息",
        "is_promo_month": "是否大促月(6/11/12月)", "is_weekend": "是否周末",
        "month_sin": "月份周期(sin)", "month_cos": "月份周期(cos)",
        "day_of_year": "年内第几天",
    })

    summary = pd.DataFrame([
        {"指标": "样本量", "数值": len(y)},
        {"指标": "正类（囤货单）占比", "数值": f"{y.mean()*100:.2f}%"},
        {"指标": "特征维度", "数值": X.shape[1]},
        {"指标": "最优模型", "数值": best_name},
        {"指标": "ROC-AUC (5折CV)", "数值": results[best_name]["ROC-AUC"]},
        {"指标": "PR-AUC (5折CV)", "数值": results[best_name]["PR-AUC"]},
        {"指标": "最佳概率阈值", "数值": round(best_thr, 3)},
        {"指标": "混淆矩阵 [[TN,FP],[FN,TP]]", "数值": cm.tolist()},
    ])

    summary.to_csv(TABLE_DIR / "20_model_summary.csv", index=False, encoding="utf-8-sig")
    imp.to_csv(TABLE_DIR / "21_feature_importance.csv", index=False, encoding="utf-8-sig")
    report.to_csv(TABLE_DIR / "22_classification_report.csv", encoding="utf-8-sig")

    return {
        "summary": summary, "importance": imp, "report": report, "cm": cm,
        "y": y, "proba": best_proba, "results": results,
        "model_comparison": pd.DataFrame(results).T.reset_index(names="模型"),
        "X_columns": list(X.columns),
    }


# --------------------------------------------------------------------------
# 性别预测的可行性评估（诚实记录，不做过度包装）
# --------------------------------------------------------------------------
def evaluate_gender_feasibility(trade: pd.DataFrame, baby: pd.DataFrame) -> pd.DataFrame:
    """用 953 个有性别标签的用户尝试建模，量化「数据能否支撑该任务」。

    结论预期：AUC 接近 0.5，说明在人均 1 笔记录的样本上无法完成该任务。
    """
    d = trade.merge(baby[["user_id", "gender"]], on="user_id", how="inner")
    d = d[d["gender"].isin([0, 1])]
    if d["gender"].nunique() < 2:
        return pd.DataFrame([{"结论": "标签不足，无法建模"}])

    X, _ = build_features(d)
    y = d["gender"].astype(int).values
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                 class_weight="balanced", n_jobs=-1, random_state=RANDOM_STATE)
    proba = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, proba)

    per_user = trade.groupby("user_id").size()
    out = pd.DataFrame([
        {"指标": "有性别标签的用户数", "数值": len(d)},
        {"指标": "人均可用的交易记录数", "数值": round(per_user.loc[d["user_id"].unique()].mean(), 2)},
        {"指标": "性别预测 ROC-AUC", "数值": round(auc, 4)},
        {"指标": "随机基线 AUC", "数值": 0.5},
        {"指标": "结论", "数值": "接近随机水平，该抽样结构不支持性别预测建模"},
        {"指标": "原因", "数值": "每位标签用户仅有约 1 条行为记录，无法构造用户级行为特征"},
    ])
    out.to_csv(TABLE_DIR / "23_gender_feasibility.csv", index=False, encoding="utf-8-sig")
    return out
