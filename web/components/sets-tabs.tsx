'use client';

import { useState } from 'react';
import type { SetData } from '@/lib/data';
import { SetsGrid } from '@/components/sets-grid';

type TabId = 'expansion' | 'special' | 'promo';

const TABS: { id: TabId; label: string; description: string }[] = [
  { id: 'expansion', label: '확장팩', description: '정규·강화 확장팩' },
  { id: 'special', label: '스페셜 · 기념', description: '25주년 등 기념 컬렉션' },
  { id: 'promo', label: '기타 프로모', description: '기타 프로모팩' },
];

type Props = {
  expansionSets: SetData[];
  specialSets: SetData[];
  promoSets: SetData[];
};

import { useSetsListRestore } from '@/lib/scroll-restore';

export function SetsTabs({ expansionSets, specialSets, promoSets }: Props) {
  const [tab, setTab] = useState<TabId>('expansion');

  useSetsListRestore(true, setTab as any);

  const counts: Record<TabId, number> = {
    expansion: expansionSets.length,
    special: specialSets.length,
    promo: promoSets.length,
  };

  const activeSets =
    tab === 'expansion' ? expansionSets : tab === 'special' ? specialSets : promoSets;

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-8">
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl w-full sm:w-auto overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`shrink-0 px-3 sm:px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                tab === t.id
                  ? 'bg-white dark:bg-slate-900 text-amber-600 dark:text-amber-400 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {t.label}
              <span className="ml-1.5 text-xs font-medium opacity-70">({counts[t.id]})</span>
            </button>
          ))}
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {TABS.find((t) => t.id === tab)?.description}
        </p>
      </div>

      {activeSets.length > 0 ? (
        <SetsGrid sets={activeSets} currentTabId={tab} />
      ) : (
        <p className="text-center py-16 text-slate-500 dark:text-slate-400">
          등록된 세트가 없습니다.
        </p>
      )}
    </>
  );
}
