import { MetadataRoute } from 'next';
import { FEATURED_SET_CODES, SPECIAL_SET_CODES } from '@/lib/constants';

const BASE = (process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc').replace(/\/$/, '');

// GSC·봇이 반복 조회해도 Workers cold start + DB 지연으로 500 나지 않게 캐시
export const revalidate = 3600;

function staticPages(now: string): MetadataRoute.Sitemap {
  return [
    { url: `${BASE}/`, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${BASE}/cards`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/sets`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${BASE}/community`, lastModified: now, changeFrequency: 'daily', priority: 0.6 },
  ];
}

async function loadSetPages(now: string): Promise<MetadataRoute.Sitemap> {
  const allSetCodes = [...FEATURED_SET_CODES, ...SPECIAL_SET_CODES];
  const { getSupabaseServer } = await import('@/lib/supabase');
  const supabase = getSupabaseServer();
  const { data, error } = await supabase
    .from('card_sets')
    .select('id, set_code')
    .in('set_code', allSetCodes as unknown as string[]);

  if (error || !data) return [];

  return data.map((row) => ({
    url: `${BASE}/sets/${row.id}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();
  const core = staticPages(now);

  try {
    const setPages = await loadSetPages(now);
    return [...core, ...setPages];
  } catch {
    // DB/런타임 실패 시에도 최소 4페이지 sitemap은 항상 200
    return core;
  }
}
