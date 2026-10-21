# -*- coding: utf-8 -*-
"""冒烟测试：streamlit stub 屏蔽顶层副作用后 exec_module，对引擎纯函数加断言。
运行：python smoke_test.py，输出 ALL PASS 才可推送。
"""
import sys, importlib.util, types

APP = r"C:\Users\孔鑫璇\Doubao\chats\2026-10-21\new-chat-2\app-src\main_app.py"

class _Dummy:
    def __getattr__(self, k):
        return lambda *a, **kw: None
    def __setattr__(self, k, v):
        object.__setattr__(self, k, v)
    def __contains__(self, k):
        return True

class _StubMod(types.ModuleType):
    def __getattr__(self, k):
        return lambda *a, **kw: None

stub = _StubMod("streamlit")
stub.session_state = _Dummy()
sys.modules["streamlit"] = stub
sys.modules["pandas"] = importlib.import_module("pandas")
sys.modules["plotly"] = importlib.import_module("plotly")

spec = importlib.util.spec_from_file_location("main_app", APP)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + info if info else ""))
    if not cond:
        fails.append(name)

T = m.TRACKS["🛵 校园即时配送"]

# 1. 初始状态
st0 = m.init_state()
check("init_state 初始现金100万", st0["cash"] == 1_000_000, f"cash={st0['cash']}")

# 2. 定价偏离 → 需求系数惩罚
check("price_factor 基准价=1.0", abs(m.price_factor(8, 8) - 1.0) < 1e-6)
pf = m.price_factor(12, 8)   # +50% → 惩罚
check("price_factor 偏离>40% 惩罚", pf < 0.5, f"pf={pf:.3f}")

# 3. 画布逻辑分：好画布 vs 空话画布
good = {
    "canvas_价值主张": ["30分钟必达（具体承诺）", "比食堂/竞品便宜2元（价格锚点）"],
    "canvas_客户细分": ["大一新生", "考研/考证党"],
    "canvas_收入来源": ["每单配送/服务费", "会员订阅（9.9元/月）"],
    "canvas_渠道通路": ["小红书种草", "微信小程序"],
    "cost_alloc": {"研发": 30, "营销": 40, "人力": 20, "合规": 10, "场地": 0},
}
bad = {
    "canvas_价值主张": ["“赋能校园生态”（空话）"],
    "canvas_客户细分": [],
    "canvas_收入来源": ["完全不收费（收入=0）"],
    "canvas_渠道通路": [],
    "cost_alloc": {"研发": 50, "营销": 10, "人力": 20, "合规": 10, "场地": 10},
}
cs_good = m.canvas_logic_score(good)
cs_bad = m.canvas_logic_score(bad)
check("画布逻辑分：好画布 > 空话画布", cs_good > cs_bad, f"good={cs_good} bad={cs_bad}")
check("画布红线：空话+收入0 触发", m.canvas_redline(bad) is True)
check("画布红线：好画布不触发", m.canvas_redline(good) is False)

# 4. 结算：Month1 默认决策 → 客户增长、现金变化
stm = m.init_state()
dec = {"price": 8.0, "ch_online": 3, "ch_ground": 3, "ch_agent": 3,
       "promos": ["首单立减3元", "分享裂变红包"], "mvp": ["下单小程序", "实时定位配送", "智能拼单"]}
m.settle_month(stm, 1, dec, T)
check("Month1 客户数>0", stm["customers"] > 0, f"customers={stm['customers']}")
check("Month1 现金 < 初始（有固定成本）", stm["cash"] < 1_000_000, f"cash={stm['cash']:,.0f}")
check("Month1 有月份记录", len(stm["month_records"]) == 1)

# 5. MVP>5 → 固定成本暴涨
stm2 = m.init_state()
dec5 = dict(dec, mvp=["a", "b", "c", "d", "e", "f"])
m.settle_month(stm2, 1, dec5, T)
stm3 = m.init_state()
m.settle_month(stm3, 1, dec, T)
check("MVP>5 固定成本更高（现金更低）", stm2["cash"] < stm3["cash"], f"mvp>5={stm2['cash']:,.0f} vs 3={stm3['cash']:,.0f}")

