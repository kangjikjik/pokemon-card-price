# SRS — 소프트웨어 요구사항 명세서

> **문서 버전**: v1.0  
> **작성일**: 2026-07-08  
> **상태**: 초안

---

## 1. 시스템 개요

### 1.1 목적

포켓몬스터 카드 한/일 시세 비교 플랫폼의 기술적 요구사항을 정의한다.

### 1.2 시스템 구성도

```
[사용자 브라우저]
      │
      ▼
[Next.js 프론트엔드]  ─────────────────────────────┐
      │                                              │
      ▼                                              ▼
[Next.js API Routes / FastAPI 백엔드]        [Vercel Edge / CDN]
      │
      ├── [PostgreSQL DB (Supabase)]
      │       ├── 카드 정보 테이블
      │       ├── 시세 이력 테이블
      │       └── 박스/세트 테이블
      │
      ├── [크롤러 스케줄러] ──12시간 주기──▶ 네이버카페, 당근, 번개장터
      │                                  ▶ 유유테이, カードラッシュ 등
      │
      └── [외부 API]
              ├── pokemontcg.io (카드 이미지·정보)
              └── ExchangeRate-API (JPY→KRW 환율)
```

---

## 2. 기술 스택

| 영역 | 기술 | 선택 이유 |
|------|------|----------|
| **프론트엔드** | Next.js 14 (App Router) + TypeScript | SSR/SSG로 SEO 대응, 풀스택 통합 용이 |
| **스타일링** | Tailwind CSS | 빠른 반응형 UI 구현 |
| **차트** | Recharts 또는 Chart.js | 가격 추이 그래프 |
| **백엔드 API** | Next.js API Routes (초기) / Python FastAPI (크롤러 전용) | 크롤링은 Python 생태계가 풍부 |
| **데이터베이스** | PostgreSQL (Supabase 무료 플랜) | 무료, 관계형 데이터 적합 |
| **크롤링** | Python + Playwright | JS 렌더링 사이트 대응 |
| **스케줄러** | Vercel Cron Jobs 또는 GitHub Actions | 12시간 주기 자동 실행 |
| **환율 API** | ExchangeRate-API (무료 플랜) | JPY→KRW 실시간 환산 |
| **카드 정보 API** | pokemontcg.io | 카드 이미지·기본 정보 |
| **배포** | Vercel (프론트+API) + Supabase (DB) | 무료 플랜으로 시작 가능 |
| **이미지 CDN** | Vercel Image Optimization 또는 Cloudinary | 카드 이미지 최적화 |

---

## 3. 기능 요구사항 (Functional Requirements)

### FR-01. 카드 시세 조회

| ID | 요구사항 |
|----|---------|
| FR-01-1 | 카드명(한글/일본어/영어) 텍스트 검색 제공 |
| FR-01-2 | 검색 결과에서 카드 이미지 + 이름 + 희귀도 + 한국판 시세(KRW) + 일본판 시세(KRW 환산) 표시 |
| FR-01-3 | 카드 클릭 시 상세 페이지로 이동 |
| FR-01-4 | 상세 페이지에서 시세 출처 링크(네이버카페, 번개장터 등) 제공 |
| FR-01-5 | 상세 페이지에서 가격 추이 그래프 표시 (한국판·일본판 선 각각) |

### FR-02. 부스터 박스 시세 조회

| ID | 요구사항 |
|----|---------|
| FR-02-1 | 발매 세트(팩) 목록 페이지 제공 |
| FR-02-2 | 세트별 박스 단위 한국판/일본판 시세 비교 표시 |
| FR-02-3 | 박스 클릭 시 해당 박스 수록 카드 목록 페이지로 이동 |
| FR-02-4 | 수록 카드 목록에서 각 카드의 한국판·일본판 시세 연동 표시 |
| FR-02-5 | 박스 상세 페이지에서 박스 가격 추이 그래프 제공 |

