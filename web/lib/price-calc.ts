/**
 * 시세 계산 유틸리티
 * 일별 스냅샷(prices_kr / prices_jp)에서 최신가·추이·7일 히스토리를 계산합니다.
 */

import { roundDisplayPrice } from './price-round';

interface PriceRecord {
  price_krw: number;
  fetched_at?: string;
  source?: string;
}

/** 개별 거래·호가 row (sold:bunjang:PID, bunjang:sold:PID 등) */
export function isTradeDetailSource(source?: string | null): boolean {
  if (!source) return false;
  return (
    /^(sold|listing):bunjang:\d+/.test(source) ||
    /^sold:snkrdunk:\d+/.test(source) ||
    /^bunjang(-jp)?:(sold|listing):\d+/.test(source)
  );
}

function isSoldDetailSource(source?: string | null): boolean {
  if (!source) return false;
  if (source.startsWith('sold:') && isTradeDetailSource(source)) return true;
  return isTradeDetailSource(source) && source.includes(':sold:');
}

/** 호가 summary — 대표 시세(체결 평균) 계산에서 제외 */
export function isListingSummarySource(source?: string | null): boolean {
  if (!source) return false;
  return source.startsWith('listing:') || source === 'bunjang-jp:listing' || source === 'bunjang:listing';
}

/** 체결 summary — sold:bunjang, sold:bunjang+snkrdunk 등 */
export function isSoldSummarySource(source?: string | null): boolean {
  if (!source) return false;
  if (isTradeDetailSource(source) || isListingSummarySource(source)) return false;
  return source.startsWith('sold:') || source === 'bunjang-jp:sold' || source === 'bunjang:sold';
}

/** 박스 개별 거래 row (bunjang(-jp):sold:PID:TS) */
export function isBoxTradeDetailSource(source?: string | null): boolean {
  if (!source) return false;
  const parts = source.split(':');
  return parts.length >= 3 && /^\d+$/.test(parts[2]);
}

/** 목록·상세에 쓸 대표가 row — 체결 우선, 없으면 호가 summary */
export function pricesForDisplay(prices: PriceRecord[]): PriceRecord[] {
  const soldSummary = prices.filter(
    (p) => isSoldSummarySource(p.source) && !isTradeDetailSource(p.source),
  );
  if (soldSummary.length > 0) return soldSummary;

  const soldDetails = prices.filter((p) => isSoldDetailSource(p.source));
  if (soldDetails.length > 0) return soldDetails;

  const listingSummary = prices.filter(
    (p) => isListingSummarySource(p.source) && !isTradeDetailSource(p.source),
  );
  if (listingSummary.length > 0) return listingSummary;

  const listingDetails = prices.filter(
    (p) => isTradeDetailSource(p.source) && p.source?.includes(':listing:'),
  );
  return listingDetails.length > 0 ? listingDetails : [];
}

/** 배열의 중앙값을 반환합니다. */
function median(arr: number[]): number {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

/** KST 기준 YYYY-MM-DD */
function kstDateKey(iso: string): string {
  return new Date(iso).toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
}

/** 표시용 MM-DD (KST) */
function kstDateLabel(iso: string): string {
  return new Date(iso)
    .toLocaleDateString('ko-KR', {
      timeZone: 'Asia/Seoul',
      month: '2-digit',
      day: '2-digit',
    })
    .replace(/\. /g, '-')
    .replace('.', '');
}

/**
 * 대표 시세 = 가장 최근 수집일 중앙값.
 * 트렌드 = 최근일 vs 직전 수집일 (%).
 * history = 최근 7개 수집일.
 */
export function calcRepresentativePrice(prices: PriceRecord[]): {
  price: number;
  trend: number;
  history: { date: string; price: number }[];
} {
  prices = pricesForDisplay(prices);
  if (prices.length === 0) return { price: 0, trend: 0, history: [] };

  const byDate: Record<string, number[]> = {};
  const labels: Record<string, string> = {};

  for (const p of prices) {
    if (!p.fetched_at || !(p.price_krw > 0)) continue;
    const key = kstDateKey(p.fetched_at);
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(p.price_krw);
    labels[key] = kstDateLabel(p.fetched_at);
  }

  const sortedKeys = Object.keys(byDate).sort();
  if (sortedKeys.length === 0) {
    const vals = prices.map((p) => p.price_krw).filter((v) => v > 0);
    if (!vals.length) return { price: 0, trend: 0, history: [] };
    const price = roundDisplayPrice(
      isTradeDetailSource(prices[0]?.source) ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : median(vals),
    );
    return { price, trend: 0, history: price ? [{ date: '시세', price }] : [] };
  }

  const history = sortedKeys.slice(-7).map((key) => {
    const vals = byDate[key];
    const dayRows = prices.filter((p) => p.fetched_at && kstDateKey(p.fetched_at) === key);
    const useAvg = dayRows.some((p) => isSoldDetailSource(p.source) || isListingSummarySource(p.source));
    const raw = useAvg ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : median(vals);
    return { date: labels[key], price: roundDisplayPrice(raw) };
  });

  const price = history[history.length - 1]?.price || 0;

  let trend = 0;
  if (history.length >= 2) {
    const older = history[history.length - 2].price;
    const newer = history[history.length - 1].price;
    if (older > 0) {
      trend = Math.round(((newer - older) / older) * 1000) / 10;
    }
  }

  return { price, trend, history };
}

/** 최신 수집일(KST) 기준 price_krw. 해당일 스냅샷이 0이면 미등록. */
export function latestPriceKrw(
  prices: { price_krw: number; fetched_at?: string; source?: string }[],
): number {
  prices = pricesForDisplay(prices);
  if (!prices.length) return 0;

  const byDate: Record<string, { price_krw: number; t: number }> = {};
  for (const p of prices) {
    if (!p.fetched_at) continue;
    const key = kstDateKey(p.fetched_at);
    const t = new Date(p.fetched_at).getTime();
    const cur = byDate[key];
    if (!cur || t >= cur.t) {
      byDate[key] = { price_krw: p.price_krw, t };
    }
  }

  const datedKeys = Object.keys(byDate).sort();
  if (datedKeys.length > 0) {
    const latest = byDate[datedKeys[datedKeys.length - 1]];
    return latest.price_krw > 0 ? latest.price_krw : 0;
  }

  // fetched_at 없는 레거시 — 양수만
  let best: { price_krw: number; t: number } | null = null;
  for (const p of prices) {
    if (!(p.price_krw > 0)) continue;
    const t = p.fetched_at ? new Date(p.fetched_at).getTime() : 0;
    if (!best || t >= best.t) best = { price_krw: p.price_krw, t };
  }
  return best?.price_krw || 0;
}
