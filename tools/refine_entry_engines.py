from pathlib import Path
import re

p = Path('app.py')
text = p.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'missing target: {label}')
    text = text.replace(old, new, 1)


def replace_func(name, next_name, new_code):
    global text
    pattern = rf'def {re.escape(name)}\(.*?(?=\n\ndef {re.escape(next_name)}\()'
    new_text, n = re.subn(pattern, new_code.rstrip(), text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'function replace failed: {name} -> {next_name}, n={n}')
    text = new_text

# Add broad USD for gold engine.
replace_once(
    '    "US 10Y Real Yield": "DFII10",\n    "10Y-2Y Spread": "T10Y2Y",\n',
    '    "US 10Y Real Yield": "DFII10",\n    "Broad USD": "DTWEXBGS",\n    "10Y-2Y Spread": "T10Y2Y",\n',
    'Broad USD series',
)

replace_once(
    'real10 = fred["US 10Y Real Yield"]\nhy_oas = fred["HY OAS"]\n',
    'real10 = fred["US 10Y Real Yield"]\nbroad_usd = fred["Broad USD"]\nhy_oas = fred["HY OAS"]\n',
    'Broad USD transformed series',
)

# Add percentile helper after daily_lookback.
needle = '''def daily_lookback(s, n=20):\n    x = s.dropna()\n    return float(x.iloc[-1-n]) if len(x) > n else np.nan\n'''
insert = needle + '''\n\ndef rolling_percentile(s, n=252):\n    x = s.dropna().tail(n)\n    if len(x) < 60:\n        return np.nan\n    now = x.iloc[-1]\n    return float((x <= now).mean() * 100)\n'''
replace_once(needle, insert, 'rolling percentile helper')

replace_once(
    '    "real10y": latest_valid(real10),\n    "real10y_20dago": daily_lookback(real10, 20),\n    "hy_oas": latest_valid(hy_oas),\n',
    '    "real10y": latest_valid(real10),\n    "real10y_20dago": daily_lookback(real10, 20),\n    "us10y_pct_1y": rolling_percentile(dgs10),\n    "us30y_pct_1y": rolling_percentile(dgs30),\n    "broad_usd": latest_valid(broad_usd),\n    "broad_usd_20dago": daily_lookback(broad_usd, 20),\n    "hy_oas": latest_valid(hy_oas),\n',
    'macro snapshot additions',
)

# Replace rate_fit_score with equity/gold helper only; bonds get dedicated duration engine.
replace_func('rate_fit_score', 'macro_fit_score', r'''def rate_fit_score(asset_name, group, m):
    # 0~15 for equities; 0~30 real-rate score for gold. Bonds use bond_duration_score().
    u10, u10p = m.get("us10y"), m.get("us10y_20dago")
    rr, rrp = m.get("real10y"), m.get("real10y_20dago")
    d10 = u10 - u10p if pd.notna(u10) and pd.notna(u10p) else np.nan
    dr = rr - rrp if pd.notna(rr) and pd.notna(rrp) else np.nan

    if group == "Equity":
        p = 8
        if pd.notna(d10):
            if d10 <= -0.20: p += 4
            elif d10 <= -0.05: p += 2
            elif d10 >= 0.25: p -= 5
            elif d10 >= 0.10: p -= 2
        if asset_name == "Nasdaq 100" and pd.notna(dr):
            if dr <= -0.10: p += 3
            elif dr >= 0.15: p -= 4
        elif pd.notna(dr):
            if dr <= -0.10: p += 1
            elif dr >= 0.15: p -= 2
        return int(np.clip(p, 0, 15))

    if group == "Gold":
        p = 15
        if pd.notna(dr):
            if dr <= -0.20: p += 15
            elif dr <= -0.10: p += 11
            elif dr <= -0.03: p += 6
            elif dr >= 0.20: p -= 14
            elif dr >= 0.10: p -= 10
            elif dr >= 0.03: p -= 5
        return int(np.clip(p, 0, 30))

    return 0''')

