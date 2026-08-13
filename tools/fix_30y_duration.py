from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old = '    "us30y": latest_valid(dgs30),\n    "us30y_20dago": daily_lookback(dgs30, 20),\n    "real10y": latest_valid(real10),\n'
new = '    "us30y": latest_valid(dgs30),\n    "us30y_20dago": daily_lookback(dgs30, 20),\n    "us30y_60dago": daily_lookback(dgs30, 60),\n    "real10y": latest_valid(real10),\n'
if old not in text:
    raise SystemExit('snapshot target not found')
text = text.replace(old, new, 1)

old = '    y_3m = m.get("us10y_60dago") if not is_long else np.nan\n'
new = '    y_3m = m.get("us30y_60dago") if is_long else m.get("us10y_60dago")\n'
if old not in text:
    raise SystemExit('y_3m target not found')
text = text.replace(old, new, 1)

old = '    # For 30Y, use 10Y 3M direction as a macro-duration confirmation when 30Y 60d history is not stored.\n    d3 = (m.get("us10y") - m.get("us10y_60dago")) if is_long and pd.notna(m.get("us10y")) and pd.notna(m.get("us10y_60dago")) else (y_now - y_3m if pd.notna(y_now) and pd.notna(y_3m) else np.nan)\n'
new = '    # 10Y engine uses 10Y 3M; 30Y engine uses 30Y 3M independently.\n    d3 = y_now - y_3m if pd.notna(y_now) and pd.notna(y_3m) else np.nan\n'
if old not in text:
    raise SystemExit('d3 target not found')
text = text.replace(old, new, 1)

old = '    if pd.notna(d1): notes.append(f"대상금리 1M {d1:+.2f}%p")\n    if pd.notna(d2): notes.append(f"2Y 1M {d2:+.2f}%p")\n'
new = '    if pd.notna(d1): notes.append(f"대상금리 1M {d1:+.2f}%p")\n    if pd.notna(d3): notes.append(f"대상금리 3M {d3:+.2f}%p")\n    if pd.notna(d2): notes.append(f"2Y 1M {d2:+.2f}%p")\n    if pd.notna(dr): notes.append(f"실질금리 1M {dr:+.2f}%p")\n'
if old not in text:
    raise SystemExit('notes target not found')
text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
print('30Y duration engine now uses 30Y 1M + 30Y 3M + 2Y + real yield')