# 6. 4P 一致性
dec_high = dict(dec, price=12.0, ch_ground=0, ch_agent=0)   # 高价+无线下
issues = m.consistency_issues(dec_high, T)
check("4P一致性：高价+弱触达 检出矛盾", len(issues) >= 1, str(issues[:1]))

# 7. AI 逻辑裁判（节点1）
ai1 = m.ai_judge_canvas(good, T, m.init_state())
check("AI裁判 五维齐全", set(ai1["scores"].keys()) == {"价值主张真实性", "4P一致性", "单位经济可行", "画布完整度", "合规风险覆盖"})
check("AI裁判 total 在0-100", 0 <= ai1["total"] <= 100, f"total={ai1['total']}")

# 8. AI 提分教练（节点2）
st_plan = m.init_state()
st_plan["plan"] = {"壁垒": "独家宿舍楼合作+配送算法", "团队": "创始团队3人",
                   "融资用途": "50%研发、30%市场", "风险与合规": m.PLAN_LEGAL_RISK}
st_plan["decisions"] = dec
ai2 = m.ai_judge_plan(st_plan, T, dec)
check("AI教练 五维齐全", set(ai2["scores"].keys()) == {"问题真实", "商业模型自洽", "数据可信", "壁垒与风险", "表达与结构"})
check("AI教练 total 在0-100", 0 <= ai2["total"] <= 100, f"total={ai2['total']}")

# 9. 估值公式
val = m.valuation({"gross_margin": 100000}, {}, T, 80, 70)
check("估值=毛利×乘数+画布×2000+路演×500", abs(val - (100000*10 + 80*2000 + 70*500)) < 0.01, f"val={val}")

# 10. 路演红线：无壁垒与风险 → 封顶60
st_rs = m.init_state()
st_rs["plan"] = {"壁垒": "暂时没有想好（留白）", "风险与合规": "暂无风险预案（留白）"}
st_rs["roadshow"] = {"陈述模式": "很长的陈述内容" * 20, "陈述数据": "很多数据" * 20, "陈述壁垒": "壁垒内容" * 20}
ps, has_br = m.roadshow_score(st_rs, {})
check("路演红线：无壁垒与风险 → 封顶60", ps <= 60 and not has_br, f"ps={ps}")

# 11. 通关判定
st_goal = m.init_state()
st_goal["cash"] = 200000; st_goal["customers"] = 3000; st_goal["gross_margin"] = 150000
st_goal["canvas_logic_score"] = 80; st_goal["pitch_score"] = 70
ok = m.check_pass_goal(st_goal, {}, T)
check("通关判定：估值≥150万且现金>0且客户≥1000", ok is True, f"val={st_goal['valuation']:,.0f}")
st_fail = m.init_state()
st_fail["cash"] = -1000; st_fail["customers"] = 3000; st_fail["gross_margin"] = 150000
st_fail["canvas_logic_score"] = 80; st_fail["pitch_score"] = 70
check("通关判定：现金<0 不通关", m.check_pass_goal(st_fail, {}, T) is False)

# 12. 评分体系：满分路径总分应达 100
st_score = m.init_state()
st_score["month"] = 4
st_score["month_records"] = [{"month": 1}]
st_score["canvas_logic_score"] = 100.0
st_score["ai_canvas"] = {"scores": {"4P一致性": 100}, "total": 100}
st_score["ai_plan"] = {"total": 100}
st_score["plan"] = {"壁垒": "独家宿舍楼合作+配送算法", "风险与合规": m.PLAN_LEGAL_RISK}
st_score["roadshow"] = {"陈述模式": "很长" * 30, "陈述数据": "很长" * 30, "陈述壁垒": "很长" * 30}
st_score["pitch_score"] = 100
dec_full = {
    "s1_read": True, "track": "校园即时配送", "pains": ["a", "b"],
    "persona": T["prefer_persona"], "market_confirmed": True,
    "mvp": ["a", "b", "c"], "price": 8.0,
    "ch_online": 5, "ch_ground": 5, "ch_agent": 5,
    "promos": ["a", "b"], "s19_read": True,
    "r1": list(m.R1_OPTIONS.keys())[0], "r2": list(m.R2_OPTIONS.keys())[0],
    "r3": list(m.R3_OPTIONS.keys())[0], "roadshow_qa": "数据与财务细节（答得有理有据）",
}
scores, total, grade = m.compute_scores(st_score, dec_full, T)
check("满分路径总分=100", total == 100, f"total={total} scores={scores}")
check("满分路径等级=优秀", grade == "优秀", grade)

