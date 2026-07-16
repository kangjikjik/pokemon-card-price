/**
 * 시세 계산 유틸리티
 * 일별 스냅샷(prices_kr / prices_jp)에서 최신가·추이·7일 히스토리를 계산합니다.
 */

import { roundDisplayPrice } from './price-round';

interface PriceRecord {
  price_krw: number;
  fetched_at?: string;
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
    // fetched_at 없는 레거시 행 — 전체 중앙값
    const vals = prices.map((p) => p.price_krw).filter((v) => v > 0);
    const price = roundDisplayPrice(median(vals));
    return { price, trend: 0, history: price ? [{ date: '시세', price }] : [] };
  }

  const history = sortedKeys.slice(-7).map((key) => ({
    date: labels[key],
    price: roundDisplayPrice(median(byDate[key])),
  }));

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

/** 최신 스냅샷 1건의 price_krw (목록/홈용). */
export function latestPriceKrw(prices: { price_krw: number; fetched_at?: string }[]): number {
  if (!prices.length) return 0;
  let best: { price_krw: number; t: number } | null = null;
  for (const p of prices) {
    if (!(p.price_krw > 0)) continue;
    const t = p.fetched_at ? new Date(p.fetched_at).getTime() : 0;
    if (!best || t >= best.t) best = { price_krw: p.price_krw, t };
  }
  return best?.price_krw || 0;
}
