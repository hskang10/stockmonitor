from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')


def rep(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'patch target not found: {label}')
    text = text.replace(old, new, 1)

# 1) Replace/extend CSS with consistent blue/orange/red/gray semantics.
old_css = '''    .asset-card {border:1px solid rgba(128,128,128,.20); border-radius:15px; padding:14px 15px 12px 15px; min-height:190px; background:rgba(128,128,128,.025); margin-bottom:8px;}\n    .asset-title {font-size:1rem; font-weight:780; margin-bottom:1px;}\n    .asset-ticker {font-size:.76rem; color:#888; margin-bottom:8px;}\n    .action {display:inline-block; padding:4px 9px; border-radius:999px; font-size:.84rem; font-weight:780; margin-bottom:7px;}\n    .action-good {background:#dff5e7; color:#126a34;} .action-mid {background:#fff2cc; color:#755300;}\n    .action-watch {background:#fde5d6; color:#873a09;} .action-wait {background:#f2dddd; color:#861e1e;}\n    .score-line {font-size:.82rem; color:#666; margin:3px 0;} .reason {font-size:.79rem; line-height:1.42; color:#707070; margin-top:6px;}\n    .summary-box {border:1px solid rgba(128,128,128,.18); border-radius:13px; padding:12px 14px; background:rgba(128,128,128,.025); min-height:92px;}\n    .summary-big {font-size:1.15rem; font-weight:780; margin-bottom:4px;} .summary-small {font-size:.82rem; color:#777; line-height:1.4;}\n'''
new_css = '''    .status-card {border:1px solid rgba(128,128,128,.20); border-left:5px solid #8a8a8a; border-radius:13px; padding:10px 12px; min-height:86px; background:rgba(128,128,128,.035);}\n    .status-label {font-size:.73rem; font-weight:720; color:#777; margin-bottom:4px;}\n    .status-value {font-size:1.02rem; line-height:1.22; font-weight:800; word-break:keep-all;}\n    .status-sub {font-size:.72rem; color:#777; margin-top:4px;}\n    .status-good {border-left-color:#2474d2; background:rgba(36,116,210,.08);} .status-good .status-value {color:#1f63b7;}\n    .status-warn {border-left-color:#e49318; background:rgba(228,147,24,.09);} .status-warn .status-value {color:#a96600;}\n    .status-bad {border-left-color:#d94b4b; background:rgba(217,75,75,.08);} .status-bad .status-value {color:#b73535;}\n    .status-neutral {border-left-color:#8b8b8b; background:rgba(128,128,128,.04);} .status-neutral .status-value {color:#666;}\n\n    .asset-card {border:1px solid rgba(128,128,128,.20); border-left:5px solid #8a8a8a; border-radius:15px; padding:14px 15px 12px 15px; min-height:190px; background:rgba(128,128,128,.025); margin-bottom:8px;}\n    .asset-card.card-good {border-left-color:#2474d2; background:rgba(36,116,210,.055);}\n    .asset-card.card-mid {border-left-color:#e49318; background:rgba(228,147,24,.055);}\n    .asset-card.card-watch {border-left-color:#d9822b; background:rgba(217,130,43,.045);}\n    .asset-card.card-wait {border-left-color:#d94b4b; background:rgba(217,75,75,.045);}\n    .asset-title {font-size:1rem; font-weight:780; margin-bottom:1px;}\n    .asset-ticker {font-size:.76rem; color:#888; margin-bottom:8px;}\n    .action {display:inline-block; padding:4px 9px; border-radius:999px; font-size:.84rem; font-weight:780; margin-bottom:7px;}\n    .action-good {background:#dbeafe; color:#1f5eaa;} .action-mid {background:#fff0cc; color:#966000;}\n    .action-watch {background:#ffead7; color:#9a4f08;} .action-wait {background:#fde0e0; color:#ad3030;}\n    .score-line {font-size:.82rem; color:#666; margin:3px 0;} .reason {font-size:.79rem; line-height:1.42; color:#707070; margin-top:6px;}\n    .summary-box {border:1px solid rgba(128,128,128,.18); border-radius:13px; padding:12px 14px; background:rgba(128,128,128,.025); min-height:92px;}\n    .summary-big {font-size:1.15rem; font-weight:780; margin-bottom:4px;} .summary-small {font-size:.82rem; color:#777; line-height:1.4;}\n'''
rep(old_css, new_css, 'visual CSS')