# Replace macro score to make equity less restrictive; bonds still use this as backdrop.
replace_func('macro_fit_score', 'entry_decision', r'''def macro_fit_score(asset_name, group, macro_state, macro_regime, macro_bias, m):
    # Macro fit: Equity max 25, Bond max 25, Gold max 20.
    if group == "Equity":
        p = 13
        if macro_state.get("Growth") == "개선": p += 4
        elif macro_state.get("Growth") == "둔화": p -= 3
        if macro_state.get("Inflation") == "둔화": p += 3
        elif macro_state.get("Inflation") == "재가속": p -= 3
        if macro_state.get("Employment") == "견조": p += 2
        elif macro_state.get("Employment") == "빠른 악화": p -= 5
        if macro_state.get("Financial Conditions") == "완화/안정": p += 3
        elif macro_state.get("Financial Conditions") == "긴축/스트레스": p -= 3
        cap = 21 if asset_name in ["KOSPI", "Nifty 50"] else 25
        return int(np.clip(p, 0, cap))

    if group == "Bond":
        p = 8
        if macro_state.get("Inflation") == "둔화": p += 8
        elif macro_state.get("Inflation") == "혼조": p += 4
        elif macro_state.get("Inflation") == "재가속": p -= 7
        if macro_state.get("Growth") == "둔화": p += 5
        elif macro_state.get("Growth") == "횡보": p += 2
        elif macro_state.get("Growth") == "개선": p -= 2
        if macro_state.get("Employment") == "완만한 냉각": p += 4
        elif macro_state.get("Employment") == "빠른 악화": p += 6
        elif macro_state.get("Employment") == "견조": p += 1
        return int(np.clip(p, 0, 25))

    if group == "Gold":
        p = 10
        if "경착륙" in macro_regime: p += 5
        if "스태그플레이션" in macro_regime: p += 6
        if macro_state.get("Inflation") == "재가속": p += 2
        if macro_state.get("Financial Conditions") == "긴축/스트레스": p += 2
        return int(np.clip(p, 0, 20))

    return 10


def bond_duration_score(asset_name, row, macro_state, macro_regime, m):
    # Duration-first Treasury ETF engine, total 100.
    # 40 duration catalyst + 25 macro backdrop + 15 starting yield + 20 ETF confirmation/value.
    is_long = "Long" in asset_name
    y_now = m.get("us30y") if is_long else m.get("us10y")
    y_1m = m.get("us30y_20dago") if is_long else m.get("us10y_20dago")
    y_3m = m.get("us10y_60dago") if not is_long else np.nan
    y_pct = m.get("us30y_pct_1y") if is_long else m.get("us10y_pct_1y")

    d1 = y_now - y_1m if pd.notna(y_now) and pd.notna(y_1m) else np.nan
    # For 30Y, use 10Y 3M direction as a macro-duration confirmation when 30Y 60d history is not stored.
    d3 = (m.get("us10y") - m.get("us10y_60dago")) if is_long and pd.notna(m.get("us10y")) and pd.notna(m.get("us10y_60dago")) else (y_now - y_3m if pd.notna(y_now) and pd.notna(y_3m) else np.nan)
    d2 = m.get("us2y") - m.get("us2y_20dago") if pd.notna(m.get("us2y")) and pd.notna(m.get("us2y_20dago")) else np.nan
    dr = m.get("real10y") - m.get("real10y_20dago") if pd.notna(m.get("real10y")) and pd.notna(m.get("real10y_20dago")) else np.nan

    # A. Duration catalyst 0~40: actual long-yield reversal is primary.
    catalyst = 0
    if pd.notna(d1):
        if d1 <= -0.25: catalyst += 18
        elif d1 <= -0.15: catalyst += 15
        elif d1 <= -0.07: catalyst += 11
        elif d1 <= 0.03: catalyst += 7
        elif d1 <= 0.12: catalyst += 3
    if pd.notna(d3):
        if d3 <= -0.35: catalyst += 10
        elif d3 <= -0.15: catalyst += 8
        elif d3 <= 0.05: catalyst += 5
        elif d3 <= 0.20: catalyst += 2
    if pd.notna(d2):
        if d2 <= -0.20: catalyst += 7
        elif d2 <= -0.08: catalyst += 5
        elif d2 <= 0.03: catalyst += 3
    if pd.notna(dr):
        if dr <= -0.12: catalyst += 5
        elif dr <= -0.03: catalyst += 3
        elif dr >= 0.15: catalyst -= 3
    catalyst = int(np.clip(catalyst, 0, 40))

    # B. Macro rate-cut/disinflation backdrop 0~25.
    macro_pts = macro_fit_score(asset_name, "Bond", macro_state, macro_regime, "", m)

    # C. Starting yield attractiveness 0~15, using 1Y percentile rather than arbitrary absolute yield.
    if pd.isna(y_pct): yield_pts = 7
    elif y_pct >= 85: yield_pts = 15
    elif y_pct >= 70: yield_pts = 13
    elif y_pct >= 55: yield_pts = 10
    elif y_pct >= 40: yield_pts = 7
    elif y_pct >= 25: yield_pts = 4
    else: yield_pts = 2

    # D. ETF confirmation/value 0~20. Do NOT require MA200 up; that would enter too late.
    os = row.get("Oversold Score", np.nan)
    r1m = row.get("1M %", np.nan)
    r3m = row.get("3M %", np.nan)
    tech = 4
    if pd.notna(os): tech += min(int(os) * 2, 8)
    if pd.notna(r1m):
        if 0 < r1m <= 6: tech += 6       # early price confirmation
        elif -4 <= r1m <= 0: tech += 3   # still near lows, acceptable for probe
        elif r1m > 8: tech -= 2          # chasing after a sharp move
    if pd.notna(r3m) and r3m > 0: tech += 2
    tech = int(np.clip(tech, 0, 20))

    score = catalyst + macro_pts + yield_pts + tech

    # Hard risk guardrails: do not call a duration trade 'friendly' while yields/inflation are reaccelerating sharply.
    if pd.notna(d1) and d1 >= 0.25 and macro_state.get("Inflation") == "재가속":
        score = min(score, 49)
    elif pd.notna(d1) and d1 >= 0.15:
        score = min(score, 59)

    if score >= 70: action, css = "진입 우호", "action-good"
    elif score >= 55: action, css = "분할 진입", "action-mid"
    elif score >= 40: action, css = "정찰 / 대기", "action-watch"
    else: action, css = "대기", "action-wait"

    notes = [f"듀레이션 촉매 {catalyst}/40", f"거시 {macro_pts}/25", f"금리수준 {yield_pts}/15", f"ETF확인 {tech}/20"]
    if pd.notna(d1): notes.append(f"대상금리 1M {d1:+.2f}%p")
    if pd.notna(d2): notes.append(f"2Y 1M {d2:+.2f}%p")
    return {
        "Entry Score": int(score), "Action": action, "CSS": css,
        "Price Pts": tech, "Trend Pts": catalyst, "Macro Pts": macro_pts,
        "Rate Pts": catalyst + yield_pts, "Pullback Pts": tech,
        "Engine": "Duration",
        "Reason": " · ".join(notes),
    }''')

