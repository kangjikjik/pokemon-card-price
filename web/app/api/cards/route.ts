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
import { matchesSearchQuery, setMatchesSearchQuery } from '@/lib/search';
import {
  fetchCardIdsPageByPrice,
  fetchCardsByIds,
  fetchCardsPageByPopular,
  fetchCardsPageByRarity,
} from '@/lib/cards-list-query';
import { fetchRecentPricesByCard } from '@/lib/fetch-recent-prices';

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

const CACHE_HEADERS = {
  'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120',
};

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
    lowKR: kr.min,
    highKR: kr.max,
    lowJP: jp.min,
    highJP: jp.max,
    trendKR: kr.trend,
    trendJP: jp.trend,
    historyKR: compact ? [] : kr.history,
    historyJP: compact ? [] : jp.history,
  };
}

async function attachRecentPrices(
  supabase: ReturnType<typeof getSupabaseServer>,
  rows: Record<string, unknown>[],
): Promise<Record<string, unknown>[]> {
  if (!rows.length) return rows;
  const priceMap = await fetchRecentPricesByCard(
    supabase,
    rows.map(r => r.id as number),
  );
  return rows.map(r => {
    const p = priceMap.get(r.id as number);
    return {
      ...r,
      prices_kr: p?.kr ?? [],
      prices_jp: p?.jp ?? [],
    };
  });
}

async function respondWithPage(
  supabase: ReturnType<typeof getSupabaseServer>,
  pageIds: number[],
  total: number,
  page: number,
  limit: number,
  compact: boolean,
) {
  if (pageIds.length === 0) {
    return NextResponse.json(
      { data: [], total, page, limit, source: 'db' },
      { headers: CACHE_HEADERS },
    );
  }

  const fullRows = await fetchCardsByIds(supabase, pageIds);
  const withPrices = await attachRecentPrices(supabase, fullRows);
  const cards = withPrices.map(r => transformCard(r, compact));

  return NextResponse.json(
    { data: cards, total, page, limit, source: 'db' },
    { headers: CACHE_HEADERS },
  );
}

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

    const listFilter = {
      featuredSetIds,
      rawRarities: rarity ? rawRaritiesForFilter(rarity) : RAW_DISPLAY_RARITIES,
      searchQuery: q,
      matchingSetIds,
    };

    if (sort === 'rarity_desc') {
      const { rows, total } = await fetchCardsPageByRarity(supabase, listFilter, page, limit);
      const withPrices = await attachRecentPrices(supabase, rows);
      const cards = withPrices.map(r => transformCard(r, compact));
      return NextResponse.json(
        { data: cards, total, page, limit, source: 'db' },
        { headers: CACHE_HEADERS },
      );
    }

    if (sort === 'popular') {
      const popular = await fetchCardsPageByPopular(supabase, listFilter, page, limit);
      const withPrices = await attachRecentPrices(supabase, popular.rows);
      const cards = withPrices.map(r => transformCard(r, compact));
      return NextResponse.json(
        { data: cards, total: popular.total, page, limit, source: 'db' },
        { headers: CACHE_HEADERS },
      );
    }

    if (sort === 'price_asc' || sort === 'price_desc') {
      const { pageIds, total } = await fetchCardIdsPageByPrice(
        supabase,
        listFilter,
        sort,
        page,
        limit,
      );
      return respondWithPage(supabase, pageIds, total, page, limit, compact);
    }

    // unknown sort — DB 등급순 페이지
    const { rows, total } = await fetchCardsPageByRarity(supabase, listFilter, page, limit);
    const withPrices = await attachRecentPrices(supabase, rows);
    const cards = withPrices.map(r => transformCard(r, compact));
    return NextResponse.json(
      { data: cards, total, page, limit, source: 'db' },
      { headers: CACHE_HEADERS },
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
