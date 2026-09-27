import type { MetadataRoute } from 'next';
import type { SupabaseClient } from '@supabase/supabase-js';
import { CARDS_LIST_SET_CODES } from '@/lib/constants';
import { DISPLAY_RARITIES, RARITY_ALIASES } from '@/lib/rarity';

export const SITEMAP_BASE = (process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc').replace(
  /\/$/,
  '',
);

const RAW_DISPLAY_RARITIES = [...DISPLAY_RARITIES, ...Object.keys(RARITY_ALIASES)];

/** 카드 URL — sitemap 1개당 (Google·Worker 타임아웃 방지) */
export const CARD_BATCH = 800;

async function getSupabase() {
  const { getSupabaseServer } = await import('@/lib/supabase');
  return getSupabaseServer();
}

async function loadSetIds(supabase: SupabaseClient): Promise<number[]> {
  const { data, error } = await supabase
    .from('card_sets')
    .select('id')
    .in('set_code', [...CARDS_LIST_SET_CODES]);
  if (error || !data?.length) return [];
  return data.map(row => row.id as number);
}

async function countCardUrls(supabase: SupabaseClient, setIds: number[]): Promise<number> {
  if (!setIds.length) return 0;
  const { count, error } = await supabase
    .from('cards')
    .select('id', { count: 'exact', head: true })
    .in('set_id', setIds)
    .in('rarity', RAW_DISPLAY_RARITIES);
  if (error) throw error;
  return count ?? 0;
}

export function staticSitemapPages(now: string): MetadataRoute.Sitemap {
  return [
    { url: `${SITEMAP_BASE}/`, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${SITEMAP_BASE}/cards`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${SITEMAP_BASE}/sets`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    {
      url: `${SITEMAP_BASE}/community`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.6,
    },
  ];
}

export async function listSitemapIds(): Promise<number[]> {
  try {
    const supabase = await getSupabase();
    const setIds = await loadSetIds(supabase);
    const totalCards = await countCardUrls(supabase, setIds);
    const cardBatches = Math.ceil(totalCards / CARD_BATCH);
    const ids = [0, 1];
    for (let i = 0; i < cardBatches; i += 1) {
      ids.push(i + 2);
    }
    return ids;
  } catch {
    return [0];
  }
}

export async function loadSitemapPart(id: number, now: string): Promise<MetadataRoute.Sitemap> {
  if (id === 0) {
    return staticSitemapPages(now);
  }

  const supabase = await getSupabase();

  if (id === 1) {
    const { data, error } = await supabase
      .from('card_sets')
      .select('id')
      .in('set_code', [...CARDS_LIST_SET_CODES]);
    if (error || !data?.length) return [];

    return data.map(row => ({
      url: `${SITEMAP_BASE}/sets/${row.id}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    }));
  }

  const setIds = await loadSetIds(supabase);
  if (!setIds.length) return [];

  const batchIndex = id - 2;
  const start = batchIndex * CARD_BATCH;
  const { data, error } = await supabase
    .from('cards')
    .select('id')
    .in('set_id', setIds)
    .in('rarity', RAW_DISPLAY_RARITIES)
    .order('id', { ascending: true })
    .range(start, start + CARD_BATCH - 1);

  if (error) throw error;
  if (!data?.length) return [];

  return data.map(row => ({
    url: `${SITEMAP_BASE}/cards/${row.id}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.65,
  }));
}
