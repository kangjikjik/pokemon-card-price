'use client';

import { buildCardPriceMatrix, getMatrixPrice, type CardPriceMatrix } from '@/lib/price-variant';
import { ClickableTableRow } from '@/components/clickable-table-row';
import { CardImage, FlagJP, FlagKR, RarityBadge } from '@/components/ui';
import { calcRepresentativePrice } from '@/lib/price-calc';
import { formatKRW } from '@/lib/data';

type SetCardRow = {
  id: number | string;
  name_kr: string;
  name_jp: string;
  name_en: string;
  rarity: string;
  card_number: string;
  image_url?: string;
  prices_kr: { price_krw: number; fetched_at?: string; source?: string }[];
  prices_jp: { price_krw: number; fetched_at?: string; source?: string }[];
};

function RegionPrice({
  flag,
  label,
  price,
}: {
  flag: 'KR' | 'JP';
  label: string;
  price: number;
}) {
  const Flag = flag === 'KR' ? FlagKR : FlagJP;
  return (
    <div className="flex items-center justify-end gap-1">
      <Flag />
      <span className="sr-only">{label}</span>
      <span className="text-sm font-medium tabular-nums whitespace-nowrap text-slate-900 dark:text-white">
        {price > 0 ? formatKRW(price) : '미등록'}
      </span>
    </div>
  );
}

function BothRegionPrices({ matrix }: { matrix: CardPriceMatrix }) {
  const kr = getMatrixPrice(matrix, 'KR', 'raw').price;
  const jp = getMatrixPrice(matrix, 'JP', 'raw').price;
  return (
    <div className="flex flex-col items-end gap-1">
      <RegionPrice flag="KR" label="한국판" price={kr} />
      <RegionPrice flag="JP" label="일본판" price={jp} />
    </div>
  );
}

function SetTableBody({ cards }: { cards: SetCardRow[] }) {
  return (
    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
      {cards.map(card => {
        const matrix = buildCardPriceMatrix({
          priceKR: calcRepresentativePrice(card.prices_kr).price,
          priceJP: calcRepresentativePrice(card.prices_jp).price,
          trendKR: 0,
          trendJP: 0,
        });
        return (
          <ClickableTableRow key={card.id} href={`/cards/${card.id}`}>
            <td className="p-2 w-16">
              <div className="w-12 h-16">
                <CardImage
                  fit="fill"
                  imageUrl={card.image_url}
                  altText={card.name_kr || card.name_jp || card.name_en}
                  colorClass="from-slate-400 to-slate-600"
                />
              </div>
            </td>
            <td className="p-3 sm:p-4 font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
              {card.name_kr || card.name_jp || card.name_en}
            </td>
            <td className="p-3 sm:p-4">
              <RarityBadge rarity={card.rarity} />
            </td>
            <td className="p-3 sm:p-4 text-right">
              <BothRegionPrices matrix={matrix} />
            </td>
          </ClickableTableRow>
        );
      })}
      {cards.length === 0 && (
        <tr>
          <td colSpan={4} className="p-8 text-center text-slate-500">
            등록된 카드가 없습니다.
          </td>
        </tr>
      )}
    </tbody>
  );
}

export function SetCardsPriceTable({ cards }: { cards: SetCardRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm">
            <th className="p-4 font-medium whitespace-nowrap">이미지</th>
            <th className="p-4 font-medium">카드명</th>
            <th className="p-4 font-medium">레어도</th>
            <th className="p-4 font-medium text-right whitespace-nowrap">시세</th>
          </tr>
        </thead>
        <SetTableBody cards={cards} />
      </table>
    </div>
  );
}
