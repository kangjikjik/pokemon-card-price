/**
 * 시세 표시용 가격 반올림 (반올림·반내림)
 * - 10,000원 미만: 100원 단위 (예: 870 → 900)
 * - 10,000원 이상: 1,000원 단위 (예: 17,300 → 17,000, 185,828 → 186,000)
 */
export function roundDisplayPrice(price: number): number {
  if (!Number.isFinite(price) || price <= 0) return 0;

  const step = price < 10000 ? 100 : 1000;
  return Math.round(price / step) * step;
}
