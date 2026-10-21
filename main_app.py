# -*- coding: utf-8 -*-
"""双创决策沙盘——从商业画布→4P作战→计划书路演的算账闭环
====================================================
Streamlit 教学应用 V1.0（虚拟仿真实验教学项目申报 · 创新创业教育）

依据《双创决策沙盘虚拟仿真实验方案 V3.0 完整版》实现：
- 26 步决策主线交互式仿真实验（开局契约 → 赛道/痛点/画像/市场 → 商业画布九格 →
  4P作战（MVP/定价/渠道/促销）→ 月度结算 → R1/R2/R3 风险事件 → 计划书 → AI判定 → 虚拟路演）；
- 算账闭环四因子：现金 / 客户数 / 毛利 / 路演与计划书质量分，每步操作后实时刷新；
- 红线机制：资金红线（现金≤0 且融资失败 → 破产）/ 合规红线（无资质经营 → 直接失败）/
  画布红线（价值主张空话且收入=0 → 不能进入4P）/ 路演红线（计划书无壁垒与风险 → 路演分封顶60）/
  刷分红线（复制粘贴套话 → 该模块重做）；
- 3 类风险事件博弈（供应链/竞品降价/政策合规），月度结算+同口径复盘表（上轮 vs 本轮）；
- AI 双节点（逻辑裁判 + 提分教练）：本地规则引擎实现，只判定与建议、不替学生决策，
  接口异常时按降级方案（硬编码权重公式）照常出分；
- 考核评价：七模块 100 分制（决策过程40 + 画布逻辑15 + 4P执行与一致性15 +
  风险控制10 + 计划书10 + 路演10），终局评定 优秀/合格/不合格；
- 20 个小白化词条、进度导航、四因子仪表盘、里程碑鼓励、审计日志 CSV 导出。

算账引擎为模块级纯函数（可冒烟测试）；UI 层以 st.session_state 驱动。
"""
import copy
import math
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

APP_VERSION = "V1.1"
INIT_CASH = 1_000_000  # 100 万元启动资金
MONTHS = [1, 2, 3, 4]

# ============================================================================
# 一、元数据：板块 / 26 步主线 / 赛道 / 卡片池 / 词条
# ============================================================================
SECTIONS = ["🏠 实验导览", "🧭 决策台", "📋 复盘报告", "🛡 能力画像", "📄 经营决策报告"]

STEPS = [
    (1, "开局剧本与契约", "C", 2),
    (2, "选赛道", "C", 4),
    (3, "选痛点卡片", "M", 4),
    (4, "用户画像匹配", "C", 3),
    (5, "市场扫描确认", "C", 2),
    (6, "画布①客户细分", "M", 2),
    (7, "画布②价值主张", "M", 4),
    (8, "画布③渠道通路", "M", 2),
    (9, "画布④客户关系", "C", 1),
    (10, "画布⑤收入来源", "M", 3),
    (11, "画布⑥关键资源", "M", 2),
    (12, "画布⑦关键业务", "M", 2),
    (13, "画布⑧重要伙伴", "M", 1),
    (14, "画布⑨成本结构分配", "S", 4),
    (15, "产品功能栈（MVP取舍）", "M", 5),
    (16, "定价（带市场基准）", "S", 5),
    (17, "渠道投放预算", "S", 4),
    (18, "促销组合", "M", 3),
    (19, "4P一致性校验（AI提示）", "A", 3),
    (20, "月度结算（Month 1）", "仪表盘", 3),
    (21, "R1 供应链/内容违规", "R·C", 4),
    (22, "R2 竞品降价/技术替代", "R·C", 3),
    (23, "R3 政策合规", "R·C", 3),
    (24, "计划书草稿补全", "T", 6),
    (25, "A判计划书（AI五维）", "A", 4),
    (26, "虚拟路演+终评", "T+评分", 10),
]

TRACKS = {
    "🛵 校园即时配送": {
        "name": "校园即时配送", "emoji": "🛵", "sea": "红海",
        "hint": "竞品多、用户刚需，拼的是效率与成本控制",
        "bench_price": 8.0, "unit_var": 5.0, "freq": 8.0, "multiplier": 10,
        "demand_idx": 82, "cac_base": 4.0, "base_acq": 1500, "fixed_base": 30000,
        "prefer_persona": "大一大二新生（价格敏感）",
        "conflict_persona": "教职工与研究生（高客单、重品质）",
        "color": "#FF7043",
    },
    "📚 校园二手教材与旧物循环": {
        "name": "校园二手教材与旧物循环", "emoji": "📚", "sea": "偏蓝海",
        "hint": "闲置需求真实、供给分散，先做平台撮合再谈盈利",
        "bench_price": 25.0, "unit_var": 12.0, "freq": 2.0, "multiplier": 9,
        "demand_idx": 60, "cac_base": 3.5, "base_acq": 800, "fixed_base": 20000,
        "prefer_persona": "大一大二新生（价格敏感）",
        "conflict_persona": "考研/考证党（时间紧、愿付费）",
        "color": "#7C4DFF",
    },
    "🥗 校园轻食与健康餐": {
        "name": "校园轻食与健康餐", "emoji": "🥗", "sea": "红海",
        "hint": "健康意识强，但成本与食品资质门槛高",
        "bench_price": 15.0, "unit_var": 9.0, "freq": 6.0, "multiplier": 8,
        "demand_idx": 75, "cac_base": 5.0, "base_acq": 1000, "fixed_base": 35000,
        "prefer_persona": "健身人群与减脂党",
        "conflict_persona": "大一大二新生（价格敏感）",
        "color": "#66BB6A",
    },
    "🎓 校园技能考证培训撮合": {
        "name": "校园技能考证培训撮合", "emoji": "🎓", "sea": "蓝海",
        "hint": "高客单、低频，重信任与口碑传播",
        "bench_price": 199.0, "unit_var": 80.0, "freq": 1.0, "multiplier": 12,
        "demand_idx": 55, "cac_base": 60.0, "base_acq": 300, "fixed_base": 40000,
        "prefer_persona": "考研/考证党（时间紧、愿付费）",
        "conflict_persona": "大一大二新生（价格敏感）",
        "color": "#42A5F5",
    },
}

PAINS = {
    "校园即时配送": [
        "下课10分钟没饭吃，排队太久",
        "外卖送到宿舍楼下不让进，取餐麻烦",
        "夜宵选择少，23点后基本没得吃",
        "拼单凑不够起送价，一个人点不划算",
        "高峰期下单要等40分钟以上",
    ],
    "校园二手教材与旧物循环": [
        "一套新教材要几百块，太贵",
        "毕业季旧书直接扔掉太浪费",
        "想要的绝版书/选修课教材到处找不到",
        "闲鱼跨城寄送慢，等不及",
        "交易没有信用保障，怕被骗",
    ],
    "校园轻食与健康餐": [
        "食堂油大盐重，健身期吃不惯",
        "外卖轻食一份30元起，太贵",
        "减脂期不知道吃什么，没人指导",
        "下午茶全是高糖高热量，不敢吃",
        "宿舍没法自己做饭，选择有限",
    ],
    "校园技能考证培训撮合": [
        "考证信息零散，找不到靠谱的课",
        "自学效率低，没人答疑",
        "校外机构太贵、水课多",
        "简历缺少技能背书，找工作吃亏",
        "想找学长学姐一对一辅导没有渠道",
    ],
}

PERSONAS = [
    "大一大二新生（价格敏感）",
    "考研/考证党（时间紧、愿付费）",
    "健身人群与减脂党",
    "教职工与研究生（高客单、重品质）",
]

MARKET_CARDS = [
    "需求已验证：调研显示 62% 同学一周内≥3次相关需求",
    "竞品价格已探明：主流竞品定价在市场基准价 ±10% 区间",
    "竞争烈度评估：头部玩家已占约 60% 市场，但服务痛点仍突出",
]

CANVAS_POOLS = {
    "客户细分": [
        "大一新生", "考研/考证党", "教职工", "夜猫子群体",
        "健身人群", "社团骨干", "毕业班学生", "家长代下单",
    ],
    "价值主张": [
        "30分钟必达（具体承诺）",
        "比食堂/竞品便宜2元（价格锚点）",
        "专属宿舍楼合作（独家资源）",
        "AI智能调度（技术壁垒）",
        "会员月付9.9元（订阅模式）",
        "“赋能校园生态”（空话）",
        "“一站式解决方案”（空话）",
        "“打造校园服务闭环”（空话）",
    ],
    "渠道通路": [
        "小红书种草", "校园大使", "微信小程序", "地推摊位",
        "宿舍楼代理", "朋友圈裂变", "社团合作", "校园广播",
    ],
    "客户关系": [
        "会员积分体系", "社群运营", "客服秒回", "生日优惠券", "老带新返利",
    ],
    "收入来源": [
        "每单配送/服务费", "会员订阅（9.9元/月）", "商家入驻抽佣",
        "广告位收入", "增值服务费", "完全不收费（收入=0）",
    ],
    "关键资源": [
        "自建配送/服务团队", "小程序系统", "宿舍楼独家协议",
        "品牌口碑", "数据与算法", "商家供给网络",
    ],
    "关键业务": [
        "接单与派单", "仓储与分拣", "质量控制", "数据运营", "供应商管理",
    ],
    "重要伙伴": [
        "食堂/商家", "宿舍楼长", "快递站", "学生会", "上游供应商",
    ],
}