# 13. 刷分检测
check("刷分检测：通用套话命中", m.detect_cheat("本项目致力于赋能校园生态，打造一站式闭环，积极响应号召，众所周知") is True)
check("刷分检测：正常文案不命中", m.detect_cheat("我们靠独家宿舍楼合作把送达时间压到30分钟") is False)

# 14. 反例命中分析（三类反例：决策错误/执行偏差/外部突变）
st_ce = m.init_state()
check("init_state 含 completed 空列表", st_ce.get("completed") == [], str(st_ce.get("completed")))
check("四幕分组覆盖26步", len(m.ACTS) == 4 and sum(e - s + 1 for _, _, s, e in m.ACTS) == 26,
      str([(t, s, e) for _, t, s, e in m.ACTS]))
st_ce["risks"] = {1: "启动备用供应商预案（多花5万应急费，供应稳定）",
                  2: "跟随降价10%（保客户，毛利下降）",
                  3: "补齐资质合规经营（一次性成本+8万）"}
st_ce["decisions"] = {
    "cost_alloc": {"研发": 30, "营销": 40, "人力": 20, "合规": 5, "场地": 5},
    "mvp": ["a", "b", "c"], "ch_online": 5, "ch_ground": 5, "ch_agent": 5,
    "persona": "大一大二新生（价格敏感）", "track_key": "🛵 校园即时配送",
    "canvas_价值主张": ["30分钟必达（具体承诺）"],
    "plan": {"壁垒": "独家宿舍楼合作+配送算法", "融资用途": "50%研发、30%市场、20%备付金"},
}
rows = m.analyze_counterexamples(st_ce, st_ce["decisions"], T)
cats = {r["类"] for r in rows}
check("反例分析覆盖三类", cats == {"决策错误", "执行偏差", "外部突变"}, str(sorted(cats)))
check("满分路径无反例命中", all(not r["命中"] for r in rows), str([r for r in rows if r["命中"]]))

st_bad = m.init_state()
st_bad["risks"] = {1: "换用无资质小作坊（便宜但风险高）", 2: "死扛不降价（客户大量流失）", 3: "无资质硬扛经营（合规红线→直接失败）"}
st_bad["redline_log"] = ["资金红线：完成融资 50 万（利息10万），实验继续", "合规红线触发：无资质经营 → 实验直接失败"]
st_bad["compliance_fail"] = True
st_bad["decisions"] = {
    "cost_alloc": {"研发": 60, "营销": 60, "人力": 20, "合规": 5, "场地": 5},
    "mvp": ["a", "b", "c", "d", "e", "f"], "ch_online": 30, "ch_ground": 0, "ch_agent": 0,
    "persona": "教职工与研究生（高客单、重品质）", "track_key": "🛵 校园即时配送",
    "canvas_价值主张": ["“赋能校园生态”（空话）"],
    "plan": {"壁垒": "本项目致力于赋能校园生态，打造一站式解决方案，积极响应号召，众所周知", "融资用途": "本项目致力于赋能校园生态，打造一站式解决方案"},
}
rows2 = m.analyze_counterexamples(st_bad, st_bad["decisions"], T)
hits2 = [r for r in rows2 if r["命中"]]
check("坏路径命中多个反例", len(hits2) >= 5, f"命中 {len(hits2)} 个: {[r['反例'] for r in hits2]}")

print("\n==== 冒烟结果:", "ALL PASS" if not fails else f"FAILED: {fails}", "====")
sys.exit(0 if not fails else 1)
