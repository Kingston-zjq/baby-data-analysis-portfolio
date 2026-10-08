"""
数据加载与基础校验。

对外提供 load_trade() / load_baby()，负责：
  1. 读取原始 CSV
  2. 统一字段类型（日期、数值）
  3. 做基础的质量检查并返回一份体检报告
"""

import pandas as pd

from src.config import BABY_RAW_FILE, TRADE_RAW_FILE


def _read_csv(path) -> pd.DataFrame:
    """兼容中英文编码的 CSV 读取。"""
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="utf-8", errors="replace")


def load_trade(path=TRADE_RAW_FILE) -> pd.DataFrame:
    """加载交易明细表并规范类型。

    原始字段：
        user_id      用户 ID
        auction_id   商品（交易）ID
        cat_id       二级品类 ID
        cat1         一级品类 ID
        property     商品属性串，形如 "1628665:29790;21458:30992"
        buy_mount    购买数量
        day          购买日期，形如 20140919
    """
    df = _read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    df["user_id"] = df["user_id"].astype("int64")
    df["auction_id"] = df["auction_id"].astype("int64")
    df["buy_mount"] = pd.to_numeric(df["buy_mount"], errors="coerce").fillna(0).astype("int64")
    df["cat_id"] = df["cat_id"].astype(str)
    df["cat1"] = df["cat1"].astype(str)
    df["property"] = df["property"].fillna("")

    # day: 20140919 -> datetime
    df["day"] = pd.to_datetime(df["day"].astype(str), format="%Y%m%d", errors="coerce")
    return df


def load_baby(path=BABY_RAW_FILE) -> pd.DataFrame:
    """加载宝宝信息表并规范类型。

    原始字段：
        user_id    用户 ID
        birthday   宝宝生日，形如 20130311
        gender     0=女宝 1=男宝 2=未知（天池官方 Overview 说明，详见 src/config.py）
    """
    df = _read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    df["user_id"] = df["user_id"].astype("int64")
    df["birthday"] = pd.to_datetime(df["birthday"].astype(str), format="%Y%m%d", errors="coerce")
    df["gender"] = pd.to_numeric(df["gender"], errors="coerce").fillna(2).astype("int64")
    return df


def quality_report(trade: pd.DataFrame, baby: pd.DataFrame) -> pd.DataFrame:
    """生成数据质量体检表，输出到 reports/tables。"""
    rows = []

    def add(name, value, note=""):
        rows.append({"检查项": name, "结果": value, "说明": note})

    add("交易表行数", len(trade))
    add("交易表用户数", trade["user_id"].nunique())
    add("交易表商品数", trade["auction_id"].nunique())
    add("交易表时间跨度", f"{trade['day'].min():%Y-%m-%d} ~ {trade['day'].max():%Y-%m-%d}")
    add("交易表日期缺失", int(trade["day"].isna().sum()))
    add("交易表属性为空", int((trade["property"] == "").sum()), "property 字段无内容")
    add("交易表购买量异常(<=0)", int((trade["buy_mount"] <= 0).sum()))
    add("宝宝表行数", len(baby))
    add("宝宝表生日缺失", int(baby["birthday"].isna().sum()))
    add("宝宝表性别分布",
        " / ".join(f"{k}:{v}" for k, v in baby["gender"].value_counts().sort_index().items()),
        "0=女宝 1=男宝 2=未知（天池官方说明）")
    add("宝宝表生日异常(早于2000年)", int((baby["birthday"].dt.year < 2000).sum()))

    # 复购结构——决定本项目能做哪些用户级分析
    per_user = trade.groupby("user_id").size()
    add("人均交易笔数", round(per_user.mean(), 4))
    add("有复购的用户数", int((per_user > 1).sum()), "该样本按行抽样，复购用户极少")

    return pd.DataFrame(rows)
