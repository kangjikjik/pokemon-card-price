import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { GoogleAnalytics } from '@/components/google-analytics';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: 'Cardory',
  title: 'Cardory · 포켓몬 카드 시세 — 한국/일본 카드·박스 실거래',
  description:
    'Cardory(카드오리)는 한국·일본 포켓몬 카드와 박스 시세를 비교하는 사이트입니다. 등급별 카드 시세, 거래 내역, 세트별 박스 가격을 한곳에서 확인하세요.',
  openGraph: {
    title: 'Cardory · 포켓몬 카드 시세 — 한국/일본 카드·박스 실거래',
    description:
      'Cardory(카드오리)는 한국·일본 포켓몬 카드와 박스 시세를 비교하는 사이트입니다. 등급별 카드 시세, 거래 내역, 세트별 박스 가격을 한곳에서 확인하세요.',
    url: SITE_URL,
    siteName: 'Cardory',
    locale: 'ko_KR',
    type: 'website',
  },
  twitter: {
    card: 'summary',
    title: 'Cardory · 포켓몬 카드 시세 — 한국/일본 카드·박스 실거래',
    description:
      'Cardory(카드오리)는 한국·일본 포켓몬 카드와 박스 시세를 비교하는 사이트입니다. 등급별 카드 시세, 거래 내역, 세트별 박스 가격을 한곳에서 확인하세요.',
  },
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
};

const websiteJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'Cardory',
  alternateName: '카드오리',
  url: SITE_URL,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
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
