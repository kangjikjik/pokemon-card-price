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

/** 체결 summary — sold+listing:bunjang, sold:bunjang 등 */
export function isSoldSummarySource(source?: string | null): boolean {
  if (!source) return false;
  if (isTradeDetailSource(source) || isListingSummarySource(source)) return false;
  return (
    source.startsWith('sold:') ||
    source === 'bunjang-jp:sold' ||
    source === 'bunjang:sold' ||
    source === 'bunjang:sold+listing' ||
    source === 'sold+listing:bunjang'
  );
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
    (p) =>
      isTradeDetailSource(p.source) &&
      (p.source?.startsWith('listing:bunjang:') || p.source?.includes(':listing:')),
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

function dayPriceFromRows(rows: PriceRecord[]): number {
  const vals = rows.map((p) => p.price_krw).filter((v) => v > 0);
  if (!vals.length) return 0;
  const useAvg = rows.some(
    (p) => isSoldDetailSource(p.source) || (isListingSummarySource(p.source) && !isTradeDetailSource(p.source)),
  );
  const raw = useAvg
    ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
    : median(vals);
  return roundDisplayPrice(raw);
}

/** 저장된 크롤일 요약을 모두 이어 그린다. 최근 7일로 자르지 않는다. */
function buildPriceHistory(allPrices: PriceRecord[]): { date: string; price: number }[] {
  const summaries = allPrices.filter(
    (p) => !isTradeDetailSource(p.source) && p.fetched_at && p.price_krw > 0,
  );

  const byDate: Record<string, PriceRecord[]> = {};
  const labels: Record<string, string> = {};

  for (const p of summaries) {
    const key = kstDateKey(p.fetched_at!);
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(p);
    labels[key] = kstDateLabel(p.fetched_at!);
  }

  return Object.keys(byDate)
    .sort()
    .map((key) => ({
      date: labels[key],
      price: dayPriceFromRows(byDate[key]),
    }));
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

function detailPid(source?: string | null): string | null {
  if (!isTradeDetailSource(source)) return null;
  const pid = (source || '').split(':')[2];
  return pid && /^\d+$/.test(pid) ? pid : null;
}

function preferTradeRow(current: PriceRecord, next: PriceRecord): PriceRecord {
  const currentSold = isSoldDetailSource(current.source);
  const nextSold = isSoldDetailSource(next.source);
  if (currentSold !== nextSold) return nextSold ? next : current;
  return (next.fetched_at || '') > (current.fetched_at || '') ? next : current;
}

/** 거래 내역과 같은 기준으로 상품당 한 건만 남긴다. */
function dedupedTradeDetails(prices: PriceRecord[]): PriceRecord[] {
  const byPid = new Map<string, PriceRecord>();
  for (const row of prices) {
    if (!isTradeDetailSource(row.source) || row.price_krw <= 0) continue;
    const pid = detailPid(row.source);
    if (!pid) continue;
    const prev = byPid.get(pid);
    byPid.set(pid, prev ? preferTradeRow(prev, row) : row);
  }
  return [...byPid.values()];
}

/** 거래 내역에 남은 판매완료·호가의 평균. 날짜로 자르지 않는다. */
export function averageTradeDetailPrice(prices: PriceRecord[]): number {
  const rows = dedupedTradeDetails(prices);
  if (!rows.length) return 0;
  const raw = Math.round(rows.reduce((sum, row) => sum + row.price_krw, 0) / rows.length);
  return roundDisplayPrice(raw);
}

/** 거래 내역에 남은 가격의 최저·최고. 날짜로 자르지 않는다. */
export function tradeDetailBounds(prices: PriceRecord[]): { min: number; max: number } {
  const rows = dedupedTradeDetails(prices);
  if (!rows.length) return { min: 0, max: 0 };
  const values = rows.map((row) => row.price_krw);
  return { min: Math.min(...values), max: Math.max(...values) };
}

/**
 * 대표 시세 = 저장된 거래 내역 평균.
 * 트렌드 = 최근일 vs 직전 수집일 (%).
 * history = 저장된 크롤일 전체.
 */
export function calcRepresentativePrice(allPrices: PriceRecord[]): {
  price: number;
  min: number;
  max: number;
  trend: number;
  history: { date: string; price: number }[];
} {
  const bounds = tradeDetailBounds(allPrices);
  if (allPrices.length === 0) return { price: 0, min: 0, max: 0, trend: 0, history: [] };

  const history = buildPriceHistory(allPrices);
  const price = averageTradeDetailPrice(allPrices);
  if (price <= 0 && history.length === 0) {
    return { price: 0, min: 0, max: 0, trend: 0, history: [] };
  }

  let trend = 0;
  if (history.length >= 2) {
    const older = history[history.length - 2].price;
    const newer = history[history.length - 1].price;
    if (older > 0) {
      trend = Math.round(((newer - older) / older) * 1000) / 10;
    }
  }

  return {
    price,
    min: bounds.min,
    max: bounds.max,
    trend,
    history: history.length > 0 ? history : price > 0 ? [{ date: '시세', price }] : [],
  };
}

/**
 * 목록·홈에 보여줄 시세. 카드 상세와 같이 거래 내역 평균이다.
 */
export function latestPriceKrw(
  prices: { price_krw: number; fetched_at?: string; source?: string }[],
): number {
  return calcRepresentativePrice(prices).price;
}
