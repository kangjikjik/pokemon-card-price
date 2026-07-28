import { NextRequest, NextResponse } from 'next/server';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, type Card } from '@/lib/data';
import { calcRepresentativePrice, latestPriceKrw } from '@/lib/price-calc';
import { CARDS_LIST_SET_CODES } from '@/lib/constants';
import { getSetShortName } from '@/lib/set-names';
import {
  compareCardsByRarity,
  DISPLAY_RARITIES,
  isDisplayableRarity,
  normalizeRarity,
  RARITY_ALIASES,
} from '@/lib/rarity';
import { matchesSearchQuery, searchIlikePattern, setMatchesSearchQuery } from '@/lib/search';
import { buildLatestKrPriceMap, viewCountFromRow } from '@/lib/card-sort-helpers';

const SET_COLORS: Record<string, string> = {
  SV2a: 'from-green-500 to-emerald-700',
  SV2D: 'from-purple-500 to-fuchsia-700',
  S12a: 'from-slate-800 to-slate-950',
  SV4a: 'from-cyan-400 to-blue-600',
  S11:  'from-indigo-700 to-purple-900',
  S12:  'from-blue-500 to-indigo-700',
};

/** DB에 저장된 raw rarity + alias 키 */
const RAW_DISPLAY_RARITIES = [
  ...DISPLAY_RARITIES,
  ...Object.keys(RARITY_ALIASES),
];

function rawRaritiesForFilter(rarity: string): string[] {
  const norm = normalizeRarity(rarity);
  const aliasKeys = Object.entries(RARITY_ALIASES)
    .filter(([, v]) => v === norm)
    .map(([k]) => k);
  return [...new Set([rarity, norm, ...aliasKeys])];
}

function transformCard(raw: Record<string, unknown>, compact: boolean): Card {
  const pricesKR = Array.isArray(raw.prices_kr)
    ? (raw.prices_kr as { price_krw: number; fetched_at: string }[])
    : [];
  const pricesJP = Array.isArray(raw.prices_jp)
    ? (raw.prices_jp as { price_krw: number; price_jpy: number; fetched_at: string }[])
    : [];

  const setRaw = raw.card_sets;
  const set = (Array.isArray(setRaw) ? setRaw[0] : setRaw) as {
    id: number;
    set_code: string;
    name_kr: string;
    name_en?: string;
  } | null;

  const kr = calcRepresentativePrice(pricesKR);
  const jp = calcRepresentativePrice(pricesJP);
  const priceKR = compact ? latestPriceKrw(pricesKR) : kr.price;
  const priceJP = compact ? latestPriceKrw(pricesJP) : jp.price;

  return {
    id: String(raw.id),
    name: (raw.name_kr as string) || (raw.name_jp as string) || (raw.name_en as string) || '알 수 없음',
    enName: (raw.name_en as string) || '',
    set: getSetShortName(set?.set_code || '', set?.name_kr || ''),
    setCode: set?.set_code || '',
    setId: set?.id != null ? String(set.id) : '',
    number: (raw.card_number as string) || '',
    rarity: normalizeRarity((raw.rarity as string) || ''),
    rarityRank: (raw.rarity_rank as number) || 0,
    imageUrl: (raw.image_url as string) || '',
    imageColor: (raw.image_color as string) || SET_COLORS[set?.set_code || ''] || 'from-slate-400 to-slate-600',
    priceKR,
    priceJP,
    trendKR: kr.trend,
    trendJP: jp.trend,
    historyKR: compact ? [] : kr.history,
    historyJP: compact ? [] : jp.history,
  };
}

type LiteRow = {
  id: number;
  rarity: string;
  card_number: string;
  name_kr: string;
  image_url?: string;
  card_sets?: { id: number; set_code: string; name_kr: string } | { id: number; set_code: string; name_kr: string }[];
};

function liteToSortable(row: LiteRow) {
  const setRaw = row.card_sets;
  const set = Array.isArray(setRaw) ? setRaw[0] : setRaw;
  return {
    id: row.id,
    rarity: normalizeRarity(row.rarity || ''),
    number: row.card_number || '',
    name: row.name_kr || '',
    imageUrl: row.image_url || '',
    setCode: set?.set_code || '',
  };
}

const SORT_LITE_RARITY =
  'id, rarity, card_number, name_kr, image_url, card_sets ( id, set_code, name_kr )';