# Replace generic entry_decision with asset-specific branches.
replace_func('entry_decision', 'status_tone', r'''def entry_decision(row, macro_state, macro_regime, macro_bias, m):
    group, asset_name = row["분류"], row["자산"]

    if group == "Bond":
        return bond_duration_score(asset_name, row, macro_state, macro_regime, m)

    oversold = row.get("Oversold Score", np.nan)
    rsi = row.get("RSI14", np.nan)
    r1m = row.get("1M %", np.nan)
    trend_up = row.get("MA200 Trend") == "상승"

    if group == "Equity":
        # Less restrictive than the old engine: normal uptrends can qualify without being statistically oversold.
        if pd.isna(oversold): price_pts = 10
        else: price_pts = {0:10, 1:14, 2:18, 3:22, 4:25}.get(int(oversold), 10)
        if pd.notna(rsi):
            if rsi >= 72: price_pts = max(price_pts - 8, 0)
            elif rsi <= 40: price_pts = min(price_pts + 3, 25)
        trend_pts = 20 if trend_up else 7
        macro_pts = macro_fit_score(asset_name, group, macro_state, macro_regime, macro_bias, m)
        rate_pts = rate_fit_score(asset_name, group, m)
        if pd.isna(r1m): pullback_pts = 7
        elif -10 <= r1m <= -2: pullback_pts = 15
        elif -2 < r1m <= 2: pullback_pts = 11
        elif -18 <= r1m < -10: pullback_pts = 10
        elif 2 < r1m <= 6: pullback_pts = 7
        else: pullback_pts = 3
        score = price_pts + trend_pts + macro_pts + rate_pts + pullback_pts
        if pd.notna(rsi) and rsi >= 75: score = min(score, 59)
        if "경착륙" in macro_regime and macro_state.get("Employment") == "빠른 악화": score = min(score, 59)
        if score >= 70: action, css = "진입 우호", "action-good"
        elif score >= 55: action, css = "분할 진입", "action-mid"
        elif score >= 40: action, css = "정찰 / 대기", "action-watch"
        else: action, css = "대기", "action-wait"
        notes = [f"가격 {price_pts}/25", f"추세 {trend_pts}/20", f"거시 {macro_pts}/25", f"금리 {rate_pts}/15", f"눌림 {pullback_pts}/15"]
        if asset_name == "KOSPI": notes.append("원/달러·외인수급 별도 확인")
        elif asset_name == "Nifty 50": notes.append("인도금리·루피 별도 확인")
        return {"Entry Score":int(score), "Action":action, "CSS":css, "Price Pts":price_pts, "Trend Pts":trend_pts,
                "Macro Pts":macro_pts, "Rate Pts":rate_pts, "Pullback Pts":pullback_pts, "Engine":"Equity", "Reason":" · ".join(notes)}

    if group == "Gold":
        real_pts = rate_fit_score(asset_name, group, m)  # 0~30
        macro_pts = macro_fit_score(asset_name, group, macro_state, macro_regime, macro_bias, m)  # 0~20
        usd_now, usd_prev = m.get("broad_usd"), m.get("broad_usd_20dago")
        if pd.notna(usd_now) and pd.notna(usd_prev):
            du = (usd_now / usd_prev - 1) * 100
            if du <= -1.5: usd_pts = 20
            elif du <= -0.5: usd_pts = 16
            elif du <= 0.5: usd_pts = 11
            elif du <= 1.5: usd_pts = 6
            else: usd_pts = 2
        else: usd_pts = 10
        trend_pts = 15 if trend_up else 6
        if pd.isna(oversold): price_pts = 7
        else: price_pts = {0:6, 1:8, 2:11, 3:13, 4:15}.get(int(oversold), 7)
        if pd.notna(rsi) and rsi >= 75: price_pts = max(price_pts - 7, 0)
        score = real_pts + usd_pts + macro_pts + trend_pts + price_pts
        if pd.notna(rsi) and rsi >= 78: score = min(score, 59)
        if score >= 70: action, css = "진입 우호", "action-good"
        elif score >= 55: action, css = "분할 진입", "action-mid"
        elif score >= 40: action, css = "정찰 / 대기", "action-watch"
        else: action, css = "대기", "action-wait"
        notes = [f"실질금리 {real_pts}/30", f"달러 {usd_pts}/20", f"거시 {macro_pts}/20", f"추세 {trend_pts}/15", f"가격 {price_pts}/15"]
        return {"Entry Score":int(score), "Action":action, "CSS":css, "Price Pts":price_pts, "Trend Pts":trend_pts,
                "Macro Pts":macro_pts, "Rate Pts":real_pts, "Pullback Pts":usd_pts, "Engine":"Gold", "Reason":" · ".join(notes)}

    return {"Entry Score":50, "Action":"정찰 / 대기", "CSS":"action-watch", "Price Pts":0, "Trend Pts":0,
            "Macro Pts":0, "Rate Pts":0, "Pullback Pts":0, "Engine":"Unknown", "Reason":"엔진 확인 필요"}''')