EMPTY_TALK = ["“赋能校园生态”（空话）", "“一站式解决方案”（空话）", "“打造校园服务闭环”（空话）"]

MVP_FEATURES = [
    "下单小程序", "实时定位配送", "智能拼单", "评价体系",
    "会员积分", "数据看板", "商家后台", "AI推荐",
]

CHANNEL_NAMES = ["线上投放（万）", "地推摊位（万）", "校园代理（万）"]
CHANNEL_KEYS = ["ch_online", "ch_ground", "ch_agent"]

PROMOS = ["首单立减3元", "满20减5", "分享裂变红包", "KOL种草", "节日大促", "会员日折扣"]

R1_OPTIONS = {
    "启动备用供应商预案（多花5万应急费，供应稳定）": {"cost": 50000, "churn": 0, "score": 4, "tag": "有预案"},
    "接受供应商涨价（月成本×1.25）": {"cost": 0, "churn": 0, "score": 2, "tag": "被动接受"},
    "换用无资质小作坊（便宜但风险高）": {"cost": -20000, "churn": 0, "score": 0, "tag": "合规风险", "illegal": True},
}
R2_OPTIONS = {
    "跟随降价10%（保客户，毛利下降）": {"price_mul": 0.9, "churn": 0, "score": 3, "tag": "跟随降价"},
    "差异化升级服务（固定成本+3万，客户增长）": {"fixed_add": 30000, "churn": 0, "new_add": 200, "score": 3, "tag": "差异化"},
    "死扛不降价（客户大量流失）": {"churn": 3, "score": 0, "tag": "死扛降价"},
}
R3_OPTIONS = {
    "补齐资质合规经营（一次性成本+8万）": {"cost": 80000, "score": 3, "tag": "补齐资质"},
    "无资质硬扛经营（合规红线→直接失败）": {"score": 0, "tag": "无资质", "illegal": True},
    "业务转型规避监管（月收入×0.7）": {"income_mul": 0.7, "score": 1, "tag": "转型规避"},
}

PLAN_FIELDS = {
    "壁垒": ["独家宿舍楼合作+配送算法", "品牌口碑与社群资产", "数据积累与AI调度", "供应链独家协议", "暂时没有想好（留白）"],
    "团队": ["创始团队3人，财务+技术+运营", "有校园资源，地推执行力强", "导师/校友资源丰富", "团队成员均为兼职，时间有限"],
    "融资用途": ["50%研发、30%市场、20%备付金", "60%市场投放、30%团队扩招、10%合规", "70%供应链、20%研发、10%运营", "主要做现金储备，暂不规划"],
    "风险与合规": ["已识别资质/食品安全/知识产权风险并备案", "识别了主要风险但未完全覆盖", "暂无风险预案（留白）"],
}

PLAN_LEGAL_RISK = "已识别资质/食品安全/知识产权风险并备案"   # 路演红线判定的关键项

GLOSSARY = [
    ("商业画布", "9个格子画清“卖给谁、卖什么、怎么收钱、要花多少”", "滴滴：乘客/司机→平台撮合→抽佣金", "客户=大学生；价值=30分钟送达；收入=每单配送费"),
    ("价值主张", "顾客选你而不是竞品的理由", "拼多多“更便宜”", "比食堂快10分钟、便宜2元"),
    ("客户细分", "你具体服务哪一类人，不喊“所有人”", "元气森林→控糖年轻人", "大学城2万名学生，先打3栋宿舍"),
    ("渠道通路", "怎么让人知道并买到", "完美日记→小红书种草", "小红书+校园大使+小程序"),
    ("收入来源", "钱从哪进", "订阅/佣金/广告", "基础版免费，会员9.9元/月"),
    ("成本结构", "哪些钱必须花", "美团骑手工资是大头", "研发30%+营销40%+人力20%+合规10%"),
    ("4P", "产品/价格/渠道/促销四件套", "瑞幸：爆款+低价+快取店+发券", "MVP3功能+客单12元+校园代理+首单立减3元"),
    ("MVP", "最简可卖版本，先验证再砸钱", "Dropbox先放演示视频测需求", "只做“下单+配送”，不做智能调度"),
    ("客单价", "一个客户平均花多少钱", "奶茶店一杯15元", "校园配送每单8元"),
    ("毛利", "卖价减掉变动成本，自己留下的", "一杯咖啡卖15、料3元→毛利12", "客单8−配送5=3元毛利"),
    ("获客成本CAC", "拉一个新客户平均花多少推广费", "每发100元券拉10人→CAC10元", "投2000元拉500人→CAC4元"),
    ("单位经济", "算一笔：一个客户到底赚不赚钱", "卖一单赚3元、获客花4元→亏", "毛利3 < CAC4 → 模型不成立"),
    ("估值", "公司值多少钱", "年利润100万×10倍=1000万", "月毛利3万×10倍+画布分=估值"),
    ("赛道", "你进入哪类生意", "咖啡/新能源车/AI", "校园即时配送赛道"),
    ("壁垒", "别人难抄你的地方", "专利/数据/品牌", "独家宿舍楼合作+配送算法"),
    ("合规", "做的事有没有牌照、不违规", "卖食品要食品经营许可", "送餐要资质，无证→红线失败"),
    ("路演", "给投资人/评委讲项目讲故事", "3分钟讲清做什么、凭什么赢", "5页PPT+3分钟讲+评委问答"),
    ("痛点", "客户真实且急的麻烦", "下课排队20分钟买不到饭", "“下课10分钟没饭吃”"),
    ("闭环", "钱/客户/信息能一圈圈转起来", "获客→成交→复购→再获客", "学生下单→复购→老带新"),
    ("红海/蓝海", "竞争挤满 vs 还没人做的地盘", "奶茶店=红海；校园旧书回收=蓝海", "校园配送=红海；旧教材+代卖=偏蓝海"),
]


# ============================================================================
# 二、算账引擎（纯函数，可冒烟测试）
# ============================================================================
def init_state():
    """初始实验状态：四因子 + 决策记录 + 月份记录 + 审计"""
    return {
        "started": False,
        "finished": False,
        "bankrupt": False,
        "compliance_fail": False,
        "month": 0,
        "cash": INIT_CASH,
        "customers": 0,
        "gross_margin": 0.0,
        "pitch_score": 0.0,
        "valuation": 0.0,
        "decisions": {},
        "month_records": [],          # [{month, cash, customers, gm, income, cost, new_c, churn}]
        "audit": [],                  # [{step, name, choice, impact}]
        "scores": {},                 # 七模块分
        "total_score": 0.0,
        "grade": "不合格",
        "pass_goal": False,
        "risks": {},                  # {1: opt, 2: opt, 3: opt}
        "financed": False,
        "plan": {},
        "roadshow": {},
        "canvas_logic_score": 0.0,
        "ai_canvas": None,
        "ai_plan": None,
        "blocked_canvas": False,
        "redline_log": [],
    }


def _deviation(price, bench):
    if not bench:
        return 0.0
    return (price - bench) / bench


def price_factor(price, bench):
    """价格偏离 → 需求系数；|偏离|>40% 触发销量惩罚"""
    dev = _deviation(price, bench)
    f = 1.0 - 0.6 * abs(dev) if dev >= 0 else 1.0 + 0.6 * abs(dev)
    f = min(max(f, 0.35), 1.9)
    if abs(dev) > 0.40:
        f *= 0.55          # 销量惩罚
    return f


def canvas_logic_score(decisions):
    """画布逻辑分 0-100：价值主张0.3 + 客户细分匹配0.2 + 收入来源0.2 + 成本结构0.15 + 渠道通路0.15"""
    vp = decisions.get("canvas_价值主张", []) or []
    cs = decisions.get("canvas_客户细分", []) or []
    rs = decisions.get("canvas_收入来源", []) or []
    ch = decisions.get("canvas_渠道通路", []) or []
    cost = decisions.get("cost_alloc", {}) or {}

    # 价值主张：非空话且≥1条 → 满分，空话越多越低
    empty = len([v for v in vp if v in EMPTY_TALK])
    real = len([v for v in vp if v not in EMPTY_TALK])
    if not vp:
        vp_score = 0
    elif empty == 0 and real >= 1:
        vp_score = 100
    elif empty == 1:
        vp_score = 55
    else:
        vp_score = 30

    # 客户细分匹配：选了细分客户（非“所有人”）且与价值主张不冲突
    cs_real = [c for c in cs if c not in ("社团骨干", "家长代下单")]
    cs_score = min(100, 40 + 20 * len(cs_real)) if cs_real else 20

    # 收入来源：非“完全不收费”且有≥1条
    if rs and "完全不收费（收入=0）" not in rs:
        rs_score = min(100, 50 + 25 * len(rs))
    else:
        rs_score = 0

    # 成本结构：合计=100 且分布合理（研发+人力+营销占大头）
    if cost and abs(sum(cost.values()) - 100) < 0.5:
        big = sum(cost.get(k, 0) for k in ("研发", "营销", "人力"))
        cs_score_alloc = min(100, 40 + big)
    else:
        cs_score_alloc = 0

    # 渠道通路：≥1 条具体渠道
    ch_score = min(100, 40 + 20 * len(ch)) if ch else 10

    score = vp_score * 0.3 + cs_score * 0.2 + rs_score * 0.2 + cs_score_alloc * 0.15 + ch_score * 0.15
    return round(max(0.0, min(100.0, score)), 1)