const SORT_LITE_POPULAR =
  'id, rarity, card_number, name_kr, image_url, view_count, card_sets ( id, set_code, name_kr )';

function isMissingViewCountError(err: unknown): boolean {
  if (err && typeof err === 'object') {
    const e = err as { code?: string; message?: string };
    if (e.code === '42703') return true;
    if (e.message?.includes('view_count')) return true;
  }
  const msg = String(err);
  return msg.includes('view_count') && (msg.includes('42703') || msg.includes('does not exist'));
}

const FULL_SELECT_COMPACT = `
  id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number,
  card_sets ( id, set_code, name_kr, name_en, name_jp ),
  prices_kr ( price_krw, fetched_at ),
  prices_jp ( price_krw, fetched_at )
`;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q') || '';
  const rarity = searchParams.get('rarity') || '';
  const sort = searchParams.get('sort') || 'rarity_desc';
  const compact = searchParams.get('compact') !== '0';
  const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10));
  const limit = Math.min(Math.max(1, parseInt(searchParams.get('limit') || '40', 10)), 200);

  try {
    const supabase = getSupabaseServer();

    const { data: featuredSets } = await supabase
      .from('card_sets')
      .select('id, set_code, name_kr')
      .in('set_code', [...CARDS_LIST_SET_CODES]);

    const featuredSetIds = (featuredSets || []).map(s => s.id);
    if (featuredSetIds.length === 0) throw new Error('No featured sets');

    const matchingSetIds = q
      ? (featuredSets || [])
          .filter(s => setMatchesSearchQuery(s.set_code || '', q, s.name_kr))
          .map(s => s.id)
      : [];

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const applySearchFilter = <T extends { or: (filters: string) => T; in: (col: string, vals: number[]) => T }>(query: T): T => {
      if (!q) return query;
      const pattern = searchIlikePattern(q);
      if (matchingSetIds.length > 0) {
        return query.or(
          `name_kr.ilike.${pattern},name_jp.ilike.${pattern},name_en.ilike.${pattern},set_id.in.(${matchingSetIds.join(',')})`,
        );
      }
      return query.or(`name_kr.ilike.${pattern},name_jp.ilike.${pattern},name_en.ilike.${pattern}`);
    };

    // ── 2단계 조회: 등급순·가격순·인기순 (전역 정렬) ──
    if (sort === 'rarity_desc' || sort === 'price_asc' || sort === 'price_desc' || sort === 'popular') {
      const BATCH = 1000;
      const liteRows: Record<string, unknown>[] = [];
      let offset = 0;
      let liteSelect = sort === 'popular' ? SORT_LITE_POPULAR : SORT_LITE_RARITY;
      let popularUsesViewCount = sort === 'popular';

      fetchLoop: while (true) {
        while (true) {
          let query = supabase
            .from('cards')
            .select(liteSelect)
            .in('set_id', featuredSetIds)
            .in('rarity', rarity ? rawRaritiesForFilter(rarity) : RAW_DISPLAY_RARITIES);

          query = applySearchFilter(query);
          query = query.order('id', { ascending: true });

          const { data, error } = await query.range(offset, offset + BATCH - 1);
          if (error) {
            if (popularUsesViewCount && isMissingViewCountError(error)) {
              liteSelect = SORT_LITE_RARITY;
              popularUsesViewCount = false;
              liteRows.length = 0;
              offset = 0;
              continue fetchLoop;
            }
            throw error;
          }
          if (!data || data.length === 0) break;

          liteRows.push(...(data as unknown as Record<string, unknown>[]));
          if (data.length < BATCH) break;
          offset += BATCH;
        }
        break fetchLoop;
      }

      let sortedLite = liteRows
        .map(r => liteToSortable(r as LiteRow))
        .filter(c => isDisplayableRarity(c.rarity));

      if (sort === 'price_asc' || sort === 'price_desc') {
        const priceMap = await buildLatestKrPriceMap(
          supabase,
          sortedLite.map(c => c.id),
        );
        sortedLite = [...sortedLite].sort((a, b) => {
          const pa = priceMap.get(a.id) ?? 0;
          const pb = priceMap.get(b.id) ?? 0;
          return sort === 'price_asc' ? pa - pb : pb - pa;
        });
      } else if (sort === 'popular') {
        const viewById = new Map<number, number>();
        for (const row of liteRows) {
          viewById.set(row.id as number, viewCountFromRow(row));
        }
        sortedLite = [...sortedLite].sort((a, b) => {
          const va = viewById.get(a.id) ?? 0;
          const vb = viewById.get(b.id) ?? 0;
          if (vb !== va) return vb - va;
          return compareCardsByRarity(a, b);
        });
      } else {
        sortedLite.sort(compareCardsByRarity);
      }

      const total = sortedLite.length;
      const start = (page - 1) * limit;
      const pageLite = sortedLite.slice(start, start + limit);
      const pageIds = pageLite.map(c => c.id);

      if (pageIds.length === 0) {
        return NextResponse.json(
          { data: [], total, page, limit, source: 'db' },
          { headers: { 'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120' } },
        );
      }

      const { data: fullRows, error: fullError } = await supabase
        .from('cards')
        .select(FULL_SELECT_COMPACT)
        .in('id', pageIds);

      if (fullError) throw fullError;

      const byId = new Map((fullRows || []).map(r => [r.id as number, r]));
      const cards = pageIds
        .map(id => byId.get(id))
        .filter(r => r != null)
        .map(r => transformCard(r as Record<string, unknown>, compact));

      return NextResponse.json(
        { data: cards, total, page, limit, source: 'db' },
        { headers: { 'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120' } },
      );
    }

    // ── fallback (unknown sort) ──
    const selectFields = compact
      ? FULL_SELECT_COMPACT
      : `
        id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number,
        card_sets ( id, set_code, name_kr, name_en, name_jp ),
        prices_kr ( price_krw, fetched_at ),
        prices_jp ( price_krw, price_jpy, fetched_at )
      `;

    let countQuery = supabase
      .from('cards')
      .select('id', { count: 'exact', head: true })
      .in('set_id', featuredSetIds)
      .in('rarity', rarity ? rawRaritiesForFilter(rarity) : RAW_DISPLAY_RARITIES);

    countQuery = applySearchFilter(countQuery);
    const { count: rawCount, error: countError } = await countQuery;
    if (countError) throw countError;

    const BATCH = 1000;
    const allRows: Record<string, unknown>[] = [];
    let fetchOffset = (page - 1) * limit;

    while (allRows.length < limit) {
      const batchSize = Math.min(BATCH, limit - allRows.length);
      let query = supabase
        .from('cards')
        .select(selectFields)
        .in('set_id', featuredSetIds)
        .in('rarity', rarity ? rawRaritiesForFilter(rarity) : RAW_DISPLAY_RARITIES);

      query = applySearchFilter(query);
      query = query.order('rarity_rank', { ascending: false }).order('card_number', { ascending: true });

      const { data, error } = await query.range(fetchOffset, fetchOffset + batchSize - 1);
      if (error) throw error;
      if (!data || data.length === 0) break;

      allRows.push(...(data as Record<string, unknown>[]));
      if (data.length < batchSize) break;
      fetchOffset += batchSize;
    }

    if (allRows.length === 0) throw new Error('No data');

    let cards = allRows
      .map(d => transformCard(d, compact))
      .filter(c => isDisplayableRarity(c.rarity));

    return NextResponse.json(
      {
        data: cards,
        total: rawCount || cards.length,
        page,
        limit,
        source: 'db',
      },
      { headers: { 'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120' } },
    );
  } catch (err) {
    console.error('[api/cards] DB error:', err);
    const featuredCodes = CARDS_LIST_SET_CODES as readonly string[];
    let result = MOCK_CARDS.filter(c => featuredCodes.includes(c.setCode) && isDisplayableRarity(c.rarity));
    if (q) result = result.filter(c => matchesSearchQuery(c.name, q) || matchesSearchQuery(c.enName, q));
    if (rarity) result = result.filter(c => c.rarity === rarity);
    if (sort === 'price_asc') result.sort((a, b) => a.priceKR - b.priceKR);
    else if (sort === 'price_desc') result.sort((a, b) => b.priceKR - a.priceKR);
    else result.sort(compareCardsByRarity);

    const start = (page - 1) * limit;
    result = result.slice(start, start + limit);

    return NextResponse.json({ data: result, total: result.length, page, limit, source: 'mock' });
  }
}
