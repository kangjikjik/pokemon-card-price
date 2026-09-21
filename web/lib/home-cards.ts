import { getSupabaseServer } from '@/lib/supabase';
import { type Card } from '@/lib/data';
import { calcRepresentativePrice, latestPriceKrw } from '@/lib/price-calc';
import { EXPANSION_SET_CODES, WEEKLY_HOT_CARD, CARDS_LIST_SET_CODES } from '@/lib/constants';
import { getSetShortName } from '@/lib/set-names';
import { mapRawSet } from '@/lib/set-map';
import type { SetData } from '@/lib/data';
import { viewCountFromRow } from '@/lib/card-sort-helpers';
import { fetchRecentPricesByCard } from '@/lib/fetch-recent-prices';
import { fetchRecentBoxPricesBySet } from '@/lib/fetch-recent-box-prices';

const SET_COLORS: Record<string, string> = {
  SV2a: 'from-green-500 to-emerald-700',
  SV2D: 'from-purple-500 to-fuchsia-700',
  S12a: 'from-slate-800 to-slate-950',
  SV4a: 'from-cyan-400 to-blue-600',
  S11:  'from-indigo-700 to-purple-900',
  S12:  'from-blue-500 to-indigo-700',
  'PRM-MISC': 'from-red-400 to-orange-600',
  CEL30: 'from-amber-400 to-rose-600',
};

const CARD_SELECT = `
  id, name_kr, name_en, name_jp, rarity, rarity_rank, image_url, image_color, card_number,
  card_sets ( id, set_code, name_kr )
`;

const CARD_SELECT_WITH_VIEWS = `
  id, name_kr, name_en, name_jp, rarity, rarity_rank, image_url, image_color, card_number, view_count,
  card_sets ( id, set_code, name_kr )
`;

function isMissingViewCountError(err: unknown): boolean {
  if (err && typeof err === 'object') {
    const e = err as { code?: string; message?: string };
    if (e.code === '42703') return true;
    if (e.message?.includes('view_count')) return true;
  }
  const msg = String(err);
  return msg.includes('view_count') && (msg.includes('42703') || msg.includes('does not exist'));
}

function mapRawToCard(
  raw: Record<string, unknown>,
  priceMap: Map<number, { kr: { price_krw: number; fetched_at?: string }[]; jp: { price_krw: number; fetched_at?: string }[] }>,
  compact = true,
): Card {
  const cid = raw.id as number;
  const p = priceMap.get(cid);
  const pricesKR = p?.kr ?? [];
  const pricesJP = p?.jp ?? [];
  const setRaw = raw.card_sets;
  const set = (Array.isArray(setRaw) ? setRaw[0] : setRaw) as {
    id: number;
    set_code: string;
    name_kr: string;
  } | null;

  const kr = calcRepresentativePrice(pricesKR);
  const jp = calcRepresentativePrice(pricesJP);

  return {
    id: String(raw.id),
    name: (raw.name_kr as string) || (raw.name_jp as string) || (raw.name_en as string) || '',
    enName: (raw.name_en as string) || '',
    set: getSetShortName(set?.set_code || '', set?.name_kr || ''),
    setCode: set?.set_code || '',
    setId: set?.id != null ? String(set.id) : '',
    number: (raw.card_number as string) || '',
    rarity: (raw.rarity as string) || '',
    rarityRank: (raw.rarity_rank as number) || 0,
    imageUrl: (raw.image_url as string) || '',
    imageColor:
      (raw.image_color as string) ||
      SET_COLORS[set?.set_code || ''] ||
      'from-slate-400 to-slate-600',
    priceKR: compact ? latestPriceKrw(pricesKR) : kr.price,
    priceJP: compact ? latestPriceKrw(pricesJP) : jp.price,
    trendKR: kr.trend,
    trendJP: jp.trend,
    historyKR: compact ? [] : kr.history,
    historyJP: compact ? [] : jp.history,
  };
}

async function fetchWeeklyHotCard(supabase: ReturnType<typeof getSupabaseServer>): Promise<Card | null> {
  const { data, error } = await supabase
    .from('cards')
    .select(CARD_SELECT)
    .eq('id', WEEKLY_HOT_CARD.cardId)
    .maybeSingle();

  if (error || !data) return null;
  const priceMap = await fetchRecentPricesByCard(
    supabase,
    [WEEKLY_HOT_CARD.cardId],
    { daysBack: 90 },
  );
  return mapRawToCard(data as Record<string, unknown>, priceMap);
}

async function fetchTrendingCards(
  supabase: ReturnType<typeof getSupabaseServer>,
  featuredSetIds: number[],
  excludeId: number,
  limit = 4,
): Promise<Card[]> {
  if (featuredSetIds.length === 0) return [];

  let rows: Record<string, unknown>[] | null = null;

  const tryViewSort = await supabase
    .from('cards')
    .select(CARD_SELECT_WITH_VIEWS)
    .in('set_id', featuredSetIds)
    .neq('id', excludeId)
    .order('view_count', { ascending: false })
    .limit(limit + 8);

  if (tryViewSort.error) {
    if (!isMissingViewCountError(tryViewSort.error)) throw tryViewSort.error;
    const fallback = await supabase
      .from('cards')
      .select(CARD_SELECT)
      .in('set_id', featuredSetIds)
      .neq('id', excludeId)
      .order('rarity_rank', { ascending: false })
      .limit(limit + 8);
    if (fallback.error) throw fallback.error;
    rows = (fallback.data || []) as Record<string, unknown>[];
  } else {
    rows = (tryViewSort.data || []) as Record<string, unknown>[];
    rows.sort((a, b) => viewCountFromRow(b) - viewCountFromRow(a));
  }

  const slice = rows.slice(0, limit);
  const ids = slice.map(r => r.id as number);
  const priceMap = await fetchRecentPricesByCard(supabase, ids);
  return slice.map(r => mapRawToCard(r, priceMap));
}

export async function getHomePageData(): Promise<{
  highlight: Card;
  trending: Card[];
  sets: SetData[];
}> {
  const supabase = getSupabaseServer();

  const { data: listSets } = await supabase
    .from('card_sets')
    .select('id')
    .in('set_code', [...CARDS_LIST_SET_CODES]);
  const featuredSetIds = (listSets || []).map(s => s.id);

  const highlight = await fetchWeeklyHotCard(supabase);
  if (!highlight) throw new Error('weekly hot card not found');

  const [trending, setsResult] = await Promise.all([
    fetchTrendingCards(supabase, featuredSetIds, WEEKLY_HOT_CARD.cardId),
    supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_en, released_at, image_url`)
      .in('set_code', [...EXPANSION_SET_CODES])
      .order('released_at', { ascending: false })
      .limit(4),
  ]);

  if (setsResult.error) throw setsResult.error;

  const setIds = (setsResult.data || []).map(s => s.id as number);
  const boxMap = await fetchRecentBoxPricesBySet(supabase, setIds);
  const sets = (setsResult.data || []).map(raw =>
    mapRawSet({ ...raw, prices_box: boxMap.get(raw.id as number) ?? [] }),
  );
  return { highlight, trending, sets };
}
