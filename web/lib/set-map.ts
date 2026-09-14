import type { SetData } from '@/lib/data';
import { getSetBoxImageUrl } from '@/lib/set-images';
import { getSetShortName } from '@/lib/set-names';
import { getSetMsrp } from '@/lib/set-msrp';
import { calcRepresentativePrice } from '@/lib/price-calc';

const SET_COLORS: Record<string, string> = {
  SV2a: 'from-green-500 to-emerald-700',
  SV2D: 'from-purple-500 to-fuchsia-700',
  S12a: 'from-slate-800 to-slate-950',
  SV4a: 'from-cyan-400 to-blue-600',
  S11: 'from-indigo-700 to-purple-900',
  S12: 'from-blue-500 to-indigo-700',
};

export function mapRawSet(raw: {
  id: number | string;
  set_code?: string | null;
  name_kr?: string | null;
  name_jp?: string | null;
  name_en?: string | null;
  released_at?: string | null;
  image_url?: string | null;
  prices_box?: { region: string; price_krw: number; fetched_at?: string; source?: string }[] | null;
}): SetData {
  const prices = Array.isArray(raw.prices_box) ? raw.prices_box : [];
  const code = raw.set_code || '';
  const msrp = getSetMsrp(code);

  // 여러 개별 거래 rows가 저장된 경우 최신일 중앙값 사용 (calcRepresentativePrice)
  const boxPriceKR = calcRepresentativePrice(prices.filter(p => p.region === 'KR')).price;
  const boxPriceJP = calcRepresentativePrice(prices.filter(p => p.region === 'JP')).price;

  return {
    id: String(raw.id),
    name: getSetShortName(code, raw.name_kr || raw.name_jp || raw.name_en || ''),
    enName: raw.name_en || '',
    code,
    releaseDate: raw.released_at || '',
    imageColor: SET_COLORS[code] || 'from-slate-600 to-slate-800',
    imageUrl: getSetBoxImageUrl(code, raw.image_url as string | null),
    boxPriceKR,
    boxPriceJP,
    msrpPackKR: msrp.packKR,
    msrpBoxKR: msrp.boxKR,
    msrpPackJP: msrp.packJP,
    msrpBoxJP: msrp.boxJP,
  };
}
