"""
生成自包含的分析报告 reports/report.html。

特点：
  - 所有图表以 base64 内嵌，单文件可直接打开、便于分享
  - 表格数据实时从 reports/tables/*.csv 读取，保证与脚本结果一致
  - 浅色主题，适配 GitHub / 浏览器 / 打印
"""

import base64
import html
from datetime import date
from pathlib import Path

import pandas as pd

from src.config import FIGURE_DIR, REPORT_DIR, TABLE_DIR


# --------------------------------------------------------------------------
# 读取与渲染工具
# --------------------------------------------------------------------------
def _img(name: str, caption: str = "") -> str:
    path = FIGURE_DIR / name
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    cap = f'<figcaption>{html.escape(caption)}</figcaption>' if caption else ""
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(caption)}">{cap}</figure>'


def _table(csv_name: str, title: str = "", max_rows: int = 30,
           highlight: str = None) -> str:
    path = TABLE_DIR / csv_name
    if not path.exists():
        return ""
    df = pd.read_csv(path, encoding="utf-8-sig")
    head = f"<h4>{html.escape(title)}</h4>" if title else ""
    cls = "table table-sm" if max_rows and len(df) > 8 else "table"
    body = df.head(max_rows).to_html(index=False, classes=cls, border=0,
                                     escape=False, justify="left")
    return f'<div class="table-wrap">{head}{body}</div>'


def _kpi(value: str, label: str, hint: str = "") -> str:
    h = f'<span class="kpi-hint">{html.escape(hint)}</span>' if hint else ""
    return (f'<div class="kpi"><div class="kpi-value">{html.escape(str(value))}</div>'
            f'<div class="kpi-label">{html.escape(label)}</div>{h}</div>')


def _finding(icon: str, title: str, body: str) -> str:
    return (f'<div class="finding"><div class="finding-head">{icon}'
            f'<span>{title}</span></div><p>{body}</p></div>')


def _section(sid: str, num: str, title: str, subtitle: str, content: str) -> str:
    return (f'<section id="{sid}"><h2><span class="sec-num">{num}</span>{title}</h2>'
            f'<p class="sec-sub">{subtitle}</p>{content}</section>')


