"""
数据清洗与特征工程。

产出三张可直接用于分析的表：
  trade_clean   交易明细 + 时间特征 + 商品属性特征
  baby_clean    宝宝信息（含出生年份、性别中文名）
  user_profile  宝宝信息 ⋈ 该用户交易聚合（仅覆盖有宝宝档案的用户）
"""

import numpy as np
import pandas as pd

from src.config import (
    AGE_BINS,
    AGE_LABELS,
    CAT1_NAME,
    GENDER_NAME,
    TRADE_CLEAN_FILE,
    BABY_CLEAN_FILE,
    USER_PROFILE_FILE,
)

# 平台大促节点（月-日），用于量化大促效应
PROMO_DAYS = {
    (11, 11): "双11",
    (12, 12): "双12",
    (6, 18): "618",
    (1, 1): "元旦",
    (10, 1): "国庆",
    (5, 1): "五一",
}

# 电商行业公认的大促月份（用于月度对比）
PROMO_MONTHS = {6, 11, 12}


# --------------------------------------------------------------------------
# 交易表清洗与特征
# --------------------------------------------------------------------------
def build_trade_features(trade: pd.DataFrame) -> pd.DataFrame:
    df = trade.copy()

    # --- 基础清洗 ---
    df = df.dropna(subset=["day"]).copy()
    df = df[df["buy_mount"] > 0].copy()
    df = df.drop_duplicates().reset_index(drop=True)

    # --- 时间特征 ---
    df["year"] = df["day"].dt.year
    df["month"] = df["day"].dt.month
    df["quarter"] = df["day"].dt.quarter
    df["weekday"] = df["day"].dt.weekday          # 0=周一
    df["weekday_name"] = df["day"].dt.dayofweek.map(
        {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    )
    df["is_weekend"] = df["weekday"] >= 5
    df["year_month"] = df["day"].dt.to_period("M").astype(str)
    df["ym_index"] = df["day"].dt.year * 12 + df["day"].dt.month

    # --- 大促标记 ---
    md = list(zip(df["month"], df["day"].dt.day))
    df["promo"] = [PROMO_DAYS.get(x, "无") for x in md]
    df["is_promo"] = df["promo"] != "无"
    df["is_promo_month"] = df["month"].isin(PROMO_MONTHS)

    # --- 品类 ---
    df["cat1_name"] = df["cat1"].map(CAT1_NAME).fillna("其他")

    # --- 购买量 ---
    df["log_buy_mount"] = np.log1p(df["buy_mount"])
    df["is_bulk"] = df["buy_mount"] >= 3          # 囤货行为
    df["is_single"] = df["buy_mount"] == 1

    return df


# --------------------------------------------------------------------------
# property 字段解析
# --------------------------------------------------------------------------
def parse_property(prop: str) -> dict:
    """把 "k1:v1;k2:v2" 解析为字典，并给出属性对数量。"""
    pairs = {}
    if not prop:
        return pairs
    for item in prop.split(";"):
        if not item or ":" not in item:
            continue
        k, v = item.split(":", 1)
        pairs[k] = v
    return pairs


def build_property_features(trade: pd.DataFrame) -> tuple:
    """生成 属性对数量 / 属性键出现次数 / 键-值明细 三份结果。"""
    df = trade.copy()
    df["prop_dict"] = df["property"].map(parse_property)
    df["n_props"] = df["prop_dict"].map(len)

    key_counter = {}
    kv_rows = []
    for cat1_name, d, bm in zip(df["cat1_name"], df["prop_dict"], df["buy_mount"]):
        for k, v in d.items():
            key_counter[k] = key_counter.get(k, 0) + 1
            kv_rows.append((k, v, cat1_name, bm))

    key_freq = (
        pd.DataFrame({"prop_key": list(key_counter.keys()),
                      "出现次数": list(key_counter.values())})
        .sort_values("出现次数", ascending=False)
        .reset_index(drop=True)
    )
    kv_detail = pd.DataFrame(kv_rows, columns=["prop_key", "prop_value", "cat1_name", "buy_mount"])
    return df, key_freq, kv_detail


# --------------------------------------------------------------------------
# 宝宝表清洗
# --------------------------------------------------------------------------
def build_baby_features(baby: pd.DataFrame) -> pd.DataFrame:
    df = baby.copy()
    df = df.dropna(subset=["birthday"]).copy()
    df["birth_year"] = df["birthday"].dt.year
    df["gender_name"] = df["gender"].map(GENDER_NAME).fillna("未知")
    # 剔除明显不合理的生日（早于 2000 年多为录入错误）
    df = df[(df["birth_year"] >= 2000)].reset_index(drop=True)
    return df


# --------------------------------------------------------------------------
# 用户画像：宝宝档案 ⋈ 交易行为
# --------------------------------------------------------------------------
def build_user_profile(trade_f: pd.DataFrame, baby_f: pd.DataFrame) -> pd.DataFrame:
    """仅保留同时拥有宝宝档案与交易记录的用户。"""
    t = trade_f[trade_f["user_id"].isin(set(baby_f["user_id"]))].copy()
    if t.empty:
        return pd.DataFrame()

    # 下单时宝宝的月龄
    merged = t.merge(baby_f[["user_id", "birthday", "gender", "gender_name"]], on="user_id", how="left")
    days = (merged["day"] - merged["birthday"]).dt.days
    merged["age_months"] = days / 30.44
    merged = merged[merged["age_months"] >= 0]          # 去掉购买时间早于出生的异常
    merged["age_stage"] = pd.cut(
        merged["age_months"], bins=AGE_BINS, labels=AGE_LABELS
    )

    # 用户级聚合
    agg = merged.groupby("user_id").agg(
        交易笔数=("auction_id", "count"),
        购买总件数=("buy_mount", "sum"),
        平均单笔件数=("buy_mount", "mean"),
        覆盖品类数=("cat1_name", "nunique"),
        首次购买=("day", "min"),
        最近购买=("day", "max"),
        平均月龄=("age_months", "mean"),
    ).reset_index()

    # 主营品类（该用户交易最多的品类）
    top_cat = (
        merged.groupby(["user_id", "cat1_name"]).size().reset_index(name="cnt")
        .sort_values("cnt", ascending=False)
        .drop_duplicates("user_id")[["user_id", "cat1_name"]]
        .rename(columns={"cat1_name": "主营品类"})
    )
    agg = agg.merge(top_cat, on="user_id", how="left")
    agg = agg.merge(
        baby_f[["user_id", "gender", "gender_name", "birth_year"]], on="user_id", how="left"
    )
    # 用户所属月龄段：以该用户交易时的平均月龄归档
    agg["月龄段"] = pd.cut(agg["平均月龄"], bins=AGE_BINS, labels=AGE_LABELS)
    agg = agg.rename(columns={"月龄段": "age_stage"})
    return agg


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def run(trade_raw: pd.DataFrame, baby_raw: pd.DataFrame) -> dict:
    trade_f = build_trade_features(trade_raw)
    baby_f = build_baby_features(baby_raw)
    trade_f, key_freq, kv_detail = build_property_features(trade_f)
    user_profile = build_user_profile(trade_f, baby_f)

    # 落盘（去掉不可序列化的 dict 列）
    trade_f.drop(columns=["prop_dict"]).to_csv(TRADE_CLEAN_FILE, index=False, encoding="utf-8-sig")
    baby_f.to_csv(BABY_CLEAN_FILE, index=False, encoding="utf-8-sig")
    if not user_profile.empty:
        user_profile.to_csv(USER_PROFILE_FILE, index=False, encoding="utf-8-sig")

    return {
        "trade": trade_f,
        "baby": baby_f,
        "key_freq": key_freq,
        "kv_detail": kv_detail,
        "user_profile": user_profile,
    }
