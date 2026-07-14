# Cloudflare Workers 배포 가이드

이 프로젝트는 [OpenNext Cloudflare adapter](https://opennext.js.org/cloudflare)로 배포합니다.

## 사전 준비

- Cloudflare 계정
- Node.js 20+
- `web/.env.local` (Supabase 키 등)

## 1. Cloudflare 로그인

```powershell
cd web
npx wrangler login
```

브라우저에서 Cloudflare 계정으로 로그인합니다.

## 2. 환경 변수 (Secrets) 등록

Workers 런타임에서 Supabase 접속에 필요합니다.

```powershell
cd web
npx wrangler secret put NEXT_PUBLIC_SUPABASE_URL
npx wrangler secret put NEXT_PUBLIC_SUPABASE_ANON_KEY
npx wrangler secret put SUPABASE_SERVICE_KEY
```

각 명령 실행 시 `.env.local`의 값을 붙여넣으세요.

> 빌드 시에도 env가 필요하면 `wrangler.jsonc`의 `[vars]` 또는 Cloudflare 대시보드 **Workers > Settings > Variables**에 동일하게 설정하세요.

## 3. 로컬 빌드 확인

```powershell
cd web
npm run build
npx opennextjs-cloudflare build
```

> **Next.js 16 주의**: 기본 빌드가 Turbopack이라 OpenNext Cloudflare에서 `ChunkLoadError`가 납니다.  
> `package.json`의 build 스크립트는 `next build --webpack`을 사용해야 합니다.

## 4. 배포

```powershell
cd web
npm run deploy
```

성공 시 `*.workers.dev` URL이 출력됩니다.

## 5. (선택) GitHub 연동 자동 배포

Cloudflare 대시보드 → **Workers & Pages** → **Create** → **Connect to Git**

| 설정 | 값 |
|------|-----|
| Root directory | `web` |
| Build command | `npm run deploy` |
| Node version | 20 |

**Environment variables** (Build + Runtime 모두):

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`

## 로컬 프리뷰 (Workers 런타임)

```powershell
npm run preview
```

`next dev`와 달리 실제 Cloudflare Workers 환경에서 동작을 확인할 수 있습니다.

## 문제 해결

- **Windows 경고**: OpenNext는 WSL에서 더 안정적입니다. 배포 실패 시 WSL 또는 GitHub Actions 빌드를 권장합니다.
- **사이트 끊김**: 로컬 `next dev`는 PC 종료/슬립 시 중단됩니다. Cloudflare 배포 후에는 24시간 접속 가능합니다.
