import type { NextConfig } from "next";

const SECURITY_HEADERS = [
  // 클릭재킹 방지
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  // MIME 스니핑 방지
  { key: "X-Content-Type-Options", value: "nosniff" },
  // Referrer 정보 최소 노출
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // HSTS (HTTPS 강제)
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  // XSS 방지 헤더 (구형 브라우저)
  { key: "X-XSS-Protection", value: "1; mode=block" },
  // 권한 정책 — 불필요 API 차단
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  // CSP — 포켓몬 카드 이미지 허용, 외부 스크립트 차단
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      // 스크립트: self + 인라인(Next.js hydration 필요) + Cloudflare Turnstile(향후)
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://challenges.cloudflare.com",
      // 스타일: self + 인라인(Tailwind)
      "style-src 'self' 'unsafe-inline'",
      // 이미지: 허용 도메인
      [
        "img-src 'self' data: blob:",
        "https://www.pokemon-card.com",
        "https://cdn.collectory.cc",
        "https://images.pokemontcg.io",
        "https://data1.pokemonkorea.co.kr",
        "https://cards.image.pokemonkorea.co.kr",
        "https://card.yuyu-tei.jp",
        "https://cdn.snkrdunk.com",
        "https://s3.ap-northeast-2.amazonaws.com",
      ].join(" "),
      // 폰트
      "font-src 'self'",
      // 연결: Supabase API + Cloudflare
      "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://v6.exchangerate-api.com",
      // 프레임
      "frame-src https://challenges.cloudflare.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: SECURITY_HEADERS,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/products/**",
      },
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/ex/**",
      },
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/assets/images/card_images/**",
      },
      {
        protocol: "https",
        hostname: "cdn.collectory.cc",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "images.pokemontcg.io",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "data1.pokemonkorea.co.kr",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "cards.image.pokemonkorea.co.kr",
        pathname: "/data/wmimages/**",
      },
      {
        protocol: "https",
        hostname: "card.yuyu-tei.jp",
        pathname: "/poc/**",
      },
    ],
  },
};

export default nextConfig;
