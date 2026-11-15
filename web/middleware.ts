// Edge 미들웨어 — IP 기반 레이트 리밋
// 보호 대상:
//   POST /api/community/**          (글쓰기·수정·삭제·따봉) — 분당 20회
//   POST /api/cards/:id/view        (카드 조회수)            — 분당 60회
//   POST /api/sets/:id/view         (세트·박스 조회수)       — 분당 60회
// 인메모리 Map, Cloudflare Workers 기준으로 충분한 수준
// 더 강한 제한: Cloudflare Dashboard > Rate Limiting 규칙 추가

import { NextRequest, NextResponse } from 'next/server';

// ── 설정 ────────────────────────────────────────────────
const WINDOW = 60000; // 1분(ms)

const RULES: { pattern: RegExp; method: string; max: number; windowMs: number }[] = [
  {
    pattern: /^\/api\/community\//,
    method: 'POST',
    max: 20,
    windowMs: WINDOW,
  },
  {
    pattern: /^\/api\/community\//,
    method: 'DELETE',
    max: 20,
    windowMs: WINDOW,
  },
  {
    pattern: /^\/api\/community\//,
    method: 'PATCH',
    max: 20,
    windowMs: WINDOW,
  },
  {
    pattern: /^\/api\/cards\/\d+\/view$/,
    method: 'POST',
    max: 60,
    windowMs: WINDOW,
  },
  {
    pattern: /^\/api\/sets\/\d+\/view$/,
    method: 'POST',
    max: 60,
    windowMs: WINDOW,
  },
];

// ── 인메모리 버킷 ────────────────────────────────────────
type Bucket = { count: number; resetAt: number };
const store = new Map<string, Bucket>();

// 오래된 버킷 정리 (메모리 누수 방지 — 1만 개 초과 시)
function cleanup() {
  if (store.size < 10000) return;
  const now = Date.now();
  for (const [key, bucket] of store) {
    if (bucket.resetAt < now) store.delete(key);
  }
}

function isRateLimited(ip: string, ruleKey: string, max: number, windowMs: number): boolean {
  cleanup();
  const key = `${ip}:${ruleKey}`;
  const now = Date.now();
  let bucket = store.get(key);

  if (!bucket || bucket.resetAt <= now) {
    bucket = { count: 1, resetAt: now + windowMs };
    store.set(key, bucket);
    return false;
  }

  bucket.count += 1;
  return bucket.count > max;
}

const CANONICAL_HOST = 'cardory.cc';

function canonicalHostRedirect(req: NextRequest): NextResponse | null {
  const host = req.headers.get('host') ?? '';
  if (host.endsWith('.workers.dev') || host === `www.${CANONICAL_HOST}`) {
    const url = req.nextUrl.clone();
    url.protocol = 'https';
    url.hostname = CANONICAL_HOST;
    return NextResponse.redirect(url, 301);
  }
  return null;
}

// ── 미들웨어 ─────────────────────────────────────────────
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  // sitemap·robots는 미들웨어를 타면 구글 서치 콘솔이 가져오기에 실패한다.
  if (
    pathname === '/robots.txt' ||
    pathname === '/sitemap.xml' ||
    pathname === '/sitemap-index.xml' ||
    pathname.startsWith('/sitemap-part-') ||
    pathname.startsWith('/sitemap/')
  ) {
    return NextResponse.next();
  }

  if (pathname === '/google3ca8d6b5eecf781e.html') {
    return new NextResponse('google-site-verification: google3ca8d6b5eecf781e.html\n', {
      status: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
  }

  const hostRedirect = canonicalHostRedirect(req);
  if (hostRedirect) return hostRedirect;
  const method = req.method.toUpperCase();

  // IP: Cloudflare → CF-Connecting-IP, 그 외 X-Forwarded-For
  const ip =
    req.headers.get('cf-connecting-ip') ||
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown';

  for (const rule of RULES) {
    if (rule.method !== method) continue;
    if (!rule.pattern.test(pathname)) continue;

    const ruleKey = `${rule.method}:${rule.pattern.source}`;
    if (isRateLimited(ip, ruleKey, rule.max, rule.windowMs)) {
      return new NextResponse(
        JSON.stringify({ error: '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.' }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': String(Math.ceil(rule.windowMs / 1000)),
          },
        },
      );
    }
    break; // 첫 번째 매칭 규칙만 적용
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|sitemap-index\\.xml|sitemap-part-|sitemap\\.xml|robots\\.txt|sitemap/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
};