# Make board labels generic enough for asset-specific engines and expose engine.
replace_once(
    '            "자산", "Action", "Entry Score", "Oversold Score", "RSI14", "MA200 Trend", "1M %", "Macro Pts", "Rate Pts"\n        ]].copy()\n        board.columns = ["자산", "판정", "진입점수", "과매도", "RSI", "MA200", "1개월", "거시적합", "금리적합"]\n',
    '            "자산", "Action", "Entry Score", "Engine", "Oversold Score", "RSI14", "MA200 Trend", "1M %", "Macro Pts", "Rate Pts"\n        ]].copy()\n        board.columns = ["자산", "판정", "진입점수", "엔진", "과매도", "RSI", "MA200", "1개월", "거시적합", "금리/듀레이션"]\n',
    'priority board engine',
)
replace_once(
    '                "금리적합": st.column_config.ProgressColumn("금리적합", min_value=0, max_value=15, format="%d"),\n',
    '                "금리/듀레이션": st.column_config.NumberColumn("금리/듀레이션", format="%d"),\n',
    'priority rate column',
)

# Replace score explanation with asset-specific explanation.
old_caption = '''        "진입점수 = 과매도 35 + MA200 추세 20 + 경기·물가·고용 20 + 자산별 금리조건 15 + 최근 1개월 눌림 10. "\n        "RSI≥70 또는 경착륙 국면의 주식은 높은 판정을 제한합니다. KOSPI·Nifty는 미국 거시만으로 완결판정하지 않도록 거시점수 상한을 낮췄습니다."\n'''
new_caption = '''        "자산군별 엔진 적용: 주식=가격25+추세20+거시25+금리15+눌림15, "\n        "채권=듀레이션 촉매40+거시25+시작금리15+ETF확인20, 금=실질금리30+달러20+거시20+추세15+가격15. "\n        "공통 판정은 70점 이상 진입 우호, 55~69 분할 진입, 40~54 정찰/대기입니다."\n'''
replace_once(old_caption, new_caption, 'score caption')

