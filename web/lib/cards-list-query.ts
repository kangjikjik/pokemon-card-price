import type { SupabaseClient } from '@supabase/supabase-js';
import { buildLatestKrPriceMap } from '@/lib/card-sort-helpers';
import { isDisplayableRarity, normalizeRarity } from '@/lib/rarity';
import { cardNameSearchOr } from '@/lib/search';

const ID_BATCH = 1000;

type CardsFilter = {
  featuredSetIds: number[];
  rawRarities: string[];
  searchQuery: string;
  matchingSetIds: number[];
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type CardsQuery = any;

function applySearchFilter(query: CardsQuery, filter: CardsFilter): CardsQuery {
  const { searchQuery, matchingSetIds } = filter;
  if (!searchQuery.trim()) return query;
  return query.or(cardNameSearchOr(searchQuery, matchingSetIds));
}

function baseCardsQuery(supabase: SupabaseClient, filter: CardsFilter): CardsQuery {
  let query = supabase
    .from('cards')
    .select('id', { count: 'exact', head: true })
    .in('set_id', filter.featuredSetIds)
    .in('rarity', filter.rawRarities);
  return applySearchFilter(query, filter);
}

export async function countFilteredCards(
  supabase: SupabaseClient,
  filter: CardsFilter,
): Promise<number> {
  const { count, error } = await baseCardsQuery(supabase, filter);
  if (error) throw error;
  return count ?? 0;
}

/** 전역 정렬용 — id만 배치 조회 (Worker 메모리·CPU 절약) */
export async function fetchFilteredCardIds(
  supabase: SupabaseClient,
  filter: CardsFilter,
): Promise<number[]> {
  const ids: number[] = [];
  let offset = 0;

  while (true) {
    let query = supabase
      .from('cards')
      .select('id, rarity')
      .in('set_id', filter.featuredSetIds)
      .in('rarity', filter.rawRarities);
    query = applySearchFilter(query, filter);
    query = query.order('id', { ascending: true });

    const { data, error } = await query.range(offset, offset + ID_BATCH - 1);
    if (error) throw error;
    if (!data?.length) break;

    for (const row of data) {
      if (isDisplayableRarity((row.rarity as string) || '')) {
        ids.push(row.id as number);
      }
    }
    if (data.length < ID_BATCH) break;
    offset += ID_BATCH;
  }

  return ids;
}

const PAGE_SELECT =
  'id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number, card_sets ( id, set_code, name_kr, name_en, name_jp )';

const PAGE_SELECT_POPULAR =
  'id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number, view_count, card_sets ( id, set_code, name_kr, name_en, name_jp )';

export async function fetchCardsPageByRarity(
  supabase: SupabaseClient,
  filter: CardsFilter,
  page: number,
  limit: number,
): Promise<{ rows: Record<string, unknown>[]; total: number }> {
  const total = await countFilteredCards(supabase, filter);
  const start = (page - 1) * limit;

  let query = supabase
    .from('cards')
    .select(PAGE_SELECT)
    .in('set_id', filter.featuredSetIds)
    .in('rarity', filter.rawRarities);
  query = applySearchFilter(query, filter);
  query = query
    .order('rarity_rank', { ascending: false })
    .order('card_number', { ascending: true });

  const { data, error } = await query.range(start, start + limit - 1);
  if (error) throw error;

  const rows = ((data || []) as Record<string, unknown>[]).filter(r =>
    isDisplayableRarity(normalizeRarity((r.rarity as string) || '')),
  );

  return { rows, total };
}

export async function fetchCardsPageByPopular(
  supabase: SupabaseClient,
  filter: CardsFilter,
  page: number,
  limit: number,
): Promise<{ rows: Record<string, unknown>[]; total: number; usedViewCount: boolean }> {
  const total = await countFilteredCards(supabase, filter);
  const start = (page - 1) * limit;

  let query = supabase
    .from('cards')
    .select(PAGE_SELECT_POPULAR)
    .in('set_id', filter.featuredSetIds)
    .in('rarity', filter.rawRarities);
  query = applySearchFilter(query, filter);
  query = query
    .order('view_count', { ascending: false, nullsFirst: false })
    .order('rarity_rank', { ascending: false })
    .order('card_number', { ascending: true });

  const { data, error } = await query.range(start, start + limit - 1);
  if (error) {
    const msg = String(error);
    if (msg.includes('view_count') || (error as { code?: string }).code === '42703') {
      const fallback = await fetchCardsPageByRarity(supabase, filter, page, limit);
      return { ...fallback, usedViewCount: false };
    }
    throw error;
  }

  const rows = ((data || []) as Record<string, unknown>[]).filter(r =>
    isDisplayableRarity(normalizeRarity((r.rarity as string) || '')),
  );

  return { rows, total, usedViewCount: true };
}

const PRICE_SORT_TTL_MS = 10 * 60 * 1000;
const priceSortCache = new Map<string, { at: number; ids: number[] }>();

function priceSortCacheKey(filter: CardsFilter, sort: 'price_asc' | 'price_desc'): string {
  return [
    sort,
    filter.featuredSetIds.join(','),
    filter.rawRarities.join(','),
    filter.searchQuery,
    filter.matchingSetIds.join(','),
  ].join('|');
}

/** 가격순 — 전체 재정렬은 10분에 한 번. 페이지 이동마다 반복하면 Worker 1102. */
export async function fetchCardIdsPageByPrice(
  supabase: SupabaseClient,
  filter: CardsFilter,
  sort: 'price_asc' | 'price_desc',
  page: number,
  limit: number,
): Promise<{ pageIds: number[]; total: number }> {
  const key = priceSortCacheKey(filter, sort);
  const cached = priceSortCache.get(key);
  const fresh = cached && Date.now() - cached.at < PRICE_SORT_TTL_MS ? cached.ids : null;

  let sorted = fresh;
  if (!sorted) {
    const ids = await fetchFilteredCardIds(supabase, filter);
    if (ids.length === 0) return { pageIds: [], total: 0 };
    const priceMap = await buildLatestKrPriceMap(supabase, ids);
    sorted = [...ids].sort((a, b) => {
      const pa = priceMap.get(a) ?? 0;
      const pb = priceMap.get(b) ?? 0;
      return sort === 'price_asc' ? pa - pb : pb - pa;
    });
    priceSortCache.set(key, { at: Date.now(), ids: sorted });
  }

  const start = (page - 1) * limit;
  return { pageIds: sorted.slice(start, start + limit), total: sorted.length };
}

export async function fetchCardsByIds(
  supabase: SupabaseClient,
  pageIds: number[],
): Promise<Record<string, unknown>[]> {
  if (!pageIds.length) return [];
  const { data, error } = await supabase.from('cards').select(PAGE_SELECT).in('id', pageIds);
  if (error) throw error;

  const byId = new Map((data || []).map(r => [r.id as number, r as Record<string, unknown>]));
  return pageIds.map(id => byId.get(id)).filter((r): r is Record<string, unknown> => r != null);
}
