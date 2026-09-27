import type { SupabaseClient } from '@supabase/supabase-js';
import { sameArtPriceIds } from '@/lib/same-art-price-groups';

export type PriceRow = { price_krw: number; fetched_at?: string; source?: string };

type RawPriceRow = {
  card_id: number;
  price_krw: number;
  fetched_at: string | null;
  source: string | null;
};

/** 목록·상세가 같은 기간을 본다 */
const PRICE_LOOKBACK_DAYS = 14;
/** 7일 추이용 — 일별 요약 스냅샷 상한 */
const MAX_SUMMARY_ROWS = 14;
/** 상세 PID row 상한 (거래 내역 API와 별개) */
const DEFAULT_DETAIL_MAX = 12;
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

function mergeSummaryAndDetails(
  summaries: PriceRow[],
  details: PriceRow[],
  detailMax: number,
): PriceRow[] {
  return [...summaries.slice(0, MAX_SUMMARY_ROWS), ...details.slice(0, detailMax)];
}

function tradePid(source?: string | null): string | null {
  if (!isTradeDetailSource(source)) return null;
  const pid = (source || '').split(':')[2];
  return pid && /^\d+$/.test(pid) ? pid : null;
}

/** 같은 그림 묶음의 거래를 상품 ID당 한 번만 남긴다. 카드별 요약은 넣지 않는다. */
function sharedDetailRows(cardId: number, byCard: Map<number, PriceRow[]>, detailMax: number): PriceRow[] | null {
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
  return [...byPid.values()].sort(comparePriceRows).slice(0, detailMax);
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
  sinceIso: string,
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
        .gte('fetched_at', sinceIso)
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

function rowsForCard(cardId: number, byCard: Map<number, PriceRow[]>, detailMax: number): PriceRow[] {
  const shared = sharedDetailRows(cardId, byCard, detailMax);
  if (shared) return shared;
  const { summaries, details } = splitSummaryDetail(byCard.get(cardId) || []);
  return mergeSummaryAndDetails(summaries, details, detailMax);
}

/** 카드 상세. 목록과 같은 조회·같은 계산을 쓴다. */
export async function fetchPricesForCardDetail(
  supabase: SupabaseClient,
  cardId: number,
): Promise<{ kr: PriceRow[]; jp: PriceRow[] }> {
  const map = await fetchRecentPricesByCard(supabase, [cardId]);
  return map.get(cardId) ?? { kr: [], jp: [] };
}

/** 카드별 최근 시세. 목록·세트·상세가 같은 14일을 본다. */
export async function fetchRecentPricesByCard(
  supabase: SupabaseClient,
  cardIds: number[],
  opts?: { daysBack?: number; perCardMax?: number },
): Promise<Map<number, { kr: PriceRow[]; jp: PriceRow[] }>> {
  const out = new Map<number, { kr: PriceRow[]; jp: PriceRow[] }>();
  if (!cardIds.length) return out;

  for (const id of cardIds) {
    out.set(id, { kr: [], jp: [] });
  }

  const daysBack = opts?.daysBack ?? PRICE_LOOKBACK_DAYS;
  const detailMax = opts?.perCardMax ?? DEFAULT_DETAIL_MAX;
  const since = new Date();
  since.setDate(since.getDate() - daysBack);
  const sinceIso = since.toISOString();
  const fetchIds = expandIds(cardIds);

  const [krRows, jpRows] = await Promise.all([
    fetchPriceRowsForCards(supabase, 'prices_kr', fetchIds, sinceIso),
    fetchPriceRowsForCards(supabase, 'prices_jp', fetchIds, sinceIso),
  ]);

  const krByCard = bucketRows(krRows);
  const jpByCard = bucketRows(jpRows);

  for (const id of cardIds) {
    out.set(id, {
      kr: rowsForCard(id, krByCard, detailMax),
      jp: rowsForCard(id, jpByCard, detailMax),
    });
  }

  return out;
}
