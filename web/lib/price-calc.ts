/**
 * 시세 계산 유틸리티
 * 번개장터/유유테이에서 수집된 다수의 가격 데이터를 분석합니다.
 */

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

/** IQR 방식으로 이상치를 제거합니다. */
function removeOutliers(arr: number[]): number[] {
  if (arr.length < 4) return arr;
  const sorted = [...arr].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const lower = q1 - iqr * 1.5;
  const upper = q3 + iqr * 1.5;
  return sorted.filter(v => v >= lower && v <= upper);
}

/** 가격 데이터에서 대표 시세(중앙값)와 트렌드를 계산합니다. */
export function calcRepresentativePrice(prices: PriceRecord[]): {
  price: number;
  trend: number;
  history: { date: string; price: number }[];
} {
  if (prices.length === 0) return { price: 0, trend: 0, history: [] };

  const all = prices.map(p => p.price_krw).filter(p => p > 0);
  const cleaned = removeOutliers(all);
  const price = median(cleaned);

  // 최근 7일치 히스토리 (날짜별 중앙값)
  const byDate: Record<string, number[]> = {};
  prices.forEach(p => {
    if (!p.fetched_at) return;
    const date = new Date(p.fetched_at).toLocaleDateString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
    }).replace(/\. /g, '-').replace('.', '');
    if (!byDate[date]) byDate[date] = [];
    byDate[date].push(p.price_krw);
  });

  const history = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-7)
    .map(([date, vals]) => ({ date, price: median(vals) }));

  // 트렌드: 최근 절반 vs 이전 절반 비교
  let trend = 0;
  if (cleaned.length >= 4) {
    const half = Math.floor(cleaned.length / 2);
    const older = median(cleaned.slice(0, half));
    const newer = median(cleaned.slice(half));
    if (older > 0) {
      trend = Math.round(((newer - older) / older) * 1000) / 10;
    }
  }

  return { price, trend, history };
}
