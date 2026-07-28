'use client';

import { buildCardPriceMatrix, variantLabel } from '@/lib/price-variant';
import {
  PriceVariantProvider,
  PriceVariantTabs,
  ListPriceDisplay,
  usePriceVariant,
} from '@/components/price-variant-ui';
import { ClickableTableRow } from '@/components/clickable-table-row';
import { RarityBadge } from '@/components/ui';
import { latestPriceKrw } from '@/lib/price-calc';

type SetCardRow = {
  id: number | string;
  name_kr: string;
  name_jp: string;
  name_en: string;
  rarity: string;
  card_number: string;
  prices_kr: { price_krw: number; fetched_at?: string }[];
  prices_jp: { price_krw: number; fetched_at?: string }[];
};

function SetTableBody({ cards }: { cards: SetCardRow[] }) {
  return (
    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
      {cards.map(card => {
        const matrix = buildCardPriceMatrix({
          priceKR: latestPriceKrw(card.prices_kr),
          priceJP: latestPriceKrw(card.prices_jp),
          trendKR: 0,
          trendJP: 0,
        });
        return (
          <ClickableTableRow key={card.id} href={`/cards/${card.id}`}>
            <td className="p-4 font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
              {card.name_kr || card.name_jp || card.name_en}
            </td>
            <td className="p-4">
              <RarityBadge rarity={card.rarity} />
            </td>
            <td className="p-4 text-right font-medium text-slate-900 dark:text-white">
              <ListPriceDisplay matrix={matrix} size="md" />
            </td>
          </ClickableTableRow>
        );
      })}
      {cards.length === 0 && (
        <tr>
          <td colSpan={3} className="p-8 text-center text-slate-500">
            등록된 카드가 없습니다.
          </td>
        </tr>
      )}
    </tbody>
  );
}

function SetPriceHeader() {
  const { region, grade } = usePriceVariant();
  return <span>{variantLabel(region, grade)}</span>;
}

export function SetCardsPriceTable({ cards }: { cards: SetCardRow[] }) {
  return (
    <PriceVariantProvider>
      <div className="px-4 pt-4 pb-2 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
        <PriceVariantTabs size="sm" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 text-sm">
              <th className="p-4 font-medium">카드명</th>
              <th className="p-4 font-medium">레어도</th>
              <th className="p-4 font-medium text-right">
                <SetPriceHeader />
              </th>
            </tr>
          </thead>
          <SetTableBody cards={cards} />
        </table>
      </div>
    </PriceVariantProvider>
  );
}
