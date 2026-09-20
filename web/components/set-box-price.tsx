'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { formatKRW } from '@/lib/data';
import { formatYen } from '@/lib/set-msrp';
import { RegionLabel } from '@/components/ui';

interface BoxTradeRecord {
  price_krw: number;
  source: string;
  fetched_at: string;
  traded_at?: string;  // 실제 거래 날짜
  label: string;
  url?: string;
}

function formatTradeDate(iso: string): string {
  if (!iso) return '-';
  return new Date(iso)
    .toLocaleDateString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    .replace(/\. /g, '-')
    .replace('.', '');
}

function LabelBadge({ label }: { label: string }) {
  const colors: Record<string, string> = {
    거래완료: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    호가: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  };
  const cls = colors[label] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300';
  return (
    <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${cls}`}>
      {label}
    </span>
  );
}

type Props = {
  setId?: string;
  region: 'KR' | 'JP';
  marketPrice: number;
  msrpBox: number;
  msrpPack: number;
  boxLabel?: string;
};

export const SetBoxPriceRows = ({
  setId,
  region,
  marketPrice,
  msrpBox,
  msrpPack,
  boxLabel = '박스',
}: Props) => {
  const formatMsrp = region === 'KR' ? formatKRW : formatYen;
  const hasMarket = marketPrice > 0;

  const [open, setOpen] = useState(false);
  const [trades, setTrades] = useState<BoxTradeRecord[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (!hasMarket || !setId) return;
    if (!open) {
      setOpen(true);
      if (trades === null) {
        setLoading(true);
        try {
          const res = await fetch(`/api/sets/${setId}/box-trades?region=${region}`);
          const json = await res.json();
          setTrades(json.trades || []);
        } catch {
          setTrades([]);
        } finally {
          setLoading(false);
        }
      }
    } else {
      setOpen(false);
    }
  }

  return (
    <div className="flex flex-col">
      <button
        onClick={handleClick}
        disabled={!hasMarket}
        className={`flex justify-between items-start bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800 gap-3 text-left w-full ${hasMarket && setId ? 'hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors cursor-pointer' : 'cursor-default'}`}
      >
        <RegionLabel region={region} suffix={` ${boxLabel}`} className="text-slate-600 dark:text-slate-400 shrink-0" />
        <div className="text-right min-w-0">
          {hasMarket ? (
            <>
              <div className="text-lg md:text-xl font-bold text-slate-900 dark:text-white leading-tight">
                {formatKRW(marketPrice)}
              </div>
              {setId && (
                <p className="text-xs text-amber-600 dark:text-amber-500 font-medium mt-0.5">
                  거래 시세 {open ? '▲' : '▼ 거래내역'}
                </p>
              )}
              {!setId && (
                <p className="text-xs text-amber-600 dark:text-amber-500 font-medium mt-0.5">
                  거래 시세
                </p>
              )}
            </>
          ) : (
            <div className="text-sm font-medium text-slate-500 dark:text-slate-400">시세 미등록</div>
          )}
          <p className="text-[11px] text-slate-400 mt-1 leading-snug">
            발매가 {formatMsrp(msrpBox)}
            <span className="mx-1">·</span>
            팩 {formatMsrp(msrpPack)}
          </p>
        </div>
      </button>

      {/* 거래내역 패널 */}
      {open && (
        <div className="border border-t-0 border-slate-100 dark:border-slate-800 rounded-b-lg bg-white dark:bg-slate-900 overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
            </div>
          ) : !trades || trades.length === 0 ? (
            <div className="py-6 text-center text-slate-400 dark:text-slate-500 text-sm">
              거래 내역이 없습니다
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-400 dark:text-slate-500 px-4 py-2 border-b border-slate-100 dark:border-slate-800">
                최근 {trades.length}건
              </p>
              <ul className="divide-y divide-slate-100 dark:divide-slate-800 max-h-72 overflow-y-auto">
                {trades.map((t, i) => {
                  const inner = (
                    <>
                      <LabelBadge label={t.label} />
                      <span className="text-xs text-slate-400 dark:text-slate-500 flex-1">
                        {formatTradeDate(t.traded_at || t.fetched_at)}
                      </span>
                      <span className="text-sm font-bold text-slate-900 dark:text-white tabular-nums">
                        {formatKRW(t.price_krw)}
                      </span>
                      {t.url && (
                        <span className="text-xs text-amber-500 shrink-0">↗</span>
                      )}
                    </>
                  );
                  return t.url ? (
                    <li key={i}>
                      <a
                        href={t.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 px-4 py-2.5 hover:bg-amber-50 dark:hover:bg-amber-900/10 transition-colors"
                      >
                        {inner}
                      </a>
                    </li>
                  ) : (
                    <li key={i} className="flex items-center gap-3 px-4 py-2.5">
                      {inner}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
};
