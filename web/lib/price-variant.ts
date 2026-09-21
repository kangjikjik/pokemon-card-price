import type { Card } from '@/lib/data';

export type PriceRegion = 'KR' | 'JP';
export type PriceGrade = 'raw' | 'psa10' | 'brg10';

export interface PriceVariantSnapshot {
  price: number;
  trend: number;
}

export type RegionPriceMap = Record<PriceGrade, PriceVariantSnapshot>;

export interface CardPriceMatrix {
  KR: RegionPriceMap;
  JP: RegionPriceMap;
}

export const PRICE_GRADES: PriceGrade[] = ['raw', 'psa10', 'brg10'];
export const VISIBLE_PRICE_GRADES: PriceGrade[] = ['raw'];

export const GRADE_LABELS: Record<PriceGrade, string> = {
  raw: '싱글',
  psa10: 'PSA10',
  brg10: 'BRG10',
};

export const DEFAULT_PRICE_VARIANT = {
  region: 'KR' as PriceRegion,
  grade: 'raw' as PriceGrade,
};

const STORAGE_KEY = 'price-variant-prefs';

export function readPriceVariantPrefs(): { region: PriceRegion; grade: PriceGrade } {
  if (typeof window === 'undefined') return DEFAULT_PRICE_VARIANT;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PRICE_VARIANT;
    const parsed = JSON.parse(raw) as { region?: PriceRegion; grade?: string };
    const region = parsed.region === 'JP' ? 'JP' : 'KR';
    const g = parsed.grade;
    const grade: PriceGrade =
      g === 'psa10' || g === 'brg10' ? g : g === 'psa9' ? 'brg10' : 'raw';
    return { region, grade };
  } catch {
    return DEFAULT_PRICE_VARIANT;
  }
}

export function writePriceVariantPrefs(region: PriceRegion, grade: PriceGrade) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ region, grade }));
}

/** 현재 DB는 raw 싱글만 — PSA는 추후 크롤 연동 전까지 0 */
export function buildCardPriceMatrix(
  card: Pick<Card, 'priceKR' | 'priceJP' | 'trendKR' | 'trendJP'>,
): CardPriceMatrix {
  const empty = (): PriceVariantSnapshot => ({ price: 0, trend: 0 });
  return {
    KR: {
      raw: { price: card.priceKR, trend: card.trendKR },
      psa10: empty(),
      brg10: empty(),
    },
    JP: {
      raw: { price: card.priceJP, trend: card.trendJP },
      psa10: empty(),
      brg10: empty(),
    },
  };
}

export function getMatrixPrice(
  matrix: CardPriceMatrix,
  region: PriceRegion,
  grade: PriceGrade,
): PriceVariantSnapshot {
  return matrix[region][grade];
}

export function variantLabel(region: PriceRegion, grade: PriceGrade): string {
  const regionLabel = region === 'KR' ? '한국판' : '일본판';
  return `${regionLabel} · ${GRADE_LABELS[grade]}`;
}