# --------------------------------------------------------------------------
# 主构建函数
# --------------------------------------------------------------------------
CSS = """
:root{
  --primary:#4C7DF0; --accent:#FF7A9C; --teal:#3DC7A0; --amber:#FFB020;
  --ink:#1F2A37; --ink2:#4B5563; --muted:#8C9BAB; --line:#E6EAF0;
  --bg:#F7F9FC; --card:#FFFFFF;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"Microsoft YaHei","PingFang SC","Hiragino Sans GB","Segoe UI",Roboto,sans-serif;
  line-height:1.75; font-size:15px;
}
.wrap{max-width:1120px;margin:0 auto;padding:0 28px 80px;}
header.hero{
  background:linear-gradient(120deg,#4C7DF0 0%,#6E8CF5 45%,#FF9EB5 100%);
  color:#fff;padding:56px 28px 48px;margin-bottom:34px;
}
header.hero .inner{max-width:1120px;margin:0 auto;}
header.hero h1{margin:0 0 12px;font-size:34px;letter-spacing:.5px;line-height:1.3;}
header.hero p.sub{margin:0;font-size:16px;opacity:.94;max-width:760px;}
.chips{margin-top:22px;display:flex;flex-wrap:wrap;gap:10px;}
.chip{background:rgba(255,255,255,.20);border:1px solid rgba(255,255,255,.42);
  border-radius:999px;padding:5px 14px;font-size:13px;}
h2{font-size:23px;margin:52px 0 6px;padding-bottom:12px;border-bottom:2px solid var(--line);
  display:flex;align-items:center;gap:12px;}
.sec-num{display:inline-flex;align-items:center;justify-content:center;
  min-width:34px;height:34px;border-radius:10px;background:var(--primary);color:#fff;
  font-size:15px;font-weight:700;}
.sec-sub{color:var(--ink2);margin:0 0 22px;font-size:14.5px;}
h3{font-size:17.5px;margin:32px 0 12px;color:var(--ink);}
h3::before{content:"";display:inline-block;width:4px;height:16px;background:var(--accent);
  border-radius:2px;margin-right:9px;vertical-align:-2px;}
h4{font-size:14.5px;margin:18px 0 8px;color:var(--ink2);}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:16px;margin:26px 0 10px;}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;
  box-shadow:0 1px 3px rgba(31,42,55,.04);}
.kpi-value{font-size:26px;font-weight:700;color:var(--primary);letter-spacing:.4px;}
.kpi-label{font-size:13.5px;color:var(--ink2);margin-top:4px;}
.kpi-hint{display:block;font-size:12px;color:var(--muted);margin-top:6px;}
figure{margin:26px 0;background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:16px;box-shadow:0 1px 3px rgba(31,42,55,.04);}
figure img{width:100%;display:block;border-radius:8px;}
figcaption{font-size:13px;color:var(--muted);margin-top:10px;text-align:center;}
.findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:24px 0;}
.finding{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:12px;padding:16px 18px;}
.finding-head{font-weight:700;font-size:15px;margin-bottom:6px;display:flex;align-items:center;gap:8px;}
.finding p{margin:0;font-size:14px;color:var(--ink2);}
.table-wrap{overflow-x:auto;margin:20px 0;background:var(--card);border:1px solid var(--line);
  border-radius:12px;padding:14px 16px;}
table{border-collapse:collapse;width:100%;font-size:13.5px;}
table thead th{background:#EEF3FE;color:#25406B;font-weight:700;text-align:left;
  padding:9px 12px;border-bottom:2px solid #D8E3F8;white-space:nowrap;}
table td{padding:8px 12px;border-bottom:1px solid var(--line);color:var(--ink2);white-space:nowrap;}
table tbody tr:last-child td{border-bottom:none;}
table tbody tr:hover{background:#FAFCFF;}
.callout{background:#FFF8E1;border:1px solid #FFE8A3;border-left:4px solid var(--amber);
  border-radius:12px;padding:16px 20px;margin:22px 0;font-size:14.5px;color:#7A5B10;}
.callout strong{color:#5C4409;}
.note{background:#EEF7F3;border:1px solid #CBE9DD;border-left:4px solid var(--teal);
  border-radius:12px;padding:16px 20px;margin:22px 0;font-size:14.5px;color:#1E5F49;}
ol.steps{padding-left:22px;}
ol.steps li{margin-bottom:7px;color:var(--ink2);}
code{background:#EEF1F6;padding:2px 7px;border-radius:5px;font-size:13px;
  font-family:Consolas,Monaco,"Courier New",monospace;color:#2C5282;}
pre{background:#1E2A3A;color:#E6EDF3;padding:16px 18px;border-radius:12px;overflow-x:auto;
  font-size:13px;font-family:Consolas,Monaco,"Courier New",monospace;line-height:1.6;}
footer{margin-top:60px;padding-top:24px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px;text-align:center;}
.toc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 24px;
  margin:30px 0;}
.toc h4{margin:0 0 12px;color:var(--ink);}
.toc ol{margin:0;padding-left:20px;columns:2;column-gap:34px;}
.toc li{margin-bottom:6px;}
.toc a{color:var(--primary);text-decoration:none;}
.toc a:hover{text-decoration:underline;}
@media print{header.hero{background:#4C7DF0;} figure{break-inside:avoid;} h2{break-after:avoid;}}
"""


