# Pokémon Card Price (한/일 시세 비교)

포켓몬 카드 한국판·일본판 시세 비교 사이트 + 카탈로그/크롤러.

- **웹**: Next.js → Cloudflare Workers (`web/`)
- **크롤러·시드**: Python (`crawler/`)
- **DB**: Supabase (스키마: `schema.sql`)

라이브: https://pokemon-card-price.stockpick.workers.dev

---

## 다른 PC에서 시작하기

### 1. 저장소 받기

```bash
git clone https://github.com/kangjikjik/pokemon-card-price.git
cd pokemon-card-price
```

### 2. 환경 변수 (비밀키는 Git에 없음)

```bash
# 웹
cp web/.env.example web/.env.local
# crawler
cp crawler/.env.example crawler/.env
```

각 파일에 Supabase URL·키를 입력합니다. (Supabase 대시보드 → Settings → API)

### 3. 웹 로컬 실행

```bash
cd web
npm install
npm run dev
```

### 4. 크롤러

```bash
cd crawler
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt   # 없으면 httpx supabase python-dotenv playwright 등 수동 설치
python main.py
```

### 5. Cloudflare 배포 (선택)

```bash
cd web
npm run deploy
```

Wrangler 로그인·Cloudflare 계정 필요.

---

## Git으로 작업 이어가기

Git은 **자동 동기화가 아닙니다.** 파일을 바꾼 뒤 직접 올리고(pull/push), 다른 PC에서는 받아야(pull) 합니다.

### 최초 1회 — GitHub에 올리기 (이 PC)

로컬 커밋은 이미 되어 있습니다. GitHub 로그인 후 한 번만 실행하세요:

```bash
gh auth login
gh repo create pokemon-card-price --private --source=. --remote=origin --push
```

`gh`가 없으면 [GitHub에서 빈 private 저장소](https://github.com/new)를 `pokemon-card-price` 이름으로 만든 뒤:

```bash
git remote add origin https://github.com/kangjikjik/pokemon-card-price.git   # 이미 있으면 생략
git push -u origin master
```

| 상황 | 할 일 |
|------|--------|
| 이 PC에서 작업 후 GitHub에 반영 | `git add .` → `git commit -m "..."` → `git push` |
| 다른 PC에서 최신 받기 | `git pull` |
| 다른 PC에서 작업 후 이 PC에 반영 | 다른 PC에서 push → 이 PC에서 `git pull` |

**Cursor에서 계속 작업해도** 저장·커밋·push를 하지 않으면 GitHub에는 올라가지 않습니다.  
반대로, GitHub에 push만 하고 이 PC에서 `git pull` 하지 않으면 로컬은 예전 상태입니다.

---

## 주요 스크립트

```bash
cd crawler/seeds
python audit_catalog_quality.py --json   # 카탈로그 품질 감사
python fill_jp_msrp_verified.py --apply  # JP MSRP → set-msrp.ts
```

---

## 커밋하면 안 되는 것

- `crawler/.env`, `web/.env.local` (Supabase 키)
- `node_modules/`, `.open-next/`, `.wrangler/`

`.env.example` 파일만 Git에 포함됩니다.