### FR-03. 정렬 및 필터

| ID | 요구사항 |
|----|---------|
| FR-03-1 | 희귀도(등급) 기준 오름차순/내림차순 정렬 |
| FR-03-2 | 가격 기준 오름차순/내림차순 정렬 |
| FR-03-3 | 발매 세트(팩)별 필터 |
| FR-03-4 | 정렬·필터 조합 적용 가능 |

### FR-04. 이미지 기반 탐색

| ID | 요구사항 |
|----|---------|
| FR-04-1 | 메인/목록 페이지에서 카드 이미지 그리드 형태로 탐색 가능 |
| FR-04-2 | 이미지 클릭 시 카드 상세 시세 페이지로 이동 |

### FR-05. 환율 변환

| ID | 요구사항 |
|----|---------|
| FR-05-1 | 일본판 시세(JPY)를 KRW로 자동 환산하여 표시 |
| FR-05-2 | 화면에 환율 기준 시각 표시 (예: "2026-07-08 09:00 기준 ¥1 = ₩9.23") |
| FR-05-3 | 환율 데이터는 하루 1회 갱신 |

### FR-06. 데이터 자동 수집

| ID | 요구사항 |
|----|---------|
| FR-06-1 | 12시간 간격으로 크롤러 자동 실행 |
| FR-06-2 | 수집된 데이터는 DB에 저장 후 캐시로 서빙 |
| FR-06-3 | 마지막 업데이트 시각을 UI에 표시 |
| FR-06-4 | 크롤링 실패 시 이전 데이터 유지 (장애 전파 방지) |

---

## 4. 비기능 요구사항 (Non-Functional Requirements)

| ID | 항목 | 요구사항 |
|----|------|---------|
| NFR-01 | 성능 | 메인 페이지 LCP 2.5초 이하 |
| NFR-02 | 반응형 | 모바일(375px) ~ 데스크탑(1440px) 지원 |
| NFR-03 | 가용성 | Vercel 기본 SLA 준수 (99.9% 목표) |
| NFR-04 | 보안 | 크롤러 User-Agent 설정, robots.txt 준수 |
| NFR-05 | 확장성 | 추후 기능 추가를 고려한 DB 스키마 설계 |
| NFR-06 | 접근성 | 로그인 없이 전체 기능 이용 가능 |

---

## 5. 데이터베이스 스키마 (초안)

### 5.1 테이블 목록

```sql
-- 카드 세트(팩) 정보
CREATE TABLE card_sets (
  id          SERIAL PRIMARY KEY,
  set_code    VARCHAR(20) UNIQUE NOT NULL,  -- 예: 'sv8a'
  name_kr     VARCHAR(100),
  name_jp     VARCHAR(100),
  name_en     VARCHAR(100),
  released_at DATE,
  image_url   TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- 개별 카드 정보
CREATE TABLE cards (
  id          SERIAL PRIMARY KEY,
  set_id      INTEGER REFERENCES card_sets(id),
  card_number VARCHAR(20),               -- 예: '001/064'
  name_kr     VARCHAR(100),
  name_jp     VARCHAR(100),
  name_en     VARCHAR(100),
  rarity      VARCHAR(30),              -- 예: 'SR', 'SAR', 'UR'
  rarity_rank INTEGER,                  -- 정렬용 희귀도 순위
  image_url   TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- 카드 시세 이력 (한국판)
CREATE TABLE prices_kr (
  id          SERIAL PRIMARY KEY,
  card_id     INTEGER REFERENCES cards(id),
  price_krw   INTEGER,                  -- 원화
  source      VARCHAR(50),              -- 'naver_cafe', 'bunjang', 'carrot'
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 카드 시세 이력 (일본판)
CREATE TABLE prices_jp (
  id          SERIAL PRIMARY KEY,
  card_id     INTEGER REFERENCES cards(id),
  price_jpy   INTEGER,                  -- 엔화
  price_krw   INTEGER,                  -- 환산된 원화
  source      VARCHAR(50),              -- 'yuyutei', 'cardrush', 'mercari'
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 박스 시세 이력
CREATE TABLE prices_box (
  id          SERIAL PRIMARY KEY,
  set_id      INTEGER REFERENCES card_sets(id),
  region      VARCHAR(5),               -- 'KR' or 'JP'
  price_krw   INTEGER,
  source      VARCHAR(50),
  fetched_at  TIMESTAMP DEFAULT NOW()
);

-- 환율 정보
CREATE TABLE exchange_rates (
  id          SERIAL PRIMARY KEY,
  jpy_to_krw  DECIMAL(10, 4),
  fetched_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 6. API 엔드포인트 (초안)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/cards` | 카드 목록 (검색·필터·정렬 파라미터) |