def build() -> Path:
    today = date.today().strftime("%Y-%m-%d")

    # ---- 头部 ----
    head = f"""
<header class="hero"><div class="inner">
  <h1>母婴电商购物行为数据分析</h1>
  <p class="sub">基于阿里天池「淘宝母婴购物数据集」的端到端分析：从数据质量体检、生意节奏、品类结构，
  到异常订单识别与囤货行为预测模型，输出可落地的运营建议。</p>
  <div class="chips">
    <span class="chip">交易记录 29,971 条</span>
    <span class="chip">时间跨度 2012.07 – 2015.02</span>
    <span class="chip">Python · pandas · scikit-learn</span>
    <span class="chip">报告生成于 {today}</span>
  </div>
</div></header>
"""

    toc = """
<div class="toc"><h4>目录</h4><ol>
<li><a href="#s1">数据说明与质量体检</a></li>
<li><a href="#s2">生意节奏：时间维度分析</a></li>
<li><a href="#s3">卖什么：品类结构分析</a></li>
<li><a href="#s4">怎么买：购买量分布与异常订单识别</a></li>
<li><a href="#s5">谁在买：宝宝画像与品类偏好</a></li>
<li><a href="#s6">商品属性挖掘</a></li>
<li><a href="#s7">囤货订单识别模型</a></li>
<li><a href="#s8">结论与运营建议</a></li>
<li><a href="#s9">局限性说明与后续计划</a></li>
<li><a href="#s10">项目复现方式</a></li>
</ol></div>
"""

    # ---- 核心结论 ----
    findings = f"""
<h3>核心结论速览</h3>
<div class="findings">
{_finding("🔴", "双11 是唯一的强爆发点，拉动 5.2 倍",
          "11 月 11 日当日件数达到平日的 5.19 倍，且 2013、2014 两年 11 月均占全年件数的 30% 左右，规律稳定可复用。"
          "反观 618 仅 0.64 倍，说明在当时的淘系母婴品类中并不成立——结论不能照搬其他平台的常识。")}
{_finding("📦", "复购由品类驱动，尿裤与奶粉是两大命脉",
          "尿裤/湿巾与奶粉/辅食合计贡献 62% 的件数、65% 的笔数，但两者的购买逻辑完全不同："
          "尿裤单笔 4.1 件属囤货型，奶粉单笔 1.5 件属高频补货型，运营策略应区别设计。")}
{_finding("⚠️", "0.03% 的订单贡献了 27.5% 的件数",
          "单笔最高达 10,000 件（童装/童鞋），一笔即占全部件数的 13.1%。这类订单更可能是批发或非真实消费，"
          "若不在分析前剥离，会显著拉高所有「平均值」类指标——本报告已做剔除对照。")}
{_finding("🔍", "性别与品类偏好在本样本中无显著关联",
          "卡方检验 p=0.79、Cramér's V=0.05，无法拒绝独立性假设。这是一个「没有差异」的结论，"
          "但它说明：基于性别的差异化推荐在本数据上缺乏依据，不宜作为运营抓手。")}
{_finding("🤖", "囤货行为可被有效预测（PR-AUC 0.21 vs 随机 0.06）",
          "逻辑回归在 5 折交叉验证下 ROC-AUC 达 0.778，PR-AUC 是随机基线的 3.4 倍。"
          "首要预测信号是「商品属性维度数」与品类，时间因素影响较弱。")}
{_finding("🧭", "先质疑数据，再下结论",
          "人均仅 1.0 笔交易的样本结构决定了「用户生命周期/RFM/性别预测」不可能成立（实测 AUC 0.493，等同随机）。"
          "识别出「哪些分析做不了」，和做出分析同样重要。")}
</div>
"""

    # ---- 1 数据说明 ----
    s1 = _section("s1", "01", "数据说明与质量体检",
                  "在动手分析前，先确认数据能回答什么问题、不能回答什么问题。",
                  f"""
<div class="kpis">
{_kpi("29,971", "交易记录", "清洗后有效记录")}
{_kpi("76,250", "购买总件数", "含大额异常单")}
{_kpi("29,944", "覆盖用户", "人均 1.0009 笔")}
{_kpi("662", "二级类目", "归属 6 个一级类目")}
{_kpi("953", "有宝宝档案用户", "占交易用户 3.2%")}
{_kpi("2012.07–2015.02", "时间跨度", "完整年度仅 2013、2014")}
</div>

<h3>1.1 数据质量体检结果</h3>
{_table("00_quality_report.csv", "")}

<div class="callout">
<strong>关键结构判断：</strong>29,971 笔交易对应 29,944 个用户，人均 1.0009 笔、仅 25 个用户存在复购。
这说明拿到的是一份<strong>按行随机抽样的样本</strong>，而非完整的用户行为序列。
因此本项目<strong>主动放弃</strong>了用户生命周期、RFM 分层、复购周期、性别预测等依赖「单用户多记录」的分析，
把重心放在交易、品类、时间、商品属性与宝宝画像这些样本能够支撑的方向上。
</div>

<h3>1.2 数据字段与口径</h3>
{_table("01_overview.csv", "规模概览")}

<div class="note">
<strong>需要说明的两处口径：</strong><br>
① <code>gender</code> 编码依天池官方 Overview 说明为 0=女宝、1=男宝、2=未知；
部分中文二手资料编码相反。<strong>本报告所有性别相关结论均做对称表述，不依赖该映射方向。</strong><br>
② 一级类目中文名依据社区整理的类目对照表，该对照表未包含在本次样本中；
所有图表均同时标注原始编码（如 <code>28</code>、<code>50008168</code>），便于核对。
</div>
""")

    # ---- 2 时间 ----
    s2 = _section("s2", "02", "生意节奏：时间维度分析",
                  "回答三件事：生意在增长吗？一年中什么时候最好卖？大促到底能拉动多少？",
                  f"""
<h3>2.1 整体趋势</h3>
{_img("fig01_monthly_trend.png", "图 2-1 月度交易趋势（2012.07–2015.02）")}
{_img("fig13_year_compare.png", "图 2-2 完整年度对比：2014 年购买件数同比增长 19.9%")}

<h3>2.2 季节性规律</h3>
{_img("fig02_seasonality.png", "图 2-3 年内月度销量分布（仅统计数据完整的 2013–2014 年）")}

<div class="findings">
{_finding("📈", "稳定增长", "2014 年购买件数同比 +19.9%，交易笔数同比增长，处于典型的行业扩张期。")}
{_finding("🗓️", "双峰结构", "两个完整年度的曲线形态高度一致：11–12 月为大促峰（约 31% + 20%），6 月为次高峰，2 月为全年低谷（春节效应）。")}
</div>

<h3>2.3 大促拉动效果</h3>
{_img("fig04_promo_effect.png", "图 2-4 各电商大促节点对销量的拉动倍数")}
{_table("04_promo_effect.csv", "大促效应量化")}

<div class="callout">
<strong>一个反直觉的发现：</strong>618 的拉动倍数只有 0.64（低于平日），而双12 也有 2.26 倍。
这说明在 2012–2014 年的淘系母婴品类中，618 尚未形成大促心智——该时期 618 是竞对平台的主场。
<strong>做数据分析不能直接套用「618 是大促」的行业常识，必须用数据验证。</strong>
</div>

<h3>2.4 周内节律与高峰单日</h3>
{_img("fig03_weekday.png", "图 2-5 一周内的下单分布")}
{_table("05_top_days.csv", "购买件数 Top10 单日")}
""")

    # ---- 3 品类 ----
    s3 = _section("s3", "03", "卖什么：品类结构分析",
                  "从品类集中度与购买逻辑两个角度，判断商品结构是否健康。",
                  f"""
<h3>3.1 一级品类结构</h3>
{_img("fig05_cat1_share.png", "图 3-1 一级品类结构（件数口径 vs 笔数口径）")}
{_table("06_category_cat1.csv", "一级品类明细")}

<div class="findings">
{_finding("🍼", "奶粉/辅食：高频低量", "41.7% 的交易笔数、12,046 个商品，但单笔仅 1.5 件——典型的「高频补货 + 极度分散」的品类，是平台流量的基本盘。")}
{_finding("🧷", "尿裤/湿巾：低频高量", "笔数占比 23.2%，却贡献 37.4% 的件数，单笔高达 4.1 件——典型的囤货型品类，是平台 GMV 的压舱石。")}
{_finding("👗", "童装/童鞋：被低估的第二梯队", "件数占比 25.9%、笔数占比 16.1%，单笔 4.09 件，规模仅次于尿裤，通常容易被忽视。")}
</div>

<h3>3.2 二级类目集中度</h3>
{_img("fig06_pareto.png", "图 3-2 二级类目帕累托图（Top 30 / 共 662 个类目）")}
{_table("09_concentration.csv", "集中度指标")}

<div class="note">
<strong>集中度判读：</strong>CR10 = 44.5%、HHI = 394.8，属于<strong>中等集中度 + 长尾厚</strong>的市场结构。
头部没有绝对垄断品类，长尾的 662 个二级类目仍贡献了近半销量——这对平台意味着
<strong>类目运营不能只盯大单品，长尾选品的覆盖广度本身就是竞争力</strong>。
</div>
""")

    # ---- 4 购买量 ----
    s4 = _section("s4", "04", "怎么买：购买量分布与异常订单识别",
                  "购买量是理解「囤货 vs 即时消费」的核心，也是识别异常数据的最佳切入点。",
                  f"""
<h3>4.1 购买量分布</h3>
{_img("fig07_buy_mount_dist.png", "图 4-1 购买量分布（对数双轴）与 Top10 档位")}
{_table("10_buy_mount_stats.csv", "购买量描述统计")}

<div class="callout">
<strong>为什么中位数比均值更可信：</strong>购买量中位数 = 1 件、众数 = 1 件，而均值被拉到 2.54 件，
偏度高达 133、峰度 20,134。这是一条极端右偏的长尾分布，<strong>任何用均值描述「典型用户行为」的结论都会被少数大单扭曲</strong>。
</div>

<h3>4.2 各品类的囤货倾向</h3>
{_img("fig08_bulk_by_cat.png", "图 4-2 各品类平均单笔件数与囤货单占比")}
{_table("11_bulk_by_category.csv", "品类囤货指标")}

<div class="findings">
{_finding("🧷", "尿裤/湿巾 = 真囤货", "平均 4.1 件，8.47% 的订单一次买 ≥3 件，是唯一符合「囤货」直觉的品类。")}
{_finding("🧸", "玩具/童车 = 高囤货率", "28.0% 的订单买 ≥3 件（比例最高），但平均只有 3.05 件——多为整套/组合装购买，属于商品结构特征而非囤积行为。")}
{_finding("🍚", "奶粉 = 不囤货", "仅 2.64% 的订单买 ≥3 件，平均 1.5 件。奶粉单价高、保质期敏感，用户倾向少量多次购买。")}
</div>

<h3>4.3 异常订单识别</h3>
{_img("fig16_outliers.png", "图 4-3 Top10 大额订单与整体贡献集中度")}
{_table("18_top_orders.csv", "单笔件数 Top10 订单")}
{_table("19_outlier_impact.csv", "异常订单对核心指标的影响")}

<div class="callout">
<strong>这是本报告最重要的一条数据质量结论。</strong>
排名第一的订单一次购买 <strong>10,000 件</strong>童装，单笔即占全部件数的 13.1%；
Top10 大单合计占 27.5%。这意味着：
<ol class="steps">
<li>本项目的<strong>「购买件数」类指标必须同时给出「含/不含大单」两个口径</strong>，否则结论不可靠；</li>
<li>这些订单更可能来自批发账号或非真实消费场景，应在业务侧单独标记；</li>
<li>若用「件数」作为核心 KPI，会被极少数订单绑架——建议改用<strong>订单数 / 用户数</strong>作为主口径。</li>
</ol>
</div>
""")

    # ---- 5 宝宝画像 ----
    s5 = _section("s5", "05", "谁在买：宝宝画像与品类偏好",
                  "结合宝宝生日与性别，观察「孩子月龄」是否驱动品类选择。",
                  f"""
<h3>5.1 宝宝基础画像</h3>
{_img("fig09_baby_profile.png", "图 5-1 有档案宝宝的出生年份与性别构成")}
{_table("14_baby_birth_year.csv", "出生年份分布")}

<h3>5.2 月龄段 × 品类偏好</h3>
{_img("fig10_age_category_heatmap.png", "图 5-2 月龄段与主营品类的偏好指数")}
{_table("17_age_category_lift.csv", "偏好指数明细（>1 表示高于平均）")}

<div class="findings">
{_finding("👶", "0–6 月龄：洗护与童装", "喂养/洗护偏好指数 2.70、童装/童鞋 1.89，新生儿阶段的需求高度集中在基础照护与衣着。")}
{_finding("🧸", "7–12 月龄：玩具爆发", "玩具/童车偏好指数 2.85，是整张表中最高值——宝宝开始有互动需求，玩具品类应在此阶段做重点推荐。")}
{_finding("🍚", "6 岁以上：奶粉仍在买", "奶粉/辅食偏好指数 1.49，说明「儿童成长奶粉」的需求周期远长于婴儿阶段，容易被运营忽略。")}
</div>

<h3>5.3 性别与品类偏好：一次假设检验</h3>
{_img("fig11_gender_category.png", "图 5-3 不同性别宝宝的品类偏好对比")}
{_table("16_gender_chi2.csv", "卡方独立性检验结果", 10)}

<div class="callout">
<strong>结论：无显著差异。</strong>卡方统计量 2.41、自由度 5、p = 0.79（远大于 0.05），Cramér's V = 0.051，
效应量接近于零。<br>
这意味着在这份数据里，<strong>“男宝家庭”与“女宝家庭”的品类结构几乎一样</strong>。
一个诚实的「无差异」结论，比强行编造出差异更有价值——它直接否定了「按性别做差异化推荐」这一运营假设。
</div>
""")

    # ---- 6 商品属性 ----
    s6 = _section("s6", "06", "商品属性挖掘",
                  "property 字段被平台脱敏，但它仍然携带「商品描述丰富度」这一有效信号。",
                  f"""
{_img("fig12_property.png", "图 6-1 高频商品属性维度与属性维度数分布")}
{_table("12_property_stats.csv", "属性维度统计")}
{_table("13_property_diversity.csv", "高频属性键的取值丰富度", 15)}

<div class="findings">
{_finding("🔢", "属性维度数是有效特征", "平均每条交易带 8.68 个属性维度，中位数 9，最大 21。属性越多，通常意味着商品规格越复杂、越可能是大包装或组合装。")}
{_finding("🏷️", "两类属性键", "取值仅 3–5 种的多为枚举型属性（如规格、段位）；取值上千种的更接近品牌或型号标识（如属性键 21458 有 8,820 种取值）。")}
{_finding("🎯", "可直接转化为建模特征", "属性维度数在后续囤货预测中成为最重要的特征（重要性 0.304），说明被脱敏的字段依然有挖掘价值。")}
</div>

<div class="note">
本节的结论刻意保持克制：由于属性键与取值均被平台脱敏，无法还原「品牌 / 尺码 / 适用年龄」等具体语义。
在真实业务场景中，若有未脱敏的属性字典，这一字段可直接支撑「同款不同规格的选择偏好」分析。
</div>
""")

    # ---- 7 建模 ----
    s7 = _section("s7", "07", "囤货订单识别模型",
                  "为什么是「囤货预测」而不是经典的「性别预测」？这是一个关于数据可行性的判断。",
                  f"""
<h3>7.1 任务选择：一个必须说明的取舍</h3>
<div class="callout">
天池该数据集最经典的赛题是<strong>「根据购买行为预测宝宝性别」</strong>，但它需要<strong>单个用户的多条购买记录</strong>来构造用户级行为特征。
本次样本中带性别标签的用户仅 929 人，<strong>人均可用交易记录数 = 1.0 条</strong>，特征维度直接塌缩。
{_table("23_gender_feasibility.csv", "性别预测可行性实测")}
我们实际跑了这个任务：<strong>ROC-AUC = 0.4931，与随机猜（0.5）无异</strong>。
与其提交一个看起来能跑、实际无意义的模型，不如把算力投到数据能支撑的问题上。
</div>

<h3>7.2 正式任务：预测订单是否会囤货</h3>
<p><strong>目标定义：</strong>预测单笔订单的购买数量是否 ≥ 3 件（正类占比 6.13%），用于库存预占、包材准备与物流资源调度。</p>
<p><strong>特征设计（44 维，严格排除 buy_mount 相关字段以避免标签泄漏）：</strong>月份正余弦周期编码、周末/大促月标记、年内天数、
商品属性维度数、6 个一级类目 one-hot、Top30 二级类目 one-hot。</p>
{_img("fig14_model_eval.png", "图 7-1 模型评估：ROC 曲线、PR 曲线与混淆矩阵")}
{_table("20_model_summary.csv", "模型结果汇总")}
{_table("22_classification_report.csv", "分类报告（按最佳 F1 阈值）")}

<h3>7.3 特征重要性与业务解读</h3>
{_img("fig15_feature_importance.png", "图 7-2 随机森林特征重要性 Top12")}

<div class="findings">
{_finding("📊", "结果优于随机基线", "5 折交叉验证下 ROC-AUC = 0.778、PR-AUC = 0.210，而随机基线 PR-AUC 仅 0.061，提升 3.4 倍。")}
{_finding("🥇", "属性维度数是第一信号", "重要性 0.304，远超其他特征。商品描述越复杂，越可能是大包装或组合装——这是可解释的业务逻辑。")}
{_finding("⏰", "时间因素影响有限", "年内天数、月份周期合计重要性约 0.19，说明囤货更多由「买什么」而非「什么时候买」决定。")}
</div>

<div class="note">
<strong>关于模型选型的坦率说明：</strong>逻辑回归（PR-AUC 0.210）略优于随机森林（0.208）。
在 44 维、3 万样本、正类仅 6% 的场景下，两者的差距在噪声范围内。
我们保留了逻辑回归作为最优模型，因为它<strong>更快、更易解释、更不容易过拟合</strong>——
这比追求零点几的指标提升更有工程价值。
</div>
""")

    # ---- 8 结论 ----
    s8 = _section("s8", "08", "结论与运营建议",
                  "把上面的分析翻译成可执行的动作。",
                  """
<div class="findings">
<div class="finding" style="border-left-color:#4C7DF0">
  <div class="finding-head" style="color:#4C7DF0">① 大促资源集中在 11 月，其余月份做节奏管理</div>
  <p>11 月贡献全年约 31% 的件数，双11 单日拉动 5.19 倍。建议把年度大促预算的绝对大头压在 11 月，
  12 月延续长尾承接，6 月做常规月度活动即可——数据不支持把 618 当作年度节点来投入。</p>
</div>
<div class="finding" style="border-left-color:#FF7A9C">
  <div class="finding-head" style="color:#FF7A9C">② 尿裤与奶粉必须用两套不同的运营逻辑</div>
  <p>尿裤/湿巾：单笔 4.1 件、囤货属性强 → 适合做<strong>大包装、满减、组合囤货</strong>，围绕「一次买够」设计促销结构。<br>
  奶粉/辅食：单笔 1.5 件、12,046 个 SKU 极度分散 → 适合做<strong>订阅制、周期购、精准补货提醒</strong>，用复购锁定用户而非用折扣冲量。</p>
</div>
<div class="finding" style="border-left-color:#3DC7A0">
  <div class="finding-head" style="color:#3DC7A0">③ 建立大额异常订单的监控口径</div>
  <p>0.03% 的订单贡献 27.5% 的件数，最大单笔 10,000 件。建议在数据平台侧设置<strong>单笔件数阈值告警</strong>，
  并将这类订单在报表中单独列示；核心 KPI 建议以<strong>订单数 / 用户数</strong>为主口径，避免被个别订单绑架。</p>
</div>
<div class="finding" style="border-left-color:#FFB020">
  <div class="finding-head" style="color:#996A00">④ 按宝宝月龄做阶段化推荐（有数据支撑）</div>
  <p>0–6 月推洗护与童装、7–12 月推玩具（偏好指数 2.85）、6 岁以上仍可推成长奶粉（1.49）。
  月龄是比性别更有效的推荐维度——这一点已被数据验证。</p>
</div>
<div class="finding" style="border-left-color:#8B7BF0">
  <div class="finding-head" style="color:#6A5ACD">⑤ 放弃按性别做差异化运营</div>
  <p>卡方检验 p=0.79、效应量 0.05，性别与品类偏好在统计上无关联。把性别作为推荐特征或分群维度的收益极低，不如把资源投向月龄分层。</p>
</div>
<div class="finding" style="border-left-color:#8C9BAB">
  <div class="finding-head" style="color:#5B6B7C">⑥ 用模型为库存与物流做准备</div>
  <p>囤货预测模型可在订单生成时给出概率，识别出高概率囤货单（PR-AUC 0.21，是随机基线的 3.4 倍），
  用于提前预占库存、准备大件包材，降低临时缺货与物流爆仓的风险。</p>
</div>
</div>
""")

    # ---- 9 局限 ----
    s9 = _section("s9", "09", "局限性说明与后续计划",
                  "主动交代边界，比假装没有边界更专业。",
                  """
<h3>9.1 本次分析的局限</h3>
<ol class="steps">
<li><strong>样本为按行抽样的子集。</strong>29,971 笔交易对应 29,944 个用户，人均 1.0 笔，
无法构造任何用户级行为特征，故 RFM、复购周期、用户生命周期、性别预测等分析均不成立。</li>
<li><strong>无金额字段。</strong>数据只有购买数量（buy_mount）没有成交金额，所有「规模」结论均为件数口径，
不能等同于 GMV 口径。</li>
<li><strong>类目与属性已脱敏。</strong>一级类目中文名依赖社区对照表，属性键无法还原语义，
因此品类命名与属性分析都保持克制表述。</li>
<li><strong>时间截断。</strong>2012 年仅含 7–12 月、2015 年仅含 1–2 月，所有趋势与季节性分析只使用数据完整的 2013–2014 年。</li>
<li><strong>性别编码存在资料冲突。</strong>官方 Overview 与部分中文资料编码相反，本报告已做对称处理以规避风险。</li>
</ol>

<h3>9.2 若拿到全量数据的后续计划</h3>
<ol class="steps">
<li><strong>用户级特征工程</strong>：构造 RFM、品类偏好向量、购买周期，把性别预测与复购预测重新做一遍，预计 AUC 可显著提升。</li>
<li><strong>引入金额字段</strong>（若可得）：把件数口径升级为 GMV 口径，重做品类贡献与用户价值分层。</li>
<li><strong>时间序列预测</strong>：用 SARIMA / Prophet 对月度销量建模，量化大促的滞后与透支效应。</li>
<li><strong>商品关联分析</strong>：基于用户购买的商品集合做关联规则挖掘（Apriori），输出「买了尿裤还会买什么」的搭售策略。</li>
<li><strong>线上化</strong>：把模型封装为 API，接入订单系统做实时囤货概率打分。</li>
</ol>
""")

    # ---- 10 复现 ----
    s10 = _section("s10", "10", "项目复现方式",
                   "一条命令跑完全流程。",
                   """
<h3>10.1 环境与运行</h3>
<pre># 1. 安装依赖
pip install -r requirements.txt

# 2. 一键运行完整流程（加载 → 清洗 → 指标 → 绘图 → 建模）
python scripts/run_all.py

# 3. 生成这份 HTML 报告
python scripts/build_report.py</pre>

<h3>10.2 项目结构</h3>
<pre>mum-baby-analysis/
├── data/
│   ├── raw/                 原始数据（CSV）
│   └── processed/           清洗后的数据集
├── src/                     可复用的分析模块
│   ├── config.py            路径、配色、中文类目字典
│   ├── data_loader.py       数据加载与质量体检
│   ├── preprocess.py        清洗、特征工程、属性解析
│   ├── analysis.py          业务指标计算（8 个分析模块）
│   ├── visualize.py         16 张图表的绘制函数
│   ├── modeling.py          特征工程与模型训练/评估
│   └── report.py            报告生成
├── scripts/
│   ├── run_all.py           一键运行全流程
│   └── build_report.py      生成 HTML 报告
├── notebooks/
│   └── mum_baby_analysis.ipynb   交互式分析笔记
└── reports/
    ├── figures/             16 张图表
    ├── tables/              24 份指标明细表
    └── report.html          本报告</pre>

<div class="note">
所有中间结果（<code>reports/tables/*.csv</code>）都会落盘，报告中的每个数字都可以追溯到对应的 CSV，
方便复核与二次分析。
</div>
""")

    footer = f"""
<footer>
数据来源：阿里云天池 · 淘宝母婴购物数据集（Baby Goods Info Data）· 本项目使用其中的公开采样样本<br>
分析工具：Python 3.13 / pandas / NumPy / SciPy / scikit-learn / Matplotlib · 报告生成于 {today}
</footer>
"""

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>母婴电商购物行为数据分析报告</title>
<style>{CSS}</style>
</head>
<body>
{head}
<div class="wrap">
{toc}
{findings}
{s1}{s2}{s3}{s4}{s5}{s6}{s7}{s8}{s9}{s10}
{footer}
</div>
</body>
</html>
"""

    out = REPORT_DIR / "report.html"
    out.write_text(html_doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    p = build()
    print(f"报告已生成：{p}")
    print(f"文件大小：{p.stat().st_size / 1024 / 1024:.2f} MB")