# 2) Add status color helper before card_html.
anchor = '\ndef card_html(row):\n'
helper = r'''
def status_tone(value, kind="generic"):
    """첫 화면 상태카드 색상: blue=우호, orange=주의/혼조, red=비우호, gray=미확인."""
    s = str(value)
    if any(k in s for k in ["확인 필요", "N/A", "미확인"]):
        return "status-neutral"

    if kind == "regime":
        if any(k in s for k in ["연착륙", "골디락스"]): return "status-good"
        if any(k in s for k in ["경착륙", "침체", "스태그플레이션", "재인플레이션"]): return "status-bad"
        return "status-warn"
    if kind == "buy":
        if any(k in s for k in ["확대", "정상"]): return "status-good"
        if "축소" in s: return "status-warn"
        if "방어" in s: return "status-bad"
    if kind == "growth":
        if "개선" in s: return "status-good"
        if "둔화" in s: return "status-bad"
        return "status-warn"
    if kind == "inflation":
        if "둔화" in s: return "status-good"
        if "재가속" in s: return "status-bad"
        return "status-warn"
    if kind == "employment":
        if "견조" in s: return "status-good"
        if "빠른 악화" in s: return "status-bad"
        if "완만한 냉각" in s: return "status-warn"
        return "status-neutral"
    if kind == "rates":
        if any(k in s for k in ["↓↓", "↓ 하락", "완화"]): return "status-good"
        if any(k in s for k in ["↑↑", "급등"]): return "status-bad"
        if "↑ 상승" in s: return "status-warn"
        if "안정" in s: return "status-good"
        return "status-neutral"
    return "status-neutral"


def status_card(label, value, kind="generic", sub=""):
    tone = status_tone(value, kind)
    sub_html = f'<div class="status-sub">{sub}</div>' if sub else ''
    return f'''<div class="status-card {tone}"><div class="status-label">{label}</div><div class="status-value">{value}</div>{sub_html}</div>'''

'''
if anchor not in text:
    raise SystemExit('card_html anchor missing')
text = text.replace(anchor, '\n' + helper + anchor.lstrip('\n'), 1)

# 3) Color the entire asset card according to action.
old_card = '''def card_html(row):\n    price, r1m = row.get("Price", np.nan), row.get("1M %", np.nan)\n    ptxt = "N/A" if pd.isna(price) else f"{price:,.2f}"\n    rtxt = "N/A" if pd.isna(r1m) else f"{r1m:+.1f}%"\n    return f"""<div class="asset-card"><div class="asset-title">{row['자산']}</div>\n    <div class="asset-ticker">{row['Ticker']}</div><div class="action {row['CSS']}">{row['Action']}</div>\n'''
new_card = '''def card_html(row):\n    price, r1m = row.get("Price", np.nan), row.get("1M %", np.nan)\n    ptxt = "N/A" if pd.isna(price) else f"{price:,.2f}"\n    rtxt = "N/A" if pd.isna(r1m) else f"{r1m:+.1f}%"\n    card_cls = {"action-good":"card-good", "action-mid":"card-mid", "action-watch":"card-watch", "action-wait":"card-wait"}.get(row['CSS'], "")\n    return f"""<div class="asset-card {card_cls}"><div class="asset-title">{row['자산']}</div>\n    <div class="asset-ticker">{row['Ticker']}</div><div class="action {row['CSS']}">{row['Action']}</div>\n'''
rep(old_card, new_card, 'asset card color class')

# 4) Replace first-screen st.metric tiles with custom visual cards.
old_market = '''    c1, c2, c3, c4, c5, c6 = st.columns(6)\n    c1.metric("거시국면", macro_regime)\n    c2.metric("전체 매수강도", buy_intensity)\n    c3.metric("성장", macro_state.get("Growth", "N/A"))\n    c4.metric("물가", macro_state.get("Inflation", "N/A"))\n    c5.metric("고용", macro_state.get("Employment", "N/A"))\n    c6.metric("금리 추이", rate_trend)\n    st.caption(f"중단기 Bias: {macro_bias} · 10Y 1개월 변화 {rate_1m_delta:+.2f}%p" if pd.notna(rate_1m_delta) else f"중단기 Bias: {macro_bias}")\n'''
new_market = '''    c1, c2, c3, c4, c5, c6 = st.columns(6)\n    with c1:\n        st.markdown(status_card("거시국면", macro_regime, "regime"), unsafe_allow_html=True)\n    with c2:\n        st.markdown(status_card("전체 매수강도", buy_intensity, "buy"), unsafe_allow_html=True)\n    with c3:\n        st.markdown(status_card("성장", macro_state.get("Growth", "N/A"), "growth"), unsafe_allow_html=True)\n    with c4:\n        st.markdown(status_card("물가", macro_state.get("Inflation", "N/A"), "inflation"), unsafe_allow_html=True)\n    with c5:\n        st.markdown(status_card("고용", macro_state.get("Employment", "N/A"), "employment"), unsafe_allow_html=True)\n    with c6:\n        rate_sub = f"10Y 1M {rate_1m_delta:+.2f}%p" if pd.notna(rate_1m_delta) else ""\n        st.markdown(status_card("금리 추이", rate_trend, "rates", rate_sub), unsafe_allow_html=True)\n    st.caption(f"중단기 Bias: {macro_bias}")\n'''
rep(old_market, new_market, 'market regime cards')

# 5) Add a compact legend above asset cards.
old_label = '    st.markdown(\'<div class="section-label">All assets — entry status</div>\', unsafe_allow_html=True)\n'
new_label = '''    st.markdown('<div class="section-label">All assets — entry status</div>', unsafe_allow_html=True)\n    st.markdown('<div style="font-size:.76rem;color:#777;margin:-2px 0 8px 0;">● <span style="color:#2474d2;font-weight:700;">파랑: 우호</span> &nbsp;&nbsp; ● <span style="color:#e49318;font-weight:700;">주황: 주의/분할</span> &nbsp;&nbsp; ● <span style="color:#d94b4b;font-weight:700;">빨강: 비우호/대기</span> &nbsp;&nbsp; ● <span style="color:#888;font-weight:700;">회색: 미확인</span></div>', unsafe_allow_html=True)\n'''
rep(old_label, new_label, 'visual legend')

p.write_text(text, encoding='utf-8')
print('patched app.py visual status')