| GET | `/api/cards/:id` | 카드 상세 + 현재 시세 |
| GET | `/api/cards/:id/history` | 카드 가격 추이 |
| GET | `/api/sets` | 발매 세트 목록 |
| GET | `/api/sets/:id` | 세트 상세 + 박스 시세 |
| GET | `/api/sets/:id/cards` | 세트 내 카드 목록 + 시세 |
| GET | `/api/sets/:id/box-history` | 박스 가격 추이 |
| GET | `/api/exchange-rate` | 현재 JPY→KRW 환율 |

### 쿼리 파라미터 (카드 목록)

```
GET /api/cards?
  q=피카츄              # 카드명 검색
  set_id=1             # 세트 필터
  sort=rarity_asc      # 정렬: rarity_asc, rarity_desc, price_asc, price_desc
  page=1
  limit=20
```

---

## 7. 크롤링 설계

### 7.1 한국판 크롤링 대상

| 사이트 | 수집 데이터 | 방식 |
|--------|------------|------|
| 네이버 카페 (포켓몬 카드 관련 카페) | 최근 거래 게시글 제목·가격 | Playwright |
| 번개장터 | 카드/박스 판매 목록 | Playwright |
| 당근마켓 | 카드/박스 판매 목록 | Playwright |

### 7.2 일본판 크롤링 대상

| 사이트 | 수집 데이터 | 방식 |
|--------|------------|------|
| 遊遊亭 (yuyutei.jp) | 카드 매입·판매가 | Playwright |
| カードラッシュ | 카드 매입·판매가 | Playwright |
| メルカリ (mercari.com) | C2C 실거래가 | Playwright |

### 7.3 크롤링 원칙

- 요청 간격 최소 2~3초 지연 (서버 부하 방지)
- robots.txt 확인 및 준수
- User-Agent를 일반 브라우저로 설정
- 수집 데이터: 가격 정보만 (개인정보 미수집)
- 실패 시 이전 캐시 데이터 유지

---

## 8. 외부 의존성

| 서비스 | 용도 | 무료 한도 |
|--------|------|----------|
| Supabase | PostgreSQL DB | 500MB, 2개 프로젝트 |
| Vercel | 프론트·API 배포 | 100GB 대역폭/월 |
| pokemontcg.io | 카드 이미지·정보 | 20,000 req/일 |
| ExchangeRate-API | 환율 조회 | 1,500 req/월 |

---

## 9. 화면 목록 (UI 연동 예정)

> 피그마 디자인 완성 후 화면별 캡처 첨부 예정

| 화면 ID | 화면명 | 주요 컴포넌트 |
|---------|--------|--------------|
| S-01 | 메인(홈) | 검색바, 최근 주목 카드, 세트 목록 |
| S-02 | 카드 검색 결과 | 카드 그리드, 정렬·필터 |
| S-03 | 카드 상세 | 이미지, 한/일 시세, 가격 추이 그래프 |
| S-04 | 세트 목록 | 박스 이미지, 박스 시세 비교 |
| S-05 | 세트 상세 (수록 카드) | 카드 목록, 정렬·필터 |
