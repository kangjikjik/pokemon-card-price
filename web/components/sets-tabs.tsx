'use client';

import { useCallback, useState } from 'react';
import type { SetData } from '@/lib/data';
import { SetsGrid } from '@/components/sets-grid';
import { useSetsListRestore } from '@/lib/scroll-restore';

type TabId = 'expansion' | 'commemorative';
type FilterValue = string | null;

const INITIALS = ['ㄱ', 'ㄴ', 'ㄷ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅅ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const FULL_INITIALS = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
  'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
];
const INITIAL_ALIASES: Record<string, string> = {
  'ㄲ': 'ㄱ',
  'ㄸ': 'ㄷ',
  'ㅃ': 'ㅂ',
  'ㅆ': 'ㅅ',
  'ㅉ': 'ㅈ',
};
const LATIN_PREFIX_INITIALS: Array<[RegExp, string]> = [
  [/^pok(?:é|e)?mon/i, 'ㅍ'],
  [/^tag/i, 'ㅌ'],
  [/^gx/i, 'ㅈ'],
  [/^v(?:star|max)/i, 'ㅂ'],
  [/^mega/i, 'ㅁ'],
];

function getInitial(name: string): string {
  const first = name.trim().charAt(0);
  const normalized = name.trim().replace(/\s+/g, '');
  const latinInitial = LATIN_PREFIX_INITIALS.find(([pattern]) => pattern.test(normalized));
  if (latinInitial) return latinInitial[1];

  const code = first.charCodeAt(0) - 0xac00;
  if (code < 0 || code > 11171) return first.toUpperCase();
  const initial = FULL_INITIALS[Math.floor(code / 588)] || first;
  return INITIAL_ALIASES[initial] || initial;
}

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
  const [initial, setInitial] = useState<FilterValue>(null);
  const [year, setYear] = useState<FilterValue>(null);

  const restoreSetsState = useCallback((saved: { tab: string | null; initial: string | null; year: string | null }) => {
    setTab(normalizeTabId(saved.tab));
    setInitial(saved.initial);
    setYear(saved.year);
  }, []);

  useSetsListRestore(true, restoreSetsState);

  const counts: Record<TabId, number> = {
    expansion: expansionSets.length,
    commemorative: commemorativeSets.length,
  };

  const activeSets = tab === 'expansion' ? expansionSets : commemorativeSets;
  const years = Array.from(
    new Set(activeSets.map((set) => set.releaseDate.slice(0, 4)).filter(Boolean)),
  ).sort((a, b) => b.localeCompare(a));
  const filteredSets = activeSets.filter((set) => {
    const matchesInitial = !initial || getInitial(set.name) === initial;
    const matchesYear = !year || set.releaseDate.startsWith(year);
    return matchesInitial && matchesYear;
  });
  const resetScroll = () => window.scrollTo({ top: 0, left: 0, behavior: 'instant' });

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-8">
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl w-full sm:w-auto overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                setTab(t.id);
                setInitial(null);
                setYear(null);
                resetScroll();
              }}
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

      <div className="grid grid-cols-1 lg:grid-cols-[180px_minmax(0,1fr)] gap-8 items-start">
        <aside className="lg:sticky lg:top-24 self-start rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4">세트 찾기</h2>
          <div className="mb-5">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">초성</p>
            <div className="grid grid-cols-4 gap-1">
              <button
                type="button"
                onClick={() => {
                  setInitial(null);
                  setYear(null);
                  resetScroll();
                }}
                className={`whitespace-nowrap rounded px-1.5 py-1 text-xs font-bold ${
                  !initial
                    ? 'bg-amber-500 text-white'
                    : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                전체
              </button>
              {INITIALS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setInitial(item);
                    setYear(null);
                    resetScroll();
                  }}
                  className={`whitespace-nowrap rounded px-1.5 py-1 text-xs font-bold ${
                    initial === item
                      ? 'bg-amber-500 text-white'
                      : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">발매년도</p>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => {
                  setYear(null);
                  setInitial(null);
                  resetScroll();
                }}
                className={`whitespace-nowrap rounded px-2 py-1 text-xs font-bold ${
                  !year
                    ? 'bg-amber-500 text-white'
                    : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                전체
              </button>
              {years.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setYear(item);
                    setInitial(null);
                    resetScroll();
                  }}
                  className={`whitespace-nowrap rounded px-2 py-1 text-xs font-bold ${
                    year === item
                      ? 'bg-amber-500 text-white'
                      : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div>
          {filteredSets.length > 0 ? (
            <SetsGrid
              sets={filteredSets}
              currentTabId={tab}
              currentInitial={initial}
              currentYear={year}
            />
          ) : (
            <p className="text-center py-16 text-slate-500 dark:text-slate-400">
              조건에 맞는 세트가 없습니다.
            </p>
          )}
        </div>
      </div>
    </>
  );
}
