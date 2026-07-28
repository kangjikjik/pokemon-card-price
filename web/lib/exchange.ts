import { formatKRW } from '@/lib/data';
import { formatYen } from '@/lib/set-msrp';

/** 크롤러·DB 환율과 동일한 기본값 (JPY→KRW) */
export const JPY_TO_KRW = 9.5;

export function krwToYenApprox(krw: number, rate = JPY_TO_KRW): number {
  if (!Number.isFinite(krw) || krw <= 0 || rate <= 0) return 0;
  return Math.round(krw / rate);
}

/** 번개 등 원화 시세 + 엔화 환산 (JP 박스·수입품 표시용) */
export function formatKrwWithYenApprox(krw: number, rate = JPY_TO_KRW): string {
  const yen = krwToYenApprox(krw, rate);
  if (yen <= 0) return formatKRW(krw);
  return `${formatKRW(krw)} (약 ${formatYen(yen)})`;
}