def canvas_empty_talk(decisions):
    vp = decisions.get("canvas_价值主张", []) or []
    empty = [v for v in vp if v in EMPTY_TALK]
    return empty


def canvas_redline(decisions):
    """画布红线：价值主张空话 且 收入来源=0"""
    rs = decisions.get("canvas_收入来源", []) or []
    income_zero = (not rs) or ("完全不收费（收入=0）" in rs)
    empty = len(canvas_empty_talk(decisions)) > 0
    return empty and income_zero


def calc_new_customers(decisions, track, month_extra=0):
    """新增获客：基准获客 × 需求 × 价格 × 促销 × 渠道"""
    price = decisions.get("price", track["bench_price"])
    bench = track["bench_price"]
    pf = price_factor(price, bench)
    promos = decisions.get("promos", []) or []
    promo_f = 1.0 + 0.12 * min(len(promos), 3)
    ch_wan = sum(decisions.get(k, 0) for k in CHANNEL_KEYS)
    ch_f = min(1 + 0.04 * ch_wan, 2.0)
    demand_f = track["demand_idx"] / 80.0
    base = track["base_acq"] * demand_f * pf * promo_f * ch_f
    return max(0, int(round(base + month_extra)))


def settle_month(state, month, decisions, track, risk=None):
    """结算一个月：现金/客户数/毛利。risk 为当月风险事件附加参数 dict。"""
    risk = risk or {}
    price = decisions.get("price", track["bench_price"])
    if risk.get("price_mul"):
        price = price * risk["price_mul"]
    var = track["unit_var"]
    freq = track["freq"]
    customers = state["customers"]

    new_c = calc_new_customers(decisions, track, month_extra=risk.get("new_add", 0))
    churn_mul = risk.get("churn", 0)
    churn = max(1, int(customers * 0.08 * (1 + churn_mul))) if customers > 0 else 0
    customers = max(0, customers + new_c - churn)

    orders = customers * freq
    income = orders * price
    if risk.get("income_mul"):
        income = income * risk["income_mul"]
    var_cost = orders * var
    channel = sum(decisions.get(k, 0) for k in CHANNEL_KEYS) * 10000.0
    fixed = track["fixed_base"]
    if len(decisions.get("mvp", []) or []) > 5:
        fixed = fixed * 1.8                       # MVP 贪多 → 成本暴涨
    if risk.get("fixed_add"):
        fixed += risk["fixed_add"]
    if risk.get("cost"):
        fixed += risk["cost"]
    gm = income - var_cost - channel - fixed

    state["customers"] = customers
    state["gross_margin"] = round(gm, 1)
    state["cash"] = round(state["cash"] + gm, 1)
    state["month"] = month
    state["month_records"].append({
        "month": month, "cash": round(state["cash"], 1), "customers": customers,
        "gm": round(gm, 1), "income": round(income, 1), "var_cost": round(var_cost, 1),
        "channel": round(channel, 1), "fixed": round(fixed, 1), "new_c": new_c, "churn": churn,
    })
    return state


def cac_value(decisions, track, month_state=None):
    """获客成本 CAC（元/人）：渠道预算 / 当月新增客户"""
    ch_wan = sum(decisions.get(k, 0) for k in CHANNEL_KEYS)
    new_c = calc_new_customers(decisions, track)
    if new_c <= 0:
        return float("inf")
    return (ch_wan * 10000.0) / new_c


def consistency_issues(decisions, track):
    """4P 一致性校验 → issues 列表（AI 逻辑裁判输入）"""
    issues = []
    price = decisions.get("price", track["bench_price"])
    bench = track["bench_price"]
    dev = _deviation(price, bench)
    promos = decisions.get("promos", []) or []
    ch = {k: decisions.get(k, 0) for k in CHANNEL_KEYS}
    has_online = ch.get("ch_online", 0) > 0
    has_ground = ch.get("ch_ground", 0) > 0
    has_agent = ch.get("ch_agent", 0) > 0
    mvp = decisions.get("mvp", []) or []

    if dev > 0.4 and not (has_ground or has_agent):
        issues.append("定价显著高于市场基准，但线下地推/代理渠道薄弱——“高价+弱触达”自相矛盾")
    if dev < -0.4 and "KOL种草" in promos:
        issues.append("低价策略却投放高成本 KOL 种草，促销与价格策略不匹配")
    if "满20减5" in promos and price < 20:
        issues.append("客单价低于满减门槛20元，满减促销难以触发")
    if len(mvp) > 5:
        issues.append("MVP 功能超过5个，验证阶段“贪多”，成本与开发风险暴涨")
    if len(mvp) < 3:
        issues.append("MVP 功能不足3个，产品价值主张缺少支撑")
    if not (has_online or has_ground or has_agent):
        issues.append("渠道投放为0，没有任何获客通路")
    if ch.get("ch_online", 0) > 0 and not has_ground and not has_agent and "微信小程序" not in (decisions.get("canvas_渠道通路") or []):
        issues.append("线上投放缺少小程序/种草承接，流量无处转化")
    return issues


def ai_judge_canvas(decisions, track, state):
    """AI 逻辑裁判（节点1）：画布与4P五维判定 0-100（规则引擎降级实现）"""
    issues = consistency_issues(decisions, track)
    cs = canvas_logic_score(decisions)

    # 1 价值主张真实性 25%
    empty = canvas_empty_talk(decisions)
    vp_real = len([v for v in (decisions.get("canvas_价值主张") or []) if v not in EMPTY_TALK])
    if empty:
        vp_dim = 30 if vp_real == 0 else 55
    elif vp_real >= 2:
        vp_dim = 90
    else:
        vp_dim = 70

    # 2 4P一致性 25%
    if issues:
        con_dim = max(30, 80 - 15 * len(issues))
    else:
        con_dim = 90

    # 3 单位经济可行 20%：毛利 ≥ CAC×1.5
    price = decisions.get("price", track["bench_price"])
    margin_per_order = price - track["unit_var"]
    cac = cac_value(decisions, track)
    if math.isinf(cac) or cac == 0:
        econ_dim = 50
    elif margin_per_order >= cac * 1.5:
        econ_dim = 90
    else:
        econ_dim = 45

    # 4 画布九格完整度 15%
    filled = sum(1 for k in CANVAS_POOLS if (decisions.get(f"canvas_{k}") or []))
    complete_dim = min(100, 30 + 10 * filled)

    # 5 合规与风险覆盖 15%
    plan = state.get("plan") or {}
    if plan.get("风险与合规") == PLAN_LEGAL_RISK:
        comp_dim = 95
    elif plan.get("风险与合规"):
        comp_dim = 60
    else:
        comp_dim = 40

    scores = {
        "价值主张真实性": vp_dim, "4P一致性": con_dim, "单位经济可行": econ_dim,
        "画布完整度": complete_dim, "合规风险覆盖": comp_dim,
    }
    total = round(vp_dim * 0.25 + con_dim * 0.25 + econ_dim * 0.20 + complete_dim * 0.15 + comp_dim * 0.15, 1)
    warnings = []
    if empty:
        warnings.append("价值主张出现空话（赋能/一站式/闭环），该维度 ≤55")
    if issues:
        warnings.append("4P 存在自相矛盾：" + issues[0])
    if not math.isinf(cac) and margin_per_order < cac * 1.5:
        warnings.append(f"单位经济不成立：毛利/单 {margin_per_order:.1f} < CAC×1.5 {cac*1.5:.1f}")
    suggestions = []
    if empty and vp_real == 0:
        suggestions.append("建议回到第7步，把“赋能/一站式”换成具体承诺（如“30分钟必达、便宜2元”）")
    if math.isinf(cac) or (margin_per_order < cac * 1.5 and cac > 0):
        suggestions.append("建议压缩渠道预算或提高客单价，让单客户毛利 ≥ CAC×1.5")
    if complete_dim < 80:
        suggestions.append("建议补齐画布九格，九格自洽才能支撑估值")
    return {"scores": scores, "total": total, "warnings": warnings, "suggestions": suggestions, "canvas_score": cs}


