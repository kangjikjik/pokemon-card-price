# 시세 수집 정책

1. **한글판 raw 싱글만** — 일본판·PSA·BRG·묶음·박스 제외
2. **체결가** — 카페 마감, Break 등 (중앙값/절사평균)
3. **호가 fallback** — 체결 없을 때
   - **번개장터 우선** (collectory에 번개 없으면 1회 추가 조회)
   - **네이버쇼핑** — 25% 할인 후 비교
   - **일반 등급** — 우선순위 구간 내 최저가
   - **SAR/MUR 등** — 호가 2건 이상이면 할인 후 중앙값
4. **미등록** — 체결·호가 모두 없음

## 속도 (빠른 모드 기본)

- 세트 시작 시 collectory **20병렬 프리로드**
- **인증 API 생략** (공개 거래내역만; `--thorough` 시 쿠키 API 사용)
- **번개 보강 8병렬** (collectory에 번개 없는 카드만)
- **DB 일괄 저장** — 일별 스냅샷 (오늘 KST분만 교체, 과거 이력 유지)
- 배치 기본 `--quiet` (요약만; `--verbose`로 카드별 로그)

Collectory set API `price_krw`는 사용하지 않음.

## 이력·자동화

- `prices_kr` / `prices_jp`에 **날짜별 스냅샷**을 쌓음 (그래프·어제 대비 추이)
- 같은 날 재실행 시 오늘 행만 교체
- 일일 배치: KR 3팩(`--daily`) + JP 5팩 순환
  - Windows: `crawler/scripts/register_price_schedule.ps1` (기본 00:00)
  - GitHub Actions: `.github/workflows/daily-prices.yml` (KST 자정)
