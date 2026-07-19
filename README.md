# Gems 3.0 글로벌 지수 과매도 진입 대시보드

## 주요 기능

- S&P 500, Nasdaq-100, Nifty 50, KOSPI 공통 지표 계산
- 20·60·200일 이격도
- Wilder 방식 RSI14
- 당일 제외 이전 252거래일 백분위 임계값
- 0~4점 과매도 점수
- MA200 20거래일 기울기 기반 장기 추세 필터
- 사이클 상태 저장
- 동일 점수 재진입 차단
- 10거래일 쿨다운
- 현금 상태별 주문 차단
- KOSPI 자동매수 기본 비활성화
- 우선순위 랭킹, 히트맵, 스파크라인, 현금 시뮬레이션
- 매수 실행 로그 CSV 저장

## 설치

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

패키지 설치:

```bash
pip install -r requirements.txt
```

실행:

```bash
streamlit run app.py
```

## 저장 파일

- `storage/cycle_state.json`: 지수별 현재 사이클 상태
- `storage/signal_log.csv`: 사용자가 기록한 매수 실행 로그

## 중요한 구현 교정 사항

1. RSI는 단순 14일 이동평균 방식이 아니라 Wilder 지수평활 방식입니다.
2. 하락 추세 반등 확인은 사양서대로 **5일 이동평균 상향 돌파**를 사용합니다.
3. 최초 진입은 쿨다운을 적용하지 않고, 기존 매수 이력이 있을 때만 10거래일 쿨다운을 적용합니다.
4. `DATA_WARNING`에서도 자동주문을 보류합니다.
5. LOW_CASH 상태에서는 2점 정찰매수를 금지합니다.
6. KOSPI 자동매수는 기본값이 꺼져 있습니다.
7. 백분위 임계값은 `shift(1)`로 당일 값을 제외합니다.

## 한계

Yahoo Finance 단독 데이터는 공인 데이터 교차검증을 완전히 충족하지 못합니다.
실전 자동주문에 사용하려면 거래소·브로커·공인 시세 API와 최소 2개 데이터 제공처의
최근 종가 교차검증 모듈을 추가해야 합니다.