# Asset detail score line should not imply the same weights across assets.
old_detail = '''        st.write(\n            f"**점수 구성:** 가격 {int(r['Price Pts'])}/35 · 추세 {int(r['Trend Pts'])}/20 · "\n            f"거시 {int(r['Macro Pts'])}/20 · 금리 {int(r['Rate Pts'])}/15 · 눌림 {int(r['Pullback Pts'])}/10"\n        )\n'''
new_detail = '''        if r.get("Engine") == "Duration":\n            st.write(f"**채권 듀레이션 엔진:** 듀레이션/금리 {int(r['Rate Pts'])} · 거시 {int(r['Macro Pts'])}/25 · ETF확인 {int(r['Price Pts'])}/20")\n        elif r.get("Engine") == "Gold":\n            st.write(f"**금 엔진:** 실질금리 {int(r['Rate Pts'])}/30 · 거시 {int(r['Macro Pts'])}/20 · 추세 {int(r['Trend Pts'])}/15 · 가격 {int(r['Price Pts'])}/15")\n        else:\n            st.write(f"**주식 엔진:** 가격 {int(r['Price Pts'])}/25 · 추세 {int(r['Trend Pts'])}/20 · 거시 {int(r['Macro Pts'])}/25 · 금리 {int(r['Rate Pts'])}/15 · 눌림 {int(r['Pullback Pts'])}/15")\n'''
replace_once(old_detail, new_detail, 'asset details scoring')

# Show broad USD in macro trend chart alongside HY OAS with a small separate chart later? Add to existing rates chart is not same unit; leave diagnostics only.

p.write_text(text, encoding='utf-8')
print('refined asset-specific entry engines')
