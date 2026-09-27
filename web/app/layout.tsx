import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { GoogleAnalytics } from '@/components/google-analytics';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc';
const SITE_NAME = '카도리';
const SITE_TITLE = `${SITE_NAME} · 포켓몬 카드 시세 — 한국/일본 카드·박스 실거래`;
const SITE_DESCRIPTION =
  '카도리는 한국·일본 포켓몬 카드와 박스 시세를 비교하는 사이트입니다. 등급별 카드 시세, 거래 내역, 세트별 박스 가격을 한곳에서 확인하세요.';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: SITE_NAME,
  title: {
    default: SITE_TITLE,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    siteName: SITE_NAME,
    locale: 'ko_KR',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml', sizes: 'any' },
      { url: '/icon-32.png', type: 'image/png', sizes: '32x32' },
      { url: '/icon-16.png', type: 'image/png', sizes: '16x16' },
    ],
    shortcut: '/icon-32.png',
    apple: '/apple-icon.png',
  },
};

const websiteJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: SITE_NAME,
  alternateName: 'Cardory',
  url: SITE_URL,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <meta
          name="naver-site-verification"
          content="8fdeb835c2b38d21de8626fc9e92cf07bf0adb4d"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
        />
      </head>
      <body>
        <GoogleAnalytics />
        <ThemeProvider>
          <div className="min-h-screen bg-slate-50 dark:bg-[#0B132B] text-slate-900 dark:text-slate-200 flex flex-col transition-colors duration-300">
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
