# -*- coding: utf-8 -*-
"""AppTest 端到端：驱动真实 Streamlit widget 跑通 26 步全流程 + 报告板块。
运行：python test_apptest.py，ALL PASS 才可推送。
"""
import sys, os
sys.path.insert(0, r"C:\Users\孔鑫璇\Doubao\chats\2026-10-21\new-chat-2\app-src")
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-21\new-chat-2\app-src\main_app.py"
fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + info if info else ""))
    if not cond:
        fails.append(name)

def by_key(seq, key):
    return [x for x in seq if getattr(x, "key", None) == key]

def all_text(at, seq_names=("markdown", "success", "info", "caption", "warning", "error")):
    parts = []
    for s in seq_names:
        try:
            for el in getattr(at, s):
                v = getattr(el, "value", None)
                if v:
                    parts.append(str(v))
        except Exception:
            pass
    return " ".join(parts)

def next_step(at):
    by_key(at.button, "next_step")[0].click()
    at.run()

# ============ 主流程：26 步全走 ============
at = AppTest.from_file(APP, default_timeout=120)
at.run()
check("着陆页出现应用名", "双创决策沙盘" in all_text(at))
check("着陆页有绩效契约", "绩效契约" in all_text(at))

by_key(at.button, "launch")[0].click(); at.run()
check("进入第1步", "第 1 步 · 开局剧本与契约" in all_text(at))

# 1 开局
by_key(at.radio, "s1_read")[0].set_value("仔细阅读剧本与契约（+2）"); at.run()
next_step(at)
check("进入第2步", "第 2 步 · 选赛道" in all_text(at))

# 2 赛道
by_key(at.radio, "s2_track")[0].set_value("🛵 校园即时配送"); at.run()
next_step(at)
check("进入第3步", "第 3 步 · 选痛点卡片" in all_text(at))

# 3 痛点
by_key(at.multiselect, "s3_pains")[0].set_value([
    "下课10分钟没饭吃，排队太久", "外卖送到宿舍楼下不让进，取餐麻烦"]); at.run()
next_step(at)
check("进入第4步", "第 4 步 · 用户画像匹配" in all_text(at))

# 4 画像
by_key(at.radio, "s4_persona")[0].set_value("大一大二新生（价格敏感）"); at.run()
next_step(at)
check("进入第5步", "第 5 步 · 市场扫描确认" in all_text(at))

# 5 市场
by_key(at.radio, "s5_market")[0].set_value("确认已掌握竞品价与需求指数（+2）"); at.run()
next_step(at)
check("进入第6步", "画布①客户细分" in all_text(at))

# 6-13 画布八格
canvas_sets = {
    "s6_客户细分": ["大一新生", "考研/考证党"],
    "s7_价值主张": ["30分钟必达（具体承诺）", "比食堂/竞品便宜2元（价格锚点）"],
    "s8_渠道通路": ["小红书种草", "微信小程序"],
    "s9_客户关系": "会员积分体系",            # radio 单选
    "s10_收入来源": ["每单配送/服务费", "会员订阅（9.9元/月）"],
    "s11_关键资源": ["自建配送/服务团队", "小程序系统"],
    "s12_关键业务": ["接单与派单", "质量控制"],
    "s13_重要伙伴": ["食堂/商家", "宿舍楼长"],
}
for key, val in canvas_sets.items():
    if isinstance(val, list):
        by_key(at.multiselect, key)[0].set_value(val)
    else:
        by_key(at.radio, key)[0].set_value(val)
    at.run()
    next_step(at)

check("进入第14步", "画布⑨ 成本结构分配" in all_text(at))
# 14 成本结构 5 滑块合计 100
for k in ("s14_研发", "s14_营销", "s14_人力", "s14_合规", "s14_场地"):
    by_key(at.slider, k)[0].set_value(20)
at.run()
next_step(at)
check("进入第15步", "产品功能栈" in all_text(at))

# 15 MVP
by_key(at.multiselect, "s15_mvp")[0].set_value(["下单小程序", "实时定位配送", "智能拼单"]); at.run()
next_step(at)
check("进入第16步", "定价" in all_text(at))

# 16 定价 10 元（高于基准，策略性提价）
by_key(at.slider, "s16_price")[0].set_value(10); at.run()
next_step(at)
check("进入第17步", "渠道投放预算" in all_text(at))

# 17 渠道
for k, v in (("s17_ch_online", 5), ("s17_ch_ground", 5), ("s17_ch_agent", 5)):
    by_key(at.slider, k)[0].set_value(v)
at.run()
next_step(at)
check("进入第18步", "促销组合" in all_text(at))

# 18 促销
by_key(at.multiselect, "s18_promos")[0].set_value(["首单立减3元", "分享裂变红包"]); at.run()
next_step(at)
check("进入第19步", "4P 一致性校验" in all_text(at))
check("AI 裁判判定出现", "AI 判定总分" in all_text(at))

# 19 一致性
by_key(at.radio, "s19_read")[0].set_value("认真阅读 AI 提示并修正思路（+3）"); at.run()
next_step(at)
check("进入第20步", "月度结算（Month 1）" in all_text(at))
check("Month1 自动结算", "Month 1 已自动结算" in all_text(at))
next_step(at)
check("进入第21步", "R1 供应链" in all_text(at))

# 21 R1
by_key(at.radio, "s21_r1")[0].set_value("启动备用供应商预案（多花5万应急费，供应稳定）"); at.run()
by_key(at.button, "s21_confirm")[0].click(); at.run()
check("R1 已结算", "Month 2 已结算" in all_text(at))
next_step(at)
check("进入第22步", "R2 竞品降价" in all_text(at))

