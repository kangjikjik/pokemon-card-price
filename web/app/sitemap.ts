import { MetadataRoute } from 'next';
import { FEATURED_SET_CODES, SPECIAL_SET_CODES } from '@/lib/constants';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://pokemon-card-price.stockpick.workers.dev';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();

  // 정적 페이지
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${BASE}/cards`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/sets`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${BASE}/community`, lastModified: now, changeFrequency: 'daily', priority: 0.6 },
  ];

  // 세트 페이지 — DB 없이 constants 기반 (빌드 시 안정적)
  const allSetCodes = [
    ...FEATURED_SET_CODES,
    ...SPECIAL_SET_CODES,
  ];

  // set_code → DB id 매핑을 시도, 실패하면 세트 URL 생략
  let setPages: MetadataRoute.Sitemap = [];
  try {
    const { getSupabaseServer } = await import('@/lib/supabase');
    const supabase = getSupabaseServer();
    const { data } = await supabase
      .from('card_sets')
      .select('id, set_code')
      .in('set_code', allSetCodes as unknown as string[]);

    if (data) {
      setPages = data.map((row) => ({
        url: `${BASE}/sets/${row.id}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.7,
      }));
    }
  } catch {
    // DB 접근 실패 시 세트 페이지 없이 빌드 진행
  }

  return [...staticPages, ...setPages];
}
