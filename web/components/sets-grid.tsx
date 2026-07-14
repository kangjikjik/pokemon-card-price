'use client';

import Link from 'next/link';
import type { SetData } from '@/lib/data';
import { SetPackImage } from '@/components/set-pack-image';
import { SetBoxPriceRows } from '@/components/set-box-price';
import { saveSetsListState, useSetsListRestore } from '@/lib/scroll-restore';

type Props = {
  sets: SetData[];
};

export function SetsGrid({ sets }: Props) {
  useSetsListRestore(true);

  const onSetClick = () => {
    saveSetsListState(window.scrollY);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {sets.map(set => (
        <Link
          href={`/sets/${set.id}`}
          key={set.id}
          onClick={onSetClick}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden hover:border-amber-500/50 dark:hover:border-amber-500/50 transition-all group hover:-translate-y-1 shadow-sm hover:shadow-md"
        >
          <div className="pt-6 pb-3 px-4 flex justify-center">
            <SetPackImage imageUrl={set.imageUrl} alt={set.name} colorClass={set.imageColor} size="lg" />
          </div>
          <div className="px-6 pb-6 pt-2">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-1">{set.name}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
              {set.releaseDate ? `발매일: ${set.releaseDate}` : '발매일 미등록'}
            </p>
            <div className="space-y-3">
              <SetBoxPriceRows
                region="KR"
                marketPrice={set.boxPriceKR}
                msrpBox={set.msrpBoxKR}
                msrpPack={set.msrpPackKR}
              />
              <SetBoxPriceRows
                region="JP"
                marketPrice={set.boxPriceJP}
                msrpBox={set.msrpBoxJP}
                msrpPack={set.msrpPackJP}
              />
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
