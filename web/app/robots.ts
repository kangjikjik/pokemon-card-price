import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'https://pokemon-card-price.stockpick.workers.dev';
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        // API·내부 경로는 인덱싱 차단
        disallow: ['/api/', '/_next/'],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
  };
}
