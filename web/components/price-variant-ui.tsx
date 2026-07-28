'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { cn } from '@/lib/utils';
import { formatKRW } from '@/lib/data';
import { TrendBadge, FlagKR, FlagJP } from '@/components/ui';
import {
  buildCardPriceMatrix,
  DEFAULT_PRICE_VARIANT,
  GRADE_LABELS,
  getMatrixPrice,
  readPriceVariantPrefs,
  variantLabel,
  writePriceVariantPrefs,
  type CardPriceMatrix,
  type PriceGrade,
  type PriceRegion,
  PRICE_GRADES,
} from '@/lib/price-variant';

type PriceVariantContextValue = {
  region: PriceRegion;
  grade: PriceGrade;
  setRegion: (region: PriceRegion) => void;
  setGrade: (grade: PriceGrade) => void;
};

const PriceVariantContext = createContext<PriceVariantContextValue | null>(null);

export function PriceVariantProvider({ children }: { children: ReactNode }) {
  const [region, setRegionState] = useState<PriceRegion>(DEFAULT_PRICE_VARIANT.region);
  const [grade, setGradeState] = useState<PriceGrade>(DEFAULT_PRICE_VARIANT.grade);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const prefs = readPriceVariantPrefs();
    setRegionState(prefs.region);
    setGradeState(prefs.grade);
    setReady(true);
  }, []);

  const persist = useCallback((nextRegion: PriceRegion, nextGrade: PriceGrade) => {
    writePriceVariantPrefs(nextRegion, nextGrade);
  }, []);

  const setRegion = useCallback(
    (next: PriceRegion) => {
      setRegionState(next);
      persist(next, grade);
    },
    [grade, persist],
  );

  const setGrade = useCallback(
    (next: PriceGrade) => {
      setGradeState(next);
      persist(region, next);
    },
    [region, persist],
  );

  const value = useMemo(
    () => ({ region, grade, setRegion, setGrade }),
    [region, grade, setRegion, setGrade],
  );

  if (!ready) {
    return (
      <PriceVariantContext.Provider value={value}>
        {children}
      </PriceVariantContext.Provider>
    );
  }

  return (
    <PriceVariantContext.Provider value={value}>
      {children}
    </PriceVariantContext.Provider>
  );
}

export function usePriceVariant() {
  const ctx = useContext(PriceVariantContext);
  if (!ctx) {
    return {
      region: DEFAULT_PRICE_VARIANT.region,
      grade: DEFAULT_PRICE_VARIANT.grade,
      setRegion: () => {},
      setGrade: () => {},
    };
  }
  return ctx;
}

