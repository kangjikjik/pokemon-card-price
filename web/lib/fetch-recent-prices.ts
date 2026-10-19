import type { SupabaseClient } from '@supabase/supabase-js';
import { sameArtPriceIds } from '@/lib/same-art-price-groups';

export type PriceRow = { price_krw: number; fetched_at?: string; source?: string };

type RawPriceRow = {
  card_id: number;
  price_krw: number;
  fetched_at: string | null;
  source: string | null;
};

/** 거래 내역에 쓰는 상세 행. 수집일 14일로 자르지 않는다. */
const DETAIL_SOURCE_OR =
  'source.like.sold:bunjang:%,source.like.listing:bunjang:%,source.like.bunjang:sold:%,source.like.bunjang:listing:%,source.like.bunjang-jp:sold:%,source.like.bunjang-jp:listing:%';
/** 카드당 저장된 거래 상한(50)보다 넉넉히 가져온다. */
const DETAIL_MAX = 100;
/** 시세 추이에 쓰는 요약. 매물 행이 아니다. */
const SUMMARY_SOURCES = [
  'sold+listing:bunjang',
  'sold:bunjang',
  'listing:bunjang',
  'bunjang:sold',
  'bunjang:listing',
  'bunjang:sold+listing',
  'bunjang-jp:sold',
  'bunjang-jp:listing',
  'bunjang-jp:sold+listing',
];
const FETCH_CHUNK = 25;

function isBunjangSource(source?: string | null): boolean {
  if (!source) return false;
  return (
    source === 'bunjang:sold' ||
    source === 'bunjang:listing' ||
    source === 'bunjang:sold+listing' ||
    source === 'bunjang-jp:sold' ||
    source === 'bunjang-jp:listing' ||
    source === 'bunjang-jp:sold+listing' ||
    source === 'sold:bunjang' ||
    source === 'listing:bunjang' ||
    source === 'sold+listing:bunjang' ||
    /^sold:bunjang:\d+/.test(source) ||
    /^listing:bunjang:\d+/.test(source) ||
    /^bunjang-jp:(sold|listing):\d+/.test(source)
  );
}

/** 개별 거래·호가 PID row */
function isTradeDetailSource(source?: string | null): boolean {
  if (!source) return false;
  return (
    /^(sold|listing):bunjang:\d+/.test(source) ||
    /^bunjang-jp:(sold|listing):\d+/.test(source)
  );
}

function comparePriceRows(a: PriceRow, b: PriceRow): number {
  const ta = a.fetched_at || '';
  const tb = b.fetched_at || '';
  if (ta !== tb) return tb.localeCompare(ta);
  return (a.source || '').localeCompare(b.source || '');
}

function splitSummaryDetail(rows: PriceRow[]): { summaries: PriceRow[]; details: PriceRow[] } {
  const summaries: PriceRow[] = [];
  const details: PriceRow[] = [];
  for (const row of rows) {
    if (isTradeDetailSource(row.source)) details.push(row);
    else summaries.push(row);
  }
  summaries.sort(comparePriceRows);
  details.sort(comparePriceRows);
  return { summaries, details };
}

function mergeSummaryAndDetails(summaries: PriceRow[], details: PriceRow[]): PriceRow[] {
  return [...summaries, ...details.slice(0, DETAIL_MAX)];
}

function tradePid(source?: string | null): string | null {
  if (!isTradeDetailSource(source)) return null;
  const pid = (source || '').split(':')[2];
  return pid && /^\d+$/.test(pid) ? pid : null;
}

/** 같은 그림 묶음의 거래를 상품 ID당 한 번만 남긴다. 카드별 요약은 넣지 않는다. */
function sharedDetailRows(cardId: number, byCard: Map<number, PriceRow[]>): PriceRow[] | null {
  const ids = sameArtPriceIds(cardId);
  if (ids.length < 2) return null;
  const byPid = new Map<string, PriceRow>();
  for (const id of ids) {
    for (const row of byCard.get(id) || []) {
      const pid = tradePid(row.source);
      if (!pid) continue;
      const prev = byPid.get(pid);
      if (!prev || (row.fetched_at || '') > (prev.fetched_at || '')) byPid.set(pid, row);
    }
  }
  if (byPid.size === 0) return null;
  return [...byPid.values()].sort(comparePriceRows).slice(0, DETAIL_MAX);
}

function expandIds(cardIds: readonly number[]): number[] {
  const out = new Set<number>();
  for (const id of cardIds) {
    for (const sib of sameArtPriceIds(id)) out.add(sib);
  }
  return [...out];
}

