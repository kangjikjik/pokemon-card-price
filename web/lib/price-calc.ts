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

function extractBunjangTradeTs(source?: string | null): number | null {
  if (!source) return null;
  const parts = source.split(':');
  if (parts.length >= 4 && parts[1] === 'bunjang') {
    const ts = parseInt(parts[3], 10);
    return Number.isNaN(ts) || ts <= 0 ? null : ts;
  }
  return null;
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

/** 일별 요약 + (요약 없는 날) 상세 fetched_at/traded_at 보조로 7일 추이 구성 */
function buildPriceHistory(allPrices: PriceRecord[]): { date: string; price: number }[] {
  const summaries = allPrices.filter(
    (p) => !isTradeDetailSource(p.source) && p.fetched_at && p.price_krw > 0,
  );
  const details = allPrices.filter(
    (p) => isTradeDetailSource(p.source) && p.price_krw > 0,
  );

  const byDate: Record<string, PriceRecord[]> = {};
  const labels: Record<string, string> = {};

  for (const p of summaries) {
    const key = kstDateKey(p.fetched_at!);
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(p);
    labels[key] = kstDateLabel(p.fetched_at!);
  }

  // 요약 없는 날 — 크롤 당일 상세 PID fetched_at으로 보조
  for (const p of details) {
    if (!p.fetched_at) continue;
    const key = kstDateKey(p.fetched_at);
    if (byDate[key]?.length) continue;
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(p);
    labels[key] = kstDateLabel(p.fetched_at);
  }

  // 요약·fetched_at 둘 다 없는 날 — 번개 거래 시각(traded_at)으로 보조
  for (const p of details) {
    const ts = extractBunjangTradeTs(p.source);
    if (!ts) continue;
    const iso = new Date(ts * 1000).toISOString();
    const key = kstDateKey(iso);
    if (byDate[key]?.length) continue;
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(p);
    labels[key] = kstDateLabel(iso);
  }

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 7);
  const cutoffKey = kstDateKey(cutoff.toISOString());

  const sortedKeys = Object.keys(byDate)
    .filter((key) => key >= cutoffKey)
    .sort();
  return sortedKeys.slice(-7).map((key) => ({
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

/**
 * 대표 시세 = 가장 최근 수집일 중앙값.
 * 트렌드 = 최근일 vs 직전 수집일 (%).
 * history = 최근 7개 수집일.
 */
export function calcRepresentativePrice(allPrices: PriceRecord[]): {
  price: number;
  trend: number;
  history: { date: string; price: number }[];
} {
  if (allPrices.length === 0) return { price: 0, trend: 0, history: [] };

  const displayPrices = pricesForDisplay(allPrices);
  if (displayPrices.length === 0) return { price: 0, trend: 0, history: [] };

  const history = buildPriceHistory(allPrices);
  if (history.length === 0) {
    const vals = displayPrices.map((p) => p.price_krw).filter((v) => v > 0);
    if (!vals.length) return { price: 0, trend: 0, history: [] };
    const price = roundDisplayPrice(
      isTradeDetailSource(displayPrices[0]?.source)
        ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
        : median(vals),
    );
    return { price, trend: 0, history: price ? [{ date: '시세', price }] : [] };
  }

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

/**
 * 목록·홈에 보여줄 시세. 카드 상세와 같이 최근 수집일의 대표가다.
 * 예전 거래완료 요약이 있어도, 그 뒤의 호가 요약을 가리지 않는다.
 */
export function latestPriceKrw(
  prices: { price_krw: number; fetched_at?: string; source?: string }[],
): number {
  return calcRepresentativePrice(prices).price;
}
