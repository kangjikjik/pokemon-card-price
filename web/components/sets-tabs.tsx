'use client';

import { useState } from 'react';
import type { SetData } from '@/lib/data';
import { SetsGrid } from '@/components/sets-grid';
import { useSetsListRestore } from '@/lib/scroll-restore';

type TabId = 'expansion' | 'commemorative';

const TABS: { id: TabId; label: string; description: string }[] = [
  { id: 'expansion', label: '확장팩', description: '정규·강화 확장팩' },
  { id: 'commemorative', label: '기념 · 프로모카드', description: '25주년 기념·프로모팩' },
];

type Props = {
  expansionSets: SetData[];
  commemorativeSets: SetData[];
};

function normalizeTabId(saved: string | null): TabId {
  if (saved === 'commemorative' || saved === 'special' || saved === 'promo') {
    return 'commemorative';
  }
  return 'expansion';
}

export function SetsTabs({ expansionSets, commemorativeSets }: Props) {
  const [tab, setTab] = useState<TabId>('expansion');

  useSetsListRestore(true, (saved) => setTab(normalizeTabId(saved)));

  const counts: Record<TabId, number> = {
    expansion: expansionSets.length,
    commemorative: commemorativeSets.length,
  };

  const activeSets = tab === 'expansion' ? expansionSets : commemorativeSets;

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