def ai_judge_plan(state, track, decisions):
    """AI 提分教练（节点2）：计划书五维判定 0-100（规则引擎降级实现）"""
    plan = state.get("plan") or {}
    pains = decisions.get("pains", []) or []
    persona = decisions.get("persona", "")
    cs = canvas_logic_score(decisions)
    issues = consistency_issues(decisions, track)

    # 1 问题真实/痛点有据 25%
    pain_dim = min(100, 40 + 20 * len(pains)) if pains else 20

    # 2 商业模型自洽 25%
    model_dim = min(100, int(cs * 0.6 + 40))

    # 3 数据可信（有假设与来源）20%
    scanned = decisions.get("market_confirmed", False)
    data_dim = 90 if scanned else 55

    # 4 壁垒与风险 20%
    barrier = plan.get("壁垒", "")
    risk = plan.get("风险与合规", "")
    if barrier and "留白" not in barrier and risk and "留白" not in risk:
        br_dim = 90
    elif barrier and "留白" not in barrier:
        br_dim = 60
    else:
        br_dim = 35

    # 5 表达与结构 10%
    texts = [plan.get(k, "") for k in ("壁垒", "团队", "融资用途", "风险与合规")]
    total_len = sum(len(str(t)) for t in texts)
    expr_dim = min(100, 40 + int(total_len / 3))

    scores = {
        "问题真实": pain_dim, "商业模型自洽": model_dim, "数据可信": data_dim,
        "壁垒与风险": br_dim, "表达与结构": expr_dim,
    }
    total = round(pain_dim * 0.25 + model_dim * 0.25 + data_dim * 0.20 + br_dim * 0.20 + expr_dim * 0.10, 1)
    suggestions = []
    if br_dim < 60:
        suggestions.append("计划书必须写清“壁垒与风险”，否则路演分封顶60")
    if pain_dim < 60:
        suggestions.append("回到第3步补充真实痛点，用调研数据支撑问题真实性")
    if issues:
        suggestions.append("先解决4P矛盾：" + issues[0])
    return {"scores": scores, "total": total, "suggestions": suggestions}


def valuation(state, decisions, track, canvas_score, pitch_score):
    """估值 = 月毛利 × 行业乘数(8~12) + 画布逻辑分×2000 + 路演分×500"""
    gm = state.get("gross_margin", 0.0)
    val = gm * track["multiplier"] + canvas_score * 2000 + pitch_score * 500
    return round(val, 1)