async function fetchPriceRowsForCards(
  supabase: SupabaseClient,
  table: 'prices_kr' | 'prices_jp',
  cardIds: number[],
): Promise<RawPriceRow[]> {
  const rows: RawPriceRow[] = [];
  for (let i = 0; i < cardIds.length; i += FETCH_CHUNK) {
    const chunk = cardIds.slice(i, i + FETCH_CHUNK);
    for (let offset = 0, page = 0; page < 20; offset += 1000, page += 1) {
      const { data } = await supabase
        .from(table)
        .select('card_id, price_krw, fetched_at, source')
        .in('card_id', chunk)
        .gt('price_krw', 0)
        .or(DETAIL_SOURCE_OR)
        .order('fetched_at', { ascending: false })
        .range(offset, offset + 999);

      const pageRows = (data || []) as RawPriceRow[];
      rows.push(...pageRows);
      if (pageRows.length < 1000) break;
    }
  }
  return rows;
}

async function fetchSummaryRowsForCards(
  supabase: SupabaseClient,
  table: 'prices_kr' | 'prices_jp',
  cardIds: number[],
): Promise<RawPriceRow[]> {
  const rows: RawPriceRow[] = [];
  for (let i = 0; i < cardIds.length; i += FETCH_CHUNK) {
    const chunk = cardIds.slice(i, i + FETCH_CHUNK);
    for (let offset = 0, page = 0; page < 20; offset += 1000, page += 1) {
      const { data } = await supabase
        .from(table)
        .select('card_id, price_krw, fetched_at, source')
        .in('card_id', chunk)
        .in('source', SUMMARY_SOURCES)
        .gt('price_krw', 0)
        .order('fetched_at', { ascending: false })
        .range(offset, offset + 999);
      const pageRows = (data || []) as RawPriceRow[];
      rows.push(...pageRows);
      if (pageRows.length < 1000) break;
    }
  }
  return rows;
}

function bucketRows(rows: RawPriceRow[]): Map<number, PriceRow[]> {
  const byCard = new Map<number, PriceRow[]>();
  for (const row of rows) {
    if (!isBunjangSource(row.source)) continue;
    const list = byCard.get(row.card_id) || [];
    list.push({
      price_krw: row.price_krw,
      fetched_at: row.fetched_at ?? undefined,
      source: row.source ?? undefined,
    });
    byCard.set(row.card_id, list);
  }
  return byCard;
}

function rowsForCard(cardId: number, byCard: Map<number, PriceRow[]>): PriceRow[] {
  const ids = sameArtPriceIds(cardId);
  const summaryIds = ids.length ? ids : [cardId];
  const summaries: PriceRow[] = [];
  for (const id of summaryIds) {
    summaries.push(...splitSummaryDetail(byCard.get(id) || []).summaries);
  }
  const shared = sharedDetailRows(cardId, byCard);
  if (shared) return mergeSummaryAndDetails(summaries, shared);
  const { details } = splitSummaryDetail(byCard.get(cardId) || []);
  return mergeSummaryAndDetails(summaries, details);
}

/** 카드 상세. 저장된 크롤일 요약을 모두 가져와 추이를 그린다. */
export async function fetchPricesForCardDetail(
  supabase: SupabaseClient,
  cardId: number,
): Promise<{ kr: PriceRow[]; jp: PriceRow[] }> {
  const map = await fetchRecentPricesByCard(supabase, [cardId], { history: true });
  return map.get(cardId) ?? { kr: [], jp: [] };
}

/** 카드별 시세. 목록·세트·상세가 저장된 거래 내역 전체를 본다. */
export async function fetchRecentPricesByCard(
  supabase: SupabaseClient,
  cardIds: number[],
  options?: { history?: boolean },
): Promise<Map<number, { kr: PriceRow[]; jp: PriceRow[] }>> {
  const out = new Map<number, { kr: PriceRow[]; jp: PriceRow[] }>();
  if (!cardIds.length) return out;

  for (const id of cardIds) {
    out.set(id, { kr: [], jp: [] });
  }

  const fetchIds = expandIds(cardIds);

  const summaryFetches = options?.history
    ? [
        fetchSummaryRowsForCards(supabase, 'prices_kr', fetchIds),
        fetchSummaryRowsForCards(supabase, 'prices_jp', fetchIds),
      ]
    : [Promise.resolve([] as RawPriceRow[]), Promise.resolve([] as RawPriceRow[])];
  const [krRows, jpRows, krSummaries, jpSummaries] = await Promise.all([
    fetchPriceRowsForCards(supabase, 'prices_kr', fetchIds),
    fetchPriceRowsForCards(supabase, 'prices_jp', fetchIds),
    ...summaryFetches,
  ]);
  krRows.push(...krSummaries);
  jpRows.push(...jpSummaries);

  const krByCard = bucketRows(krRows);
  const jpByCard = bucketRows(jpRows);

  for (const id of cardIds) {
    out.set(id, {
      kr: rowsForCard(id, krByCard),
      jp: rowsForCard(id, jpByCard),
    });
  }

  return out;
}