export function PriceVariantTabs({
  className,
  size = 'md',
}: {
  className?: string;
  size?: 'sm' | 'md';
}) {
  const { region, grade, setRegion, setGrade } = usePriceVariant();
  const pad = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm';

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg w-fit max-w-full">
        {(['KR', 'JP'] as const).map(r => (
          <button
            key={r}
            type="button"
            onClick={() => setRegion(r)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md font-medium transition-colors',
              pad,
              region === r
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400',
            )}
          >
            {r === 'KR' ? <FlagKR /> : <FlagJP />}
            {r === 'KR' ? '한국' : '일본'}
          </button>
        ))}
      </div>
      <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg w-fit max-w-full flex-wrap">
        {PRICE_GRADES.map(g => (
          <button
            key={g}
            type="button"
            onClick={() => setGrade(g)}
            className={cn(
              'rounded-md font-medium transition-colors whitespace-nowrap',
              pad,
              grade === g
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400',
              g === 'psa10' && grade === g && 'text-amber-700 dark:text-amber-400',
              g === 'brg10' && grade === g && 'text-slate-600 dark:text-slate-300',
            )}
          >
            {GRADE_LABELS[g]}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ListPriceDisplay({
  matrix,
  size = 'md',
  showTrend = false,
}: {
  matrix: CardPriceMatrix;
  size?: 'sm' | 'md' | 'lg';
  showTrend?: boolean;
}) {
  const { region, grade } = usePriceVariant();
  const snap = getMatrixPrice(matrix, region, grade);
  const text =
    size === 'lg' ? 'text-3xl md:text-4xl' : size === 'md' ? 'text-sm font-medium' : 'text-sm font-semibold';

  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className={cn('text-slate-900 dark:text-white tabular-nums whitespace-nowrap', text)}>
        {snap.price > 0 ? formatKRW(snap.price) : '미등록'}
      </span>
      {showTrend && snap.trend !== 0 && <TrendBadge value={snap.trend} />}
    </div>
  );
}

export function ListPriceBlock({
  matrix,
  className,
}: {
  matrix: CardPriceMatrix;
  className?: string;
}) {
  const { region, grade } = usePriceVariant();

  return (
    <div className={cn('flex flex-col items-stretch gap-0.5 bg-slate-50 dark:bg-slate-950/50 p-2 rounded-lg min-w-0', className)}>
      <span className="text-xs text-slate-500 dark:text-slate-400 truncate">
        {variantLabel(region, grade)}
      </span>
      <div className="flex justify-end min-w-0">
        <ListPriceDisplay matrix={matrix} size="sm" />
      </div>
    </div>
  );
}

export function PriceMatrix({
  matrix,
  selectedRegion,
  selectedGrade,
  onSelect,
}: {
  matrix: CardPriceMatrix;
  selectedRegion?: PriceRegion;
  selectedGrade?: PriceGrade;
  onSelect?: (region: PriceRegion, grade: PriceGrade) => void;
}) {
  const regions: PriceRegion[] = ['KR', 'JP'];

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="p-2 text-left text-slate-500 dark:text-slate-400 font-medium w-24" />
            {PRICE_GRADES.map(g => (
              <th
                key={g}
                className={cn(
                  'p-2 text-center font-semibold',
                  g === 'raw' && 'text-slate-700 dark:text-slate-200',
                  g === 'psa10' && 'text-amber-600 dark:text-amber-400',
                  g === 'brg10' && 'text-slate-600 dark:text-slate-300',
                )}
              >
                {GRADE_LABELS[g]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {regions.map(region => {
            const isKr = region === 'KR';
            return (
              <tr key={region} className="border-t border-slate-100 dark:border-slate-800">
                <td className="p-2">
                  <span className="inline-flex items-center gap-1.5 font-medium text-slate-700 dark:text-slate-300">
                    {isKr ? <FlagKR /> : <FlagJP />}
                    {isKr ? '한국' : '일본'}
                  </span>
                </td>
                {PRICE_GRADES.map(grade => {
                  const snap = matrix[region][grade];
                  const selected = selectedRegion === region && selectedGrade === grade;
                  const clickable = Boolean(onSelect);
                  return (
                    <td key={grade} className="p-2">
                      <button
                        type="button"
                        disabled={!clickable}
                        onClick={() => onSelect?.(region, grade)}
                        className={cn(
                          'w-full rounded-xl p-3 text-left transition-all border',
                          selected
                            ? isKr
                              ? 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-950/40 ring-2 ring-blue-400/30'
                              : 'border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/40 ring-2 ring-red-400/30'
                            : 'border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/40',
                          clickable && !selected && 'hover:border-amber-400/50 cursor-pointer',
                          !clickable && 'cursor-default',
                        )}
                      >
                        <div
                          className={cn(
                            'font-bold tabular-nums',
                            snap.price > 0
                              ? 'text-slate-900 dark:text-white'
                              : 'text-slate-400 dark:text-slate-500 text-base',
                            grade === 'raw' ? 'text-lg md:text-xl' : 'text-base md:text-lg',
                          )}
                        >
                          {snap.price > 0 ? formatKRW(snap.price) : '미등록'}
                        </div>
                        {snap.trend !== 0 && (
                          <div className="mt-1">
                            <TrendBadge value={snap.trend} />
                          </div>
                        )}
                      </button>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export { buildCardPriceMatrix };
