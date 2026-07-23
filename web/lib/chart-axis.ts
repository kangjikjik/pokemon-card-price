/** 차트 Y축 눈금 — 데이터 최대값에 맞춰 만/천/백/원 단위를 선택합니다. */
export function chartAxisMax(values: number[]): number {
  return values.reduce((max, v) => (v > max ? v : max), 0);
}

export function formatChartAxisKrw(val: number, maxPrice: number): string {
  const v = Math.round(val);
  if (v === 0) return '₩0';

  if (maxPrice >= 10_000) {
    if (v >= 10_000) return `₩${Math.round(v / 10_000)}만`;
    if (v >= 1_000) return `₩${Math.round(v / 1_000)}천`;
    return `₩${v.toLocaleString('ko-KR')}`;
  }

  if (maxPrice >= 1_000) {
    if (v >= 1_000) return `₩${Math.round(v / 1_000)}천`;
    return `₩${v.toLocaleString('ko-KR')}`;
  }

  if (maxPrice >= 100) {
    return `₩${Math.round(v / 100) * 100}`;
  }

  return `₩${v.toLocaleString('ko-KR')}`;
}
