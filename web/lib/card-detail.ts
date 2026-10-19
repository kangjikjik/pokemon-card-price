import { cache } from 'react';
import { getSupabaseServer } from '@/lib/supabase';
import { MOCK_CARDS, type Card, formatKRW } from '@/lib/data';
import { calcRepresentativePrice } from '@/lib/price-calc';
import { fetchPricesForCardDetail } from '@/lib/fetch-recent-prices';
import { CARDS_LIST_SET_CODES, isViewableSetCode } from '@/lib/constants';
import { getSetShortName } from '@/lib/set-names';
import { getRarityLabel, normalizeRarity } from '@/lib/rarity';

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || 'https://cardory.cc').replace(/\/$/, '');

const SET_COLORS: Record<string, string> = {
  SV2a: 'from-green-500 to-emerald-700',
  SV2D: 'from-purple-500 to-fuchsia-700',
  S12a: 'from-slate-800 to-slate-950',
  SV4a: 'from-cyan-400 to-blue-600',
  S11: 'from-indigo-700 to-purple-900',
  S12: 'from-blue-500 to-indigo-700',
};

function transformCardRow(raw: Record<string, unknown>): Card {
  const pricesKR = Array.isArray(raw.prices_kr)
    ? (raw.prices_kr as { price_krw: number; fetched_at: string }[])
    : [];
  const pricesJP = Array.isArray(raw.prices_jp)
    ? (raw.prices_jp as { price_krw: number; price_jpy: number; fetched_at: string }[])
    : [];
  const setRaw = raw.card_sets;
  const set = (Array.isArray(setRaw) ? setRaw[0] : setRaw) as {
    id: number;
    set_code: string;
    name_kr: string;
    name_en?: string;
  } | null;

  const kr = calcRepresentativePrice(pricesKR);
  const jp = calcRepresentativePrice(pricesJP);

  return {
    id: String(raw.id),
    name: (raw.name_kr as string) || (raw.name_jp as string) || (raw.name_en as string) || '알 수 없음',
    enName: (raw.name_en as string) || '',
    set: getSetShortName(set?.set_code || '', set?.name_kr || ''),
    setCode: set?.set_code || '',
    setId: set?.id != null ? String(set.id) : '',
    number: (raw.card_number as string) || '',
    rarity: normalizeRarity((raw.rarity as string) || ''),
    rarityRank: (raw.rarity_rank as number) || 0,
    imageUrl: (raw.image_url as string) || '',
    imageColor:
      (raw.image_color as string) || SET_COLORS[set?.set_code || ''] || 'from-slate-400 to-slate-600',
    priceKR: kr.price,
    priceJP: jp.price,
    lowKR: kr.min,
    highKR: kr.max,
    lowJP: jp.min,
    highJP: jp.max,
    trendKR: kr.trend,
    trendJP: jp.trend,
    historyKR: kr.history,
    historyJP: jp.history,
  };
}

export const fetchCardDetailById = cache(async (numericId: number): Promise<Card | null> => {
  if (!Number.isFinite(numericId)) return null;

  try {
    const supabase = getSupabaseServer();
    const { data: cardRow, error } = await supabase
      .from('cards')
      .select(`
        id, name_kr, name_jp, name_en, rarity, rarity_rank, image_url, image_color, card_number,
        card_sets ( id, set_code, name_kr, name_jp, name_en, released_at )
      `)
      .eq('id', numericId)
      .single();

    if (error || !cardRow) return null;

    const setRaw = cardRow.card_sets as { set_code: string } | { set_code: string }[] | null;
    const setCode = (Array.isArray(setRaw) ? setRaw[0] : setRaw)?.set_code || '';
    if (!isViewableSetCode(setCode)) return null;

    const prices = await fetchPricesForCardDetail(supabase, numericId);
    return transformCardRow({
      ...cardRow,
      prices_kr: prices.kr,
      prices_jp: prices.jp,
    } as Record<string, unknown>);
  } catch {
    const viewableCodes = CARDS_LIST_SET_CODES as readonly string[];
    const mock = MOCK_CARDS.find(c => c.id === String(numericId) && viewableCodes.includes(c.setCode));
    return mock ?? null;
  }
});

export function buildCardDetailDescription(card: Card): string {
  const rarityLabel = getRarityLabel(card.rarity);
  const parts = [
    `${card.set} ${card.number} ${card.name}(${rarityLabel}) 포켓몬 카드 시세.`,
  ];
  if (card.priceKR > 0) parts.push(`한국판 ${formatKRW(card.priceKR)}.`);
  if (card.priceJP > 0) parts.push(`일본판 ${formatKRW(card.priceJP)}.`);
  parts.push('번개장터 거래·호가 기준 최근 시세를 카도리에서 확인하세요.');
  return parts.join(' ');
}

export function buildCardDetailTitle(card: Card): string {
  const rarity = card.rarity ? ` ${card.rarity}` : '';
  const price = card.priceKR > 0 ? card.priceKR : card.priceJP;
  const priceLabel = price > 0 ? ` ${formatKRW(price)}` : '';
  return `${card.name}${rarity} 시세${priceLabel}`;
}

export function buildCardDetailJsonLd(card: Card) {
  const url = `${SITE_URL}/cards/${card.id}`;
  const offers: Record<string, unknown>[] = [];
  if (card.priceKR > 0) {
    offers.push({
      '@type': 'Offer',
      priceCurrency: 'KRW',
      price: card.priceKR,
      name: '한국판',
      availability: 'https://schema.org/InStock',
    });
  }
  if (card.priceJP > 0) {
    offers.push({
      '@type': 'Offer',
      priceCurrency: 'KRW',
      price: card.priceJP,
      name: '일본판',
      availability: 'https://schema.org/InStock',
    });
  }

  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: card.name,
    description: buildCardDetailDescription(card),
    image: card.imageUrl || undefined,
    url,
    category: `포켓몬 카드 · ${card.set}`,
    sku: card.number || card.id,
    brand: { '@type': 'Brand', name: 'Pokémon' },
    ...(offers.length ? { offers: offers.length === 1 ? offers[0] : offers } : {}),
  };
}

export function cardDetailCanonicalUrl(cardId: string): string {
  return `${SITE_URL}/cards/${cardId}`;
}