# 22 R2
by_key(at.radio, "s22_r2")[0].set_value("跟随降价10%（保客户，毛利下降）"); at.run()
by_key(at.button, "s22_confirm")[0].click(); at.run()
check("R2 已结算", "Month 3 已结算" in all_text(at))
next_step(at)
check("进入第23步", "R3 政策合规" in all_text(at))

# 23 R3
by_key(at.radio, "s23_r3")[0].set_value("补齐资质合规经营（一次性成本+8万）"); at.run()
by_key(at.button, "s23_confirm")[0].click(); at.run()
check("R3 已结算", "Month 4 已结算" in all_text(at))
next_step(at)
check("进入第24步", "计划书草稿补全" in all_text(at))

# 24 计划书
by_key(at.selectbox, "s24_barrier")[0].set_value("独家宿舍楼合作+配送算法")
by_key(at.selectbox, "s24_team")[0].set_value("创始团队3人，财务+技术+运营")
by_key(at.selectbox, "s24_use")[0].set_value("50%研发、30%市场、20%备付金")
by_key(at.selectbox, "s24_risk")[0].set_value("已识别资质/食品安全/知识产权风险并备案")
at.run()
next_step(at)
check("进入第25步", "A 判计划书" in all_text(at))
check("AI 五维判定出现", "计划书质量总分" in all_text(at))
next_step(at)
check("进入第26步", "虚拟路演" in all_text(at))

# 26 路演
by_key(at.text_area, "s26_m1")[0].set_value("我们做校园即时配送，按单收配送费，靠独家宿舍楼合作把送达压到30分钟")
by_key(at.text_area, "s26_m2")[0].set_value("需求指数82，月订单约7万单，客单价10元，单位毛利5元，CAC约3.5元")
by_key(at.text_area, "s26_m3")[0].set_value("独家宿舍楼合作加配送算法是壁垒，已备案食品资质与知识产权风险")
by_key(at.radio, "s26_qa")[0].set_value("数据与财务细节（答得有理有据）")
at.run()
by_key(at.button, "s26_submit")[0].click(); at.run()
check("终局报告出现", "终局报告" in all_text(at))
check("七模块得分表出现", len(at.table) >= 1, f"{len(at.table)} 张表")
check("总分指标出现", any(getattr(m_, "label", "") == "总分" for m_ in at.metric))
check("终局评定出现", "终局评定" in all_text(at))
check("通关/未通关出现", ("通关成功" in all_text(at)) or ("未达成通关目标" in all_text(at)))

# ============ 报告板块注入测试 ============
import importlib
mm = importlib.import_module("main_app")
eng = mm.init_state()
eng["started"] = True
eng["finished"] = True
eng["month"] = 4
eng["cash"] = 800000
eng["customers"] = 6000
eng["gross_margin"] = 120000
eng["valuation"] = 1600000
eng["total_score"] = 86
eng["grade"] = "优秀"
eng["pass_goal"] = True
eng["canvas_logic_score"] = 80
eng["pitch_score"] = 75
eng["month_records"] = [{"month": i, "cash": 1000000 - i * 30000, "customers": 2000 * i,
                         "gm": 50000 * i, "income": 200000 * i, "var_cost": 100000 * i,
                         "channel": 50000, "fixed": 30000, "new_c": 2000, "churn": 100}
                        for i in range(1, 5)]
eng["audit"] = [{"step": 1, "name": "开局", "choice": "仔细阅读", "impact": "+2", "time": "10:00:00"},
                {"step": 20, "name": "月度结算", "choice": "Month1", "impact": "ok", "time": "10:00:00"}]
eng["decisions"] = {"track_key": "🛵 校园即时配送", "track": "校园即时配送"}
eng["ai_canvas"] = {"scores": {"价值主张真实性": 85, "4P一致性": 88, "单位经济可行": 80,
                                "画布完整度": 90, "合规风险覆盖": 85}, "total": 85,
                    "suggestions": ["建议压缩渠道预算"]}
eng["ai_plan"] = {"total": 82, "scores": {}}
eng["scores"] = {"决策过程A": 18, "决策过程B": 17, "商业画布逻辑": 12,
                 "4P执行与一致性": 13, "风险控制": 9, "创业计划书": 8, "虚拟路演答辩": 9}
eng["roadshow"] = {"陈述模式": "a" * 80, "陈述数据": "b" * 80, "陈述壁垒": "c" * 80}
eng["plan"] = {"壁垒": "独家宿舍楼合作+配送算法", "团队": "创始团队3人",
               "融资用途": "50%研发", "风险与合规": mm.PLAN_LEGAL_RISK}

at2 = AppTest.from_file(APP, default_timeout=120)
at2.session_state["engine"] = eng
at2.session_state["step"] = 26
at2.session_state["nav_section"] = "📋 复盘报告"
at2.run()
check("复盘报告渲染", "复盘报告" in all_text(at2))
check("复盘报告有月份表", "同口径复盘表" in all_text(at2))

at3 = AppTest.from_file(APP, default_timeout=120)
at3.session_state["engine"] = eng
at3.session_state["step"] = 26
at3.session_state["nav_section"] = "🛡 能力画像"
at3.run()
check("能力画像渲染", "能力画像" in all_text(at3))
check("能力画像有提分建议", "提分建议" in all_text(at3))

at4 = AppTest.from_file(APP, default_timeout=120)
at4.session_state["engine"] = eng
at4.session_state["step"] = 26
at4.session_state["nav_section"] = "📄 经营决策报告"
at4.run()
check("经营决策报告渲染", "经营决策报告" in all_text(at4))
check("报告含总分指标", any(getattr(m_, "label", "") == "总分" for m_ in at4.metric))
check("报告含 CSV 导出", len(by_key(at4.download_button, "dl_csv")) == 1)

print("\n==== AppTest 结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
sys.exit(0 if not fails else 1)
