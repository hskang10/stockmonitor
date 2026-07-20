# Global Oversold Dashboard + CPI Engine

이 프로젝트는 다음을 하나의 Streamlit 앱으로 통합합니다.

- S&P 500, Nasdaq-100, Nifty 50, KOSPI
- MA20/60/200
- 이격도 20/60/200
- Wilder RSI(14)
- 장기 추세 필터와 과매도 점수
- BLS Headline/Core CPI 조회
- CPI MoM/YoY 계산
- 시장 예상치 대비 Surprise
- Shock / Neutral / Goldilocks
- 기술 투입률 × CPI 배수 = 최종 현금 투입률
- SQLite CPI 캐시 및 저장
- BLS timeout/retry 및 `-` 값 예외 처리

## 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

BLS API 키는 선택입니다. 환경변수 `BLS_API_KEY`에 설정할 수 있습니다.

## 주의

- 기본 CPI 기준월은 직전 달입니다.
- BLS에 아직 발표되지 않은 월을 입력하면 필요한 기준값 누락 메시지를 표시합니다.
- 2025년 10월처럼 BLS가 `-`를 반환한 월은 자동으로 건너뜁니다.
- CPI 예상치를 사용하지 않으면 Macro 판정은 Neutral(1.0x)입니다.
- 투자 판단을 자동 실행하지 않으며, 단계 진입 검토값을 제공합니다.
