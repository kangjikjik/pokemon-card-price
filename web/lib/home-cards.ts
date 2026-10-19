import { getSupabaseServer } from '@/lib/supabase';
import { type Card } from '@/lib/data';
import { calcRepresentativePrice, latestPriceKrw } from '@/lib/price-calc';
import { FEATURED_SET_IDS, WEEKLY_HOT_CARD, TRENDING_CARD_IDS } from '@/lib/constants';
import { getSetShortName } from '@/lib/set-names';
import { mapRawSet } from '@/lib/set-map';
import type { SetData } from '@/lib/data';
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

type HomePicks = {
  hotId: number;
  trendingIds: number[];
  setIds: number[];
};

async function loadHomePicks(supabase: ReturnType<typeof getSupabaseServer>): Promise<HomePicks> {
  const fallback: HomePicks = {
    hotId: WEEKLY_HOT_CARD.cardId,
    trendingIds: [...TRENDING_CARD_IDS],
    setIds: [...FEATURED_SET_IDS],
  };
  const { data, error } = await supabase
    .from('home_highlights')
    .select('kind, rank, card_id, set_id')
    .order('rank', { ascending: true });
  if (error || !data?.length) return fallback;

  const ranked = (kind: string) =>
    data
      .filter(row => row.kind === kind)
      .sort((a, b) => (a.rank as number) - (b.rank as number));

  const hot = ranked('hot_card').find(row => typeof row.card_id === 'number');
  const trending = ranked('trending_card')
    .map(row => row.card_id)
    .filter((id): id is number => typeof id === 'number');
  const sets = ranked('featured_set')
    .map(row => row.set_id)
    .filter((id): id is number => typeof id === 'number');

  return {
    hotId: typeof hot?.card_id === 'number' ? hot.card_id : fallback.hotId,
    trendingIds: trending.length > 0 ? trending : fallback.trendingIds,
    setIds: sets.length > 0 ? sets : fallback.setIds,
  };
}

async function fetchWeeklyHotCard(
  supabase: ReturnType<typeof getSupabaseServer>,
  cardId: number,
): Promise<Card | null> {
  const { data, error } = await supabase
    .from('cards')
    .select(CARD_SELECT)
    .eq('id', cardId)
    .maybeSingle();

  if (error || !data) return null;
  const priceMap = await fetchRecentPricesByCard(supabase, [cardId], { history: true });
  return mapRawToCard(data as Record<string, unknown>, priceMap);
}

async function fetchTrendingCards(
  supabase: ReturnType<typeof getSupabaseServer>,
  ids: number[],
  excludeId: number,
): Promise<Card[]> {
  const orderedIds = ids.filter(id => id !== excludeId);
  if (orderedIds.length === 0) return [];

  const { data, error } = await supabase
    .from('cards')
    .select(CARD_SELECT)
    .in('id', orderedIds);

  if (error) throw error;

  const byId = new Map((data || []).map(r => [r.id as number, r as Record<string, unknown>]));
  const ordered = orderedIds.map(id => byId.get(id)).filter((r): r is Record<string, unknown> => r != null);

  const priceMap = await fetchRecentPricesByCard(supabase, ordered.map(r => r.id as number), { history: true });
  return ordered.map(r => mapRawToCard(r, priceMap));
}

export async function getHomePageData(): Promise<{
  highlight: Card;
  trending: Card[];
  sets: SetData[];
}> {
  const supabase = getSupabaseServer();
  const picks = await loadHomePicks(supabase);

  const highlight = await fetchWeeklyHotCard(supabase, picks.hotId);
  if (!highlight) throw new Error('weekly hot card not found');

  const [trending, setsResult] = await Promise.all([
    fetchTrendingCards(supabase, picks.trendingIds, picks.hotId),
    supabase
      .from('card_sets')
      .select(`id, set_code, name_kr, name_en, released_at, image_url`)
      .in('id', picks.setIds),
  ]);

  if (setsResult.error) throw setsResult.error;

  const bySetId = new Map((setsResult.data || []).map(s => [s.id as number, s]));
  const orderedSets = picks.setIds.map(id => bySetId.get(id)).filter(
    (s): s is NonNullable<typeof s> => s != null,
  );
  const boxMap = await fetchRecentBoxPricesBySet(supabase, picks.setIds);
  const sets = orderedSets.map(raw =>
    mapRawSet({ ...raw, prices_box: boxMap.get(raw.id as number) ?? [] }),
  );
  return { highlight, trending, sets };
}