def roadshow_score(state, decisions):
    """路演分 0-100：规则评分 + 表达质量；无壁垒与风险章节 → 封顶60"""
    plan = state.get("plan") or {}
    rs = state.get("roadshow") or {}
    barrier = plan.get("壁垒", "")
    risk = plan.get("风险与合规", "")
    has_br = bool(barrier and "留白" not in barrier and risk and "留白" not in risk)
    texts = [rs.get("陈述模式", ""), rs.get("陈述数据", ""), rs.get("陈述壁垒", "")]
    total_len = sum(len(str(t)) for t in texts)
    base = min(50, 10 + total_len // 4)
    qa = 30 if decisions.get("roadshow_qa") == "数据与财务细节（答得有理有据）" else (15 if decisions.get("roadshow_qa") else 0)
    score = min(100, base + qa + (20 if has_br else 0))
    if not has_br:
        score = min(score, 60)          # 路演红线：封顶60
    return round(score, 1), has_br


def compute_scores(state, decisions, track):
    """七模块 100 分制总评"""
    d = decisions
    s = {}
    # 决策过程A（赛道/痛点/画像/市场）20 分
    sA = (2 if d.get("s1_read") else 0) + (4 if d.get("track") and d.get("track") != "盲选" else 0) \
        + (4 if len(d.get("pains", [])) >= 2 else (2 if len(d.get("pains", [])) == 1 else 0)) \
        + (3 if d.get("persona") == track.get("prefer_persona") else (1 if d.get("persona") and d.get("persona") != track.get("conflict_persona") else 0)) \
        + (2 if d.get("market_confirmed") else (1 if d.get("market_skipped") else 0))
    s["决策过程A"] = round(20 * sA / 15.0)

    # 决策过程B（4P作战/月度结算）20 分
    mvp_n = len(d.get("mvp", []))
    p15 = 5 if mvp_n == 3 else (3 if 0 < mvp_n < 6 else 1)
    dev = abs(_deviation(d.get("price", track["bench_price"]), track["bench_price"]))
    p16 = 5 if dev <= 0.2 else (3 if dev <= 0.4 else 1)
    ch_wan = sum(d.get(k, 0) for k in CHANNEL_KEYS)
    p17 = 4 if 3 <= ch_wan <= 25 else (2 if ch_wan > 0 else 0)
    p18 = 3 if len(d.get("promos", [])) >= 2 else (1 if d.get("promos") else 0)
    p19 = 3 if d.get("s19_read") else (1 if d.get("s19_ignored") else 0)
    p20 = 3 if state.get("month") >= 1 else 0
    sB = (p15 + p16 + p17 + p18 + p19 + p20) / 23.0
    s["决策过程B"] = round(20 * sB)

    # 画布逻辑 15 分
    cs = state.get("canvas_logic_score", 0.0)
    s["商业画布逻辑"] = round(15 * cs / 100.0)

    # 4P执行与一致性 15 分（以 AI 逻辑裁判的 4P 一致性维度为主）
    ai = state.get("ai_canvas") or ai_judge_canvas(d, track, state)
    con_dim = ai["scores"]["4P一致性"]
    s["4P执行与一致性"] = round(15 * con_dim / 100.0)

    # 风险控制 10 分
    r1 = d.get("r1", ""); r2 = d.get("r2", ""); r3 = d.get("r3", "")
    sR = 0
    if r1 in R1_OPTIONS: sR += R1_OPTIONS[r1]["score"]
    if r2 in R2_OPTIONS: sR += R2_OPTIONS[r2]["score"]
    if r3 in R3_OPTIONS: sR += R3_OPTIONS[r3]["score"]
    if state.get("compliance_fail"): sR = 0
    s["风险控制"] = round(10 * sR / 10.0)

    # 计划书 10 分
    ai_plan = state.get("ai_plan") or ai_judge_plan(state, track, d)
    s["创业计划书"] = round(10 * ai_plan["total"] / 100.0)

    # 路演 10 分
    ps, has_br = roadshow_score(state, d)
    state["pitch_score"] = ps
    s["虚拟路演答辩"] = round(10 * ps / 100.0)

    total = round(sum(s.values()), 1)
    if state.get("bankrupt") or state.get("compliance_fail"):
        total = min(total, 40.0)
        s["风险控制"] = 0
    grade = "优秀" if total >= 85 else ("合格" if total >= 60 else "不合格")
    return s, total, grade


def check_pass_goal(state, decisions, track):
    """通关目标：估值≥150万 且 现金>0 且 客户数≥1000"""
    cs = state.get("canvas_logic_score", 0.0)
    ps = state.get("pitch_score", 0.0)
    val = valuation(state, decisions, track, cs, ps)
    state["valuation"] = val
    ok = val >= 1_500_000 and state["cash"] > 0 and state["customers"] >= 1000
    state["pass_goal"] = bool(ok)
    return ok


def detect_cheat(text):
    """刷分红线：复制粘贴通用套话检测（简单规则）"""
    if not text:
        return False
    t = str(text)
    generic = ["本项目致力于", "赋能", "一站式", "打造生态", "积极响应", "众所周知"]
    hits = sum(1 for g in generic if g in t)
    return hits >= 2 and len(t) >= 30


def build_plan_autofill(decisions, track):
    """计划书骨架自动灌入（Step24 顶部展示）"""
    pains = "、".join(decisions.get("pains", [])[:3]) or "（待补）"
    cs = "、".join(decisions.get("canvas_客户细分", [])[:3]) or "（待补）"
    vp = "、".join([v for v in decisions.get("canvas_价值主张", []) if v not in EMPTY_TALK][:2]) or "（待补）"
    rs = "、".join([v for v in decisions.get("canvas_收入来源", []) if "完全不收费" not in v][:2]) or "（待补）"
    return {
        "项目名称": f"{track['name']}创业项目",
        "问题与痛点": f"面向{cs}，解决「{pains}」的痛点",
        "解决方案": f"价值主张：{vp}；收入来源：{rs}",
        "市场机会": f"需求指数 {track['demand_idx']}，行业乘数 {track['multiplier']} 倍（{track['sea']}）",
        "商业模式": "单价×订单量−变动成本−渠道成本−固定成本，月结算滚动",
    }


# ============================================================================
# 三、UI 工具函数
# ============================================================================
def md_html(s):
    lines = [ln.strip() for ln in str(s).splitlines()]
    return st.markdown("\n".join(lines), unsafe_allow_html=True)


def css():
    st.markdown("""
    <style>
    .main {background: linear-gradient(160deg,#f5f7ff 0%, #eef3fb 100%);}
    .block-container {padding-top: 1.4rem;}
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.92); border-radius: 14px; padding: 12px 14px;
        box-shadow: 0 2px 10px rgba(30,60,140,0.08); border: 1px solid #e3e9f7;
    }
    div[data-testid="stMetricLabel"] {font-size: 0.86rem; color:#5a6b8c;}
    /* 顶部板块导航 tab 化（横向平铺、选中高亮） */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 8px; flex-wrap: wrap; margin-bottom: 2px;
    }
    div[data-testid="stRadio"] label {
        background: #ffffff; border: 1px solid #e3e9f7; border-radius: 999px;
        padding: 8px 20px; cursor: pointer; transition: all .15s ease;
    }
    div[data-testid="stRadio"] label div {display:none;}   /* 隐藏圆点，纯 tab 视觉 */
    div[data-testid="stRadio"] label:hover {border-color:#9db5f5; background:#f4f7ff;}
    div[data-testid="stRadio"] label:has(input:checked) {
        background: #1f3a93; border-color: #1f3a93; box-shadow: 0 4px 12px rgba(31,58,147,.22);
    }
    div[data-testid="stRadio"] label:has(input:checked) span {color:#fff; font-weight:600;}
    /* 侧边栏四因子紧凑卡片 */
    [data-testid="stSidebar"] div[data-testid="stMetric"] {
        padding: 8px 10px; border-radius: 10px;
    }
    [data-testid="stSidebar"] div[data-testid="stMetricLabel"] {font-size:.78rem;}
    [data-testid="stSidebar"] div[data-testid="stMetricValue"] {font-size:1.02rem;}
    .banner {
        background: linear-gradient(120deg,#1f3a93,#3f6df5); color:#fff; border-radius: 16px;
        padding: 22px 26px; box-shadow: 0 6px 22px rgba(31,58,147,0.25); margin-bottom: 10px;
    }
    .banner h1 {margin:0; font-size: 1.55rem; line-height:1.35;}
    .banner p {margin:8px 0 0; opacity:.92; font-size:.95rem;}
    .stepcard {
        background: #fff; border-radius: 14px; padding: 16px 18px; margin: 8px 0;
        border: 1px solid #e6ebf6; box-shadow: 0 2px 8px rgba(30,60,140,0.06);
    }
    .tag {display:inline-block; background:#eef3ff; color:#1f3a93; border-radius:20px;
        padding: 2px 10px; font-size:.78rem; margin:2px;}
    .redline {background:#fff1f0; border:1px solid #ffccc7; border-radius:12px; padding:10px 14px; margin:6px 0;}
    .goodline {background:#f0fff4; border:1px solid #b7eb8f; border-radius:12px; padding:10px 14px; margin:6px 0;}
    div[data-testid="stExpander"] {background:#fff; border-radius:12px; border:1px solid #e6ebf6;}
    </style>
    """, unsafe_allow_html=True)


def factor_dashboard(state):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 现金（元）", f"{state['cash']:,.0f}")
    c2.metric("👥 客户数", f"{state['customers']:,}")
    c3.metric("📈 月毛利（元）", f"{state['gross_margin']:,.0f}")
    c4.metric("🏆 路演/计划书分", f"{state['pitch_score']:.0f}")
    if state["month_records"]:
        df = pd.DataFrame(state["month_records"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["month"], y=df["cash"], name="现金", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df["month"], y=df["customers"], name="客户数", yaxis="y2", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=df["month"], y=df["gm"], name="月毛利", yaxis="y3", mode="lines+markers"))
        fig.update_layout(
            height=240, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white",
            title="四因子月度走势", legend=dict(orientation="h", y=1.12),
            yaxis=dict(title="现金/毛利"), yaxis2=dict(title="客户数", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)


def redline_banner(state):
    for r in state.get("redline_log", []):
        st.warning(f"🚨 {r}")


def sidebar_nav(state):
    """左侧导航栏：常驻四因子 + 26 步实验导航（板块导航已移至页面上方）"""
    with st.sidebar:
        st.markdown("#### 📊 四因子（实时）")
        c1, c2 = st.columns(2)
        c1.metric("现金（元）", f"{state['cash']:,.0f}")
        c2.metric("客户数", f"{state['customers']:,}")
        c3, c4 = st.columns(2)
        c3.metric("月毛利（元）", f"{state['gross_margin']:,.0f}")
        c4.metric("路演分", f"{state['pitch_score']:.0f}")
        st.markdown("---")
        st.markdown("### 🧭 实验导航")
        if st.session_state.get("nav_section") == "🧭 决策台" and state.get("started"):
            step_labels = [f"第{i}步 {n}" for i, n, _, _ in STEPS]
            sel = st.radio("步骤跳转", step_labels, key="nav_step",
                           label_visibility="collapsed")
            state["step"] = step_labels.index(sel) + 1
        else:
            st.caption("进入决策台并开始实验后，这里显示 26 步导航")
        st.markdown("---")
        st.caption(f"应用版本 {APP_VERSION} · 四因子算账闭环")
        st.caption("决策有代价，选择需谨慎 🎯")


def audit_append(state, step_no, name, choice, impact):
    """审计留痕（连续重复的同一操作只记一次）"""
    if state["audit"] and state["audit"][-1]["step"] == step_no and state["audit"][-1]["choice"] == choice:
        return
    state["audit"].append({
        "step": step_no, "name": name, "choice": choice, "impact": impact,
        "time": datetime.now().strftime("%H:%M:%S"),
    })


def goto_step(state, n):
    state["step"] = max(1, min(26, n))


# ============================================================================
# 四、决策台：26 步
# ============================================================================
def render_landing(state):
    st.markdown('<div class="banner"><h1>🪙 双创决策沙盘</h1>'
                '<p>从商业画布 → 4P作战 → 计划书路演的算账闭环 · 虚拟仿真实验 V1.1</p></div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 启动资金", "100万")
    c2.metric("🗓 经营周期", "4 个月")
    c3.metric("🎯 通关目标", "估值≥150万")
    st.markdown("### 📜 你的绩效契约（开局必读）")
    st.info("你以 **初创公司 CEO** 身份入场：100 万元虚拟启动资金、4 个月经营周期。"
            "目标：第 4 月末 **估值 ≥ 150 万 且 现金 > 0 且 客户数 ≥ 1000**。"
            "每一步卡片选择、滑块定价、预算投放都会即时改变 **现金 / 客户数 / 毛利 / 评分** 四项指标。")
    st.markdown("### 🗺 实验地图（26 步）")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("**① 开局决策**（第1-5步）\n\n赛道·痛点·画像·市场")
    with m2:
        st.markdown("**② 商业画布**（第6-14步）\n\n九格卡片化+成本结构")
    with m3:
        st.markdown("**③ 4P作战**（第15-20步）\n\nMVP·定价·渠道·促销·结算")
    with m4:
        st.markdown("**④ 计划书与路演**（第21-26步）\n\n风险事件·计划书·AI判定·路演")
    st.markdown("### 🚨 三条红线")
    st.markdown('<div class="redline">🩸 <b>资金红线</b>：现金≤0 且融资失败 → 破产终止<br>'
                '🩸 <b>合规红线</b>：无资质经营金融/医疗/食品类 → 直接失败<br>'
                '🩸 <b>画布红线</b>：价值主张空话 且 收入来源=0 → 不能进入4P</div>', unsafe_allow_html=True)
    with st.expander("💡 小白化词条库（20 个）"):
        for term, one, case, sample in GLOSSARY:
            st.markdown(f"**{term}**：{one} ｜ 案例：{case} ｜ 本题：{sample}")
    if st.button("🚀 开始实验（进入第1步）", key="launch", type="primary", use_container_width=True):
        if not state.get("started"):
            state["started"] = True
            state["step"] = 1
            audit_append(state, 0, "开始实验", "点击开始", "实验启动")
        st.session_state["_go_deck"] = True
        st.rerun()


def settle_remaining(state, decisions, track):
    """兜底：跳步时按已确认（或默认）风险选项补齐未结算月份"""
    if state.get("compliance_fail"):
        return
    for k, opt_map in ((1, R1_OPTIONS), (2, R2_OPTIONS), (3, R3_OPTIONS)):
        m = k + 1
        if state["month"] >= m:
            continue
        opt = state.get("risks", {}).get(k)
        risk = opt_map.get(opt, {}) if opt else {}
        if risk.get("illegal"):
            continue
        settle_month(state, m, decisions, track, risk)


def render_step(state):
    step_no = state.get("step", 1)
    step_name, ctrl, full = STEPS[step_no - 1][1], STEPS[step_no - 1][2], STEPS[step_no - 1][3]
    d = state["decisions"]

    # 月度结算前置：第20步进入时自动结算 Month 1（4P 参数已锁定）
    if step_no == 20 and state["month"] == 0 and not state.get("finished"):
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        settle_month(state, 1, d, t)
        audit_append(state, 20, "月度结算", "Month 1 结算", f"现金 {state['cash']:,.0f} / 客户 {state['customers']}")

    st.markdown(f'<div class="banner"><h1>第 {step_no} 步 · {step_name}</h1>'
                f'<p>交互：{ctrl} ｜ 满分 {full} ｜ 当前进度 {step_no}/26</p></div>', unsafe_allow_html=True)
    redline_banner(state)
    factor_dashboard(state)

    if step_no == 1:
        st.markdown("### 📖 开局剧本与绩效契约")
        st.markdown("你是 **校园创新项目公司 CEO**。投资人给了你 100 万启动资金与 4 个月窗口期："
                    "**估值 ≥150 万、现金为正、客户数破千** 才能拿到下一轮融资。"
                    "记住三条红线：资金断裂、无资质经营、画布空话。")
        opt = st.radio("你的选择", ["仔细阅读剧本与契约（+2）", "直接跳过不看（−2）"], key="s1_read")
        d["s1_read"] = "仔细阅读剧本与契约（+2）" in opt
        audit_append(state, 1, "开局剧本", opt, "决策分+2" if d["s1_read"] else "决策分−2")

    elif step_no == 2:
        st.markdown("### 🎯 选赛道（4 张大卡，单选）")
        st.caption("赛道决定你的市场基准价、获客成本与行业乘数（估值倍数）。")
        track_choices = list(TRACKS.keys()) + ["我不确定，随便选一个"]
        opt = st.radio("赛道", track_choices, key="s2_track",
                       format_func=lambda x: x, label_visibility="collapsed")
        if opt != "我不确定，随便选一个":
            t = TRACKS[opt]
            st.markdown(f'<div class="stepcard"><span class="tag">{t["sea"]}</span> '
                        f'<span class="tag">基准价 {t["bench_price"]}元</span> '
                        f'<span class="tag">行业乘数 {t["multiplier"]}x</span> '
                        f'<span class="tag">需求指数 {t["demand_idx"]}</span><br>{t["hint"]}</div>',
                        unsafe_allow_html=True)
            d["track"] = t["name"]
            d["track_key"] = opt
        else:
            d["track"] = "盲选"
            d["track_key"] = ""
        audit_append(state, 2, "选赛道", opt, "确定市场方向")

    elif step_no == 3:
        track_name = d.get("track_key", "")
        pool = PAINS.get(d.get("track") or next(iter(PAINS)), PAINS["校园即时配送"])
        st.markdown("### 🩹 选痛点卡片（多选 ≥2）")
        if not track_name:
            st.warning("⚠️ 你还没有选择赛道，请先回到第2步选赛道。")
        else:
            st.caption(f"当前赛道：{d.get('track')} —— 从真实用户麻烦里挑至少 2 个痛点。")
            sel = st.pills("痛点", pool, key="s3_pains", selection_mode="multi",
                           label_visibility="collapsed") or []
            d["pains"] = sel
            if len(sel) == 1:
                st.warning("⚠️ 只选 1 个痛点 → 决策分 −2；选 ≥2 个才得满分。")
            audit_append(state, 3, "选痛点", "、".join(sel) if sel else "（空）", f"{len(sel)} 个")

    elif step_no == 4:
        track_name = d.get("track")
        st.markdown("### 👤 用户画像匹配（单选）")
        opt = st.radio("画像", PERSONAS, key="s4_persona", label_visibility="collapsed")
        d["persona"] = opt
        t = TRACKS.get(d.get("track_key"), TRACKS["🛵 校园即时配送"])
        if opt == t["prefer_persona"]:
            st.success(f"✅ 画像与赛道高度匹配（{t['name']} 的最优客群）→ +3")
        elif opt == t["conflict_persona"]:
            st.error(f"❌ 画像与痛点/赛道冲突（{t['name']} 与「{opt}」错位）→ −2")
        audit_append(state, 4, "用户画像", opt, "匹配判定")

    elif step_no == 5:
        st.markdown("### 🔍 市场扫描确认（单选）")
        st.markdown("以下市场情报已由系统探明：")
        for card in MARKET_CARDS:
            st.markdown(f"- ✅ {card}")
        opt = st.radio("你的选择", ["确认已掌握竞品价与需求指数（+2）", "跳过不看（+1）"], key="s5_market")
        d["market_confirmed"] = "确认已掌握竞品价与需求指数（+2）" in opt
        d["market_skipped"] = not d["market_confirmed"]
        audit_append(state, 5, "市场扫描", opt, "获取竞品价/需求指数")

    elif 6 <= step_no <= 14:
        render_canvas(state, step_no)

    elif step_no == 15:
        st.markdown("### 🧩 产品功能栈（MVP 取舍，多选恰好 3 个）")
        sel = st.pills("MVP 功能（选 3 个，>5 个成本暴涨）", MVP_FEATURES,
                       key="s15_mvp", selection_mode="multi", label_visibility="collapsed") or []
        d["mvp"] = sel
        if len(sel) == 3:
            st.success("✅ MVP 克制，先验证再砸钱 → +5")
        elif len(sel) > 5:
            st.error("❌ 功能超过 5 个 → 固定成本 ×1.8，成本暴涨！")
        elif len(sel) == 0:
            st.warning("⚠️ 至少选 1 个功能")
        audit_append(state, 15, "MVP取舍", "、".join(sel), f"{len(sel)} 个功能")

    elif step_no == 16:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        lo = int(t["bench_price"] * 0.4); hi = int(t["bench_price"] * 1.7)
        st.markdown(f"### 💲 定价（滑块，市场基准价 {t['bench_price']} 元）")
        st.caption("偏离基准价 ±40% 触发销量惩罚；价格决定单笔毛利与需求系数。")
        price = st.slider("客单价（元）", lo, hi, int(t["bench_price"]), key="s16_price")
        d["price"] = float(price)
        dev = _deviation(price, t["bench_price"])
        pf = price_factor(price, t["bench_price"])
        st.markdown(f"偏离基准 **{dev*100:+.0f}%** ｜ 需求系数 **{pf:.2f}**"
                    + (" ｜ 🚨 偏离>40% 销量惩罚！" if abs(dev) > 0.4 else ""))
        audit_append(state, 16, "定价", f"{price} 元", f"偏离 {dev*100:+.0f}%")

    elif step_no == 17:
        st.markdown("### 📢 渠道投放预算（3 个滑块，单位：万元）")
        st.caption("预算越高获客越多，但渠道成本同时压毛利——CAC 与单位经济要算清楚。")
        cols = st.columns(3)
        vals = []
        for i, (name, key) in enumerate(zip(CHANNEL_NAMES, CHANNEL_KEYS)):
            v = cols[i].slider(name, 0, 20, 3, key=f"s17_{key}")
            d[key] = v
            vals.append(v)
        total = sum(vals)
        st.metric("渠道总预算（万元）", f"{total} 万")
        if total == 0:
            st.warning("⚠️ 渠道投放为 0 → 无获客通路，4P 一致性判负")
        audit_append(state, 17, "渠道投放", f"线上{vals[0]}/地推{vals[1]}/代理{vals[2]} 万", f"合计 {total} 万")

    elif step_no == 18:
        st.markdown("### 🎁 促销组合（多选，≥2 个更佳）")
        sel = st.pills("促销", PROMOS, key="s18_promos", selection_mode="multi",
                       label_visibility="collapsed") or []
        d["promos"] = sel
        if len(sel) >= 2:
            st.success("✅ 促销组合丰富，获客系数 +12%/个（上限3个）")
        audit_append(state, 18, "促销组合", "、".join(sel) if sel else "（空）", f"{len(sel)} 个")

    elif step_no == 19:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🤖 4P 一致性校验（AI 逻辑裁判提示）")
        issues = consistency_issues(d, t)
        ai = ai_judge_canvas(d, t, state)
        state["ai_canvas"] = ai
        st.markdown(f"**AI 判定总分：{ai['total']} / 100**")
        if issues:
            st.warning("⚠️ 检测到 4P 自相矛盾：\n\n" + "\n\n".join(f"- {x}" for x in issues))
        else:
            st.success("✅ 4P 组合逻辑自洽，没有明显矛盾")
        opt = st.radio("你的选择", ["认真阅读 AI 提示并修正思路（+3）", "无视提示硬过（−2）"], key="s19_read")
        d["s19_read"] = "认真阅读 AI 提示并修正思路（+3）" in opt
        d["s19_ignored"] = not d["s19_read"]
        audit_append(state, 19, "4P一致性校验", opt, f"AI 总分 {ai['total']}")

    elif step_no == 20:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🧮 月度结算（Month 1）+ 同口径复盘表")
        st.success("✅ Month 1 已自动结算，四因子已刷新（见上方仪表盘与走势图）")
        st.markdown("**复盘表（上轮 vs 本轮，同口径）**")
        st.table(pd.DataFrame(state["month_records"]))
        st.caption("口径：收入=订单量×客单价；成本=变动成本+渠道成本+固定成本；毛利=收入−成本")

    elif step_no == 21:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🚨 R1 供应链/内容违规（Month 2 危机决策）")
        st.markdown("你的核心供应商突然断供，且内容物料被投诉夸大宣传。你怎么应对？")
        settled = state.get("risks", {}).get(1) is not None
        opt = st.radio("应对方案", list(R1_OPTIONS.keys()), key="s21_r1",
                       index=0 if not settled else list(R1_OPTIONS.keys()).index(state["risks"][1]),
                       disabled=settled)
        if st.button("✅ 确认应对方案并结算 Month 2", key="s21_confirm", type="primary",
                     disabled=settled, use_container_width=True):
            state["risks"][1] = opt
            d["r1"] = opt
            settle_month(state, 2, d, t, R1_OPTIONS[opt])
            audit_append(state, 21, "R1供应链", opt, f"Month2 结算 现金 {state['cash']:,.0f}")
            if R1_OPTIONS[opt].get("illegal"):
                st.error("⚠️ 你换用了无资质供应商——若在 R3 继续无资质经营，将触发合规红线直接失败！")
            st.rerun()
        if settled:
            st.success(f"✅ 已确认方案：「{state['risks'][1]}」→ Month 2 已结算（见上方仪表盘）")
            if R1_OPTIONS[state["risks"][1]].get("illegal"):
                st.error("⚠️ 已使用无资质供应商——若在 R3 继续无资质经营，将触发合规红线直接失败！")
        if state["cash"] <= 0:
            render_finance_redline(state)

    elif step_no == 22:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### ⚔️ R2 竞品降价/技术替代（Month 3 防守决策）")
        st.markdown("头部竞品突然降价 15%，并上线了 AI 配送调度。你的市场份额受到威胁。")
        settled = state.get("risks", {}).get(2) is not None
        opt = st.radio("防守方案", list(R2_OPTIONS.keys()), key="s22_r2",
                       index=0 if not settled else list(R2_OPTIONS.keys()).index(state["risks"][2]),
                       disabled=settled)
        if st.button("✅ 确认防守方案并结算 Month 3", key="s22_confirm", type="primary",
                     disabled=settled, use_container_width=True):
            state["risks"][2] = opt
            d["r2"] = opt
            settle_month(state, 3, d, t, R2_OPTIONS[opt])
            audit_append(state, 22, "R2竞品降价", opt, f"Month3 结算 客户 {state['customers']}")
            st.rerun()
        if settled:
            st.success(f"✅ 已确认方案：「{state['risks'][2]}」→ Month 3 已结算（见上方仪表盘）")
        if state["cash"] <= 0:
            render_finance_redline(state)

    elif step_no == 23:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🧾 R3 政策合规（Month 4 合规红线）")
        st.markdown("监管部门要求相关业务必须持证经营（食品/医疗/金融类资质）。你如何决策？")
        settled = state.get("risks", {}).get(3) is not None
        opt = st.radio("合规方案", list(R3_OPTIONS.keys()), key="s23_r3",
                       index=0 if not settled else list(R3_OPTIONS.keys()).index(state["risks"][3]),
                       disabled=settled)
        if st.button("✅ 确认合规方案并结算 Month 4", key="s23_confirm", type="primary",
                     disabled=settled, use_container_width=True):
            if R3_OPTIONS[opt].get("illegal"):
                state["compliance_fail"] = True
                state["finished"] = True
                state["redline_log"].append("合规红线触发：无资质经营 → 实验直接失败")
                audit_append(state, 23, "R3政策合规", opt, "合规红线·实验失败")
                st.rerun()
            state["risks"][3] = opt
            d["r3"] = opt
            settle_month(state, 4, d, t, R3_OPTIONS[opt])
            audit_append(state, 23, "R3政策合规", opt, f"Month4 结算 现金 {state['cash']:,.0f}")
            st.rerun()
        if settled:
            st.success(f"✅ 已确认方案：「{state['risks'][3]}」→ Month 4 已结算（见上方仪表盘）")
        if state.get("compliance_fail"):
            st.error("🚨 合规红线触发：无资质经营金融/医疗/食品类业务 → **实验直接失败**！")
        if state["cash"] <= 0 and not state.get("compliance_fail"):
            render_finance_redline(state)

    elif step_no == 24:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 📝 计划书草稿补全（骨架已自动灌入）")
        auto = build_plan_autofill(d, t)
        state["plan_auto"] = auto
        with st.expander("📄 系统已自动灌入的计划书骨架", expanded=True):
            for k, v in auto.items():
                st.markdown(f"**{k}**：{v}")
        cols = st.columns(2)
        with cols[0]:
            barrier = st.selectbox("壁垒（必写，否则路演分封顶60）", PLAN_FIELDS["壁垒"], key="s24_barrier")
            team = st.selectbox("团队", PLAN_FIELDS["团队"], key="s24_team")
        with cols[1]:
            use = st.selectbox("融资用途", PLAN_FIELDS["融资用途"], key="s24_use")
            risk = st.selectbox("风险与合规（必写）", PLAN_FIELDS["风险与合规"], key="s24_risk")
        state["plan"] = {"壁垒": barrier, "团队": team, "融资用途": use, "风险与合规": risk}
        cheat = detect_cheat(barrier + use)
        if cheat:
            st.error("🚨 刷分红线：检测到复制粘贴通用套话，请重写本模块！")
        d["plan_done"] = True
        audit_append(state, 24, "计划书补全", f"壁垒/风险已填", "")

    elif step_no == 25:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🤖 A 判计划书（AI 五维判定 + 提分建议）")
        ai = ai_judge_plan(state, t, d)
        state["ai_plan"] = ai
        st.markdown(f"**计划书质量总分：{ai['total']} / 100**")
        for dim, score in ai["scores"].items():
            st.progress(int(score), text=f"{dim}：{score}")
        st.caption("维度权重：问题真实25% / 模型自洽25% / 数据可信20% / 壁垒与风险20% / 表达结构10%")
        if ai["suggestions"]:
            st.info("💡 提分建议：\n\n" + "\n\n".join(f"- {x}" for x in ai["suggestions"]))

    elif step_no == 26:
        track_name = d.get("track_key", "🛵 校园即时配送")
        t = TRACKS.get(track_name, TRACKS["🛵 校园即时配送"])
        st.markdown("### 🎤 虚拟路演 + 终评")
        st.markdown("在虚拟路演厅向投资人做 3 分钟陈述并回答追问。")
        c1, c2 = st.columns(2)
        with c1:
            m1 = st.text_area("陈述·商业模式（一句话讲清怎么赚钱）", key="s26_m1")
            m2 = st.text_area("陈述·数据（市场/客户/财务假设）", key="s26_m2")
        with c2:
            m3 = st.text_area("陈述·壁垒与风险（凭什么赢）", key="s26_m3")
            qa = st.radio("评委追问应对", [
                "数据与财务细节（答得有理有据）",
                "泛泛而谈（答非所问）",
                "直接卡壳（没有准备）",
            ], key="s26_qa")
        state["roadshow"] = {"陈述模式": m1, "陈述数据": m2, "陈述壁垒": m3}
        d["roadshow_qa"] = qa
        if st.button("🎉 提交路演并完成实验", key="s26_submit", type="primary", use_container_width=True):
            finish_experiment(state, d, t)
        if state.get("finished"):
            render_final_report(state, d, t)
    else:
        st.write(f"步骤 {step_no}")

    # 底部分页按钮（画布红线拦截 + 破产拦截）
    render_pager(state, step_no)


def render_canvas(state, step_no):
    """第 6-14 步：商业画布九格"""
    d = state["decisions"]
    cell_map = {
        6: "客户细分", 7: "价值主张", 8: "渠道通路", 9: "客户关系", 10: "收入来源",
        11: "关键资源", 12: "关键业务", 13: "重要伙伴", 14: "成本结构",
    }
    cell = cell_map[step_no]
    if step_no == 14:
        st.markdown("### ⚖️ 画布⑨ 成本结构分配（5 个滑块，合计必须 = 100%）")
        st.caption("研发/营销/人力/合规/场地占比——合计超/不足 100% 将无法进入 4P 阶段。")
        cols = st.columns(5)
        alloc = {}
        for i, name in enumerate(["研发", "营销", "人力", "合规", "场地"]):
            alloc[name] = cols[i].slider(f"{name}%", 0, 100, 20, key=f"s14_{name}")
        total = sum(alloc.values())
        st.metric("合计", f"{total}%", delta="✅ 100%" if total == 100 else f"还需 {'+' if total < 100 else '−'}{abs(100-total)}%")
        d["cost_alloc"] = alloc
        if total != 100:
            st.error("🚨 成本结构合计必须等于 100%——超/不足将归零，无法进入 4P！")
        audit_append(state, 14, "成本结构", f"研发{alloc['研发']}%营销{alloc['营销']}%人力{alloc['人力']}%合规{alloc['合规']}%场地{alloc['场地']}%", f"合计{total}%")
    else:
        pool = CANVAS_POOLS[cell]
        st.markdown(f"### 🗂 画布 {step_no-5} · {cell}"
                    + ("（单选）" if step_no == 9 else "（多选卡片）"))
        st.caption("卡片化交互：把最贴合你方案的卡片勾选进画布格。")
        if step_no == 9:
            sel_one = st.radio(cell, pool, key=f"s{step_no}_{cell}", label_visibility="collapsed")
            sel = [sel_one] if sel_one else []
        else:
            sel = st.pills(cell, pool, key=f"s{step_no}_{cell}", selection_mode="multi",
                           label_visibility="collapsed") or []
        d[f"canvas_{cell}"] = sel
        if step_no == 7:
            empty = [v for v in sel if v in EMPTY_TALK]
            if empty:
                st.warning(f"⚠️ AI 弹改：{empty[0]} 属于空话，缺少具体依据（逻辑裁判会给低分）")
            if not sel:
                st.warning("⚠️ 价值主张为空 → 画布逻辑分 0")
        if step_no == 10:
            if "完全不收费（收入=0）" in sel:
                st.error("🚨 收入来源=0：若价值主张同时是空话 → 触发画布红线，无法进入 4P！")
        if step_no == 6 and not sel:
            st.warning("⚠️ 客户细分为空 → 画布锁死，需至少勾选 1 项")
        audit_append(state, step_no, f"画布·{cell}", "、".join(sel) if sel else "（空）", f"{len(sel)} 项")


def render_finance_redline(state):
    """资金红线：现金≤0 时触发融资/破产决策"""
    if state.get("financed"):
        return
    st.error("🚨 **资金红线触发**：现金 ≤ 0！")
    opt = st.radio("融资决策", ["向投资人融资 50 万（利息 10 万，一次性）", "放弃融资 → 破产终止"], key="fin_opt")
    if st.button("确认融资决策", key="fin_confirm"):
        if "融资 50 万" in opt:
            state["cash"] = round(state["cash"] + 500000 - 100000, 1)
            state["financed"] = True
            state["redline_log"].append("资金红线：完成融资 50 万（利息10万），实验继续")
            audit_append(state, state.get("step", 0), "资金红线融资", opt, f"现金 {state['cash']:,.0f}")
        else:
            state["bankrupt"] = True
            state["finished"] = True
            state["redline_log"].append("资金红线触发：破产终止")
            audit_append(state, state.get("step", 0), "资金红线破产", opt, "实验终止")
        st.rerun()


def step_label(n):
    i, name, _, _ = STEPS[n - 1]
    return f"第{i}步 {name}"


def render_pager(state, step_no):
    """底部上一步/下一步（与侧边栏 nav_step 同步）"""
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    blocked = False
    if state.get("blocked_canvas") or canvas_redline(state["decisions"]):
        blocked = True
        st.error("🚨 画布红线：价值主张空话 且 收入来源=0 → **不允许进入 4P 阶段**，请回第7/10步修正！")
    if state.get("bankrupt") or state.get("compliance_fail"):
        blocked = True
    with c1:
        if step_no > 1 and st.button("⬅ 上一步", key="prev_step", use_container_width=True):
            st.session_state["_go_step"] = step_no - 1
            st.rerun()
    with c3:
        if step_no < 26:
            can_next = True
            if step_no == 14:
                alloc = state["decisions"].get("cost_alloc", {})
                if alloc and abs(sum(alloc.values()) - 100) > 0.01:
                    can_next = False
                    st.error("成本结构合计必须 = 100% 才能进入 4P")
            if blocked:
                can_next = False
            if can_next and st.button("下一步 ➡", key="next_step", type="primary", use_container_width=True):
                st.session_state["_go_step"] = step_no + 1
                st.session_state["_done_notice"] = f"🎉 第 {step_no} 步「{STEPS[step_no-1][1]}」已完成，进入下一步"
                st.rerun()
        else:
            st.caption("最后一环：提交路演后查看终评")


def finish_experiment(state, d, track):
    """终评：估值、通关、七模块总分、等级"""
    settle_remaining(state, d, track)   # 跳步兜底：补齐未结算月份
    state["canvas_logic_score"] = canvas_logic_score(d)
    state["blocked_canvas"] = canvas_redline(d)
    ai_c = state.get("ai_canvas") or ai_judge_canvas(d, track, state)
    state["ai_canvas"] = ai_c
    if not state.get("ai_plan"):
        state["ai_plan"] = ai_judge_plan(state, track, d)
    ps, has_br = roadshow_score(state, d)
    state["pitch_score"] = ps
    check_pass_goal(state, d, track)
    scores, total, grade = compute_scores(state, d, track)
    state["scores"], state["total_score"], state["grade"] = scores, total, grade
    state["finished"] = True
    audit_append(state, 26, "虚拟路演+终评", "提交", f"总分 {total} · {grade}")


def render_final_report(state, d, track):
    st.markdown("---")
    st.markdown('<div class="banner"><h1>🎉 终局报告</h1></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("估值（元）", f"{state['valuation']:,.0f}")
    c2.metric("现金（元）", f"{state['cash']:,.0f}")
    c3.metric("客户数", f"{state['customers']:,}")
    c4.metric("总分", f"{state['total_score']}")
    if state.get("bankrupt"):
        st.error("💀 破产终止：资金红线触发，实验失败。")
    if state.get("compliance_fail"):
        st.error("💀 合规红线触发：无资质经营，实验直接失败。")
    if state.get("pass_goal"):
        st.success("🏆 通关成功：估值≥150万 且 现金>0 且 客户数≥1000！下一轮融资到手！")
    else:
        st.warning("⚠️ 未达成通关目标（估值≥150万 且 现金>0 且 客户数≥1000）")
    st.markdown("#### 📊 七模块得分（满分100）")
    df_score = pd.DataFrame([
        {"模块": k, "得分": v} for k, v in state["scores"].items()
    ] + [{"模块": "总分", "得分": state["total_score"]}])
    st.table(df_score)
    grade_color = {"优秀": "#52c41a", "合格": "#faad14", "不合格": "#f5222d"}
    st.markdown(f"**终局评定：<span style='color:{grade_color.get(state['grade'],'#333')};font-size:1.4rem'>"
                f"{state['grade']}</span>**", unsafe_allow_html=True)
    with st.expander("📋 完整审计日志"):
        st.table(pd.DataFrame(state["audit"]))
    csv = pd.DataFrame(state["audit"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ 导出决策审计 CSV", csv, "shuangchuang_audit.csv", "text/csv", key="dl_csv")
    if st.button("🔄 重新开始", key="restart"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ============================================================================
# 五、报告板块
# ============================================================================
def render_review(state, d, track):
    st.markdown('<div class="banner"><h1>📋 复盘报告</h1></div>', unsafe_allow_html=True)
    if not state.get("month_records"):
        st.info("尚未完成月度结算，先到决策台跑到第20步。")
        return
    st.markdown("#### 四因子月度走势")
    factor_dashboard(state)
    st.markdown("#### 决策—后果复盘")
    for rec in state["audit"][-18:]:
        st.markdown(f"- **第{rec['step']}步 {rec['name']}**：{rec['choice']}（{rec['impact']}）")
    st.markdown("#### 同口径复盘表（上轮 vs 本轮）")
    st.table(pd.DataFrame(state["month_records"]))


def render_profile(state, d, track):
    st.markdown('<div class="banner"><h1>🛡 能力画像</h1></div>', unsafe_allow_html=True)
    ai = state.get("ai_canvas") or (ai_judge_canvas(d, track, state) if state.get("started") else None)
    if not ai:
        st.info("完成决策台后此处生成五维能力雷达。")
        return
    dims = ["价值主张真实性", "4P一致性", "单位经济可行", "画布完整度", "合规风险覆盖"]
    vals = [ai["scores"][k] for k in dims]
    fig = go.Figure(go.Scatterpolar(r=vals, theta=dims, fill="toself",
                                    line_color="#3f6df5", fillcolor="rgba(63,109,245,0.25)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                      height=420, margin=dict(l=40, r=40, t=30, b=20), title="能力雷达（AI 逻辑裁判）")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### 提分建议")
    for s in ai["suggestions"]:
        st.markdown(f"- {s}")


def render_report(state, d, track):
    st.markdown('<div class="banner"><h1>📄 经营决策报告</h1></div>', unsafe_allow_html=True)
    if not state.get("finished"):
        st.info("完成第 26 步路演提交后生成完整报告。")
        return
    render_final_report(state, d, track)


# ============================================================================
# 六、主流程
# ============================================================================
def main():
    css()
    # 在 widget 实例化前同步板块/步骤跳转
    if st.session_state.pop("_go_deck", False):
        st.session_state["nav_section"] = "🧭 决策台"
    go_step = st.session_state.pop("_go_step", None)
    if go_step:
        st.session_state["nav_step"] = step_label(go_step)
    done_notice = st.session_state.pop("_done_notice", None)
    state = st.session_state
    if "engine" not in state:
        state["engine"] = init_state()
    eng = state["engine"]
    if go_step:
        eng["step"] = go_step
    if "step" not in state:
        state["step"] = 1

    # 页面上方：实验导航（横向平铺 tab）
    st.markdown("### 🧭 实验导航")
    st.radio("板块", SECTIONS, key="nav_section", horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    if done_notice:
        st.success(done_notice)

    sidebar_nav(eng)
    section = st.session_state.get("nav_section", SECTIONS[0])

    if section == "🏠 实验导览":
        render_landing(eng)
    elif section == "🧭 决策台":
        if not eng.get("started"):
            render_landing(eng)
        else:
            render_step(eng)
    elif section == "📋 复盘报告":
        render_review(eng, eng["decisions"], TRACKS.get(eng["decisions"].get("track_key"), TRACKS["🛵 校园即时配送"]))
    elif section == "🛡 能力画像":
        render_profile(eng, eng["decisions"], TRACKS.get(eng["decisions"].get("track_key"), TRACKS["🛵 校园即时配送"]))
    elif section == "📄 经营决策报告":
        render_report(eng, eng["decisions"], TRACKS.get(eng["decisions"].get("track_key"), TRACKS["🛵 校园即时配送"]))


if __name__ == "__main__":
    main()
