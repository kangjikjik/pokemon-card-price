'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ChevronLeft, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { type Card, formatKRW } from '@/lib/data';
import { chartAxisMax, formatChartAxisKrw } from '@/lib/chart-axis';
import { RarityBadge, TrendBadge, CardImage, RegionLabel } from '@/components/ui';

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { color: string; name: string; value: number }[]; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-3 rounded-lg shadow-xl">
        <p className="text-slate-500 dark:text-slate-400 text-xs mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm font-bold" style={{ color: entry.color }}>
            {entry.name}: {formatKRW(entry.value)}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function CardDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(true);
  const [chartType, setChartType] = useState<'KR' | 'JP'>('KR');

  useEffect(() => {
    fetch(`/api/cards/${id}`)
      .then(r => r.json())
      .then(json => setCard(json.data || null))
      .catch(() => setCard(null))
      .finally(() => setLoading(false));

    fetch(`/api/cards/${id}/view`, { method: 'POST' }).catch(() => {});
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    );
  }

  if (!card) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8 text-center">
        <p className="text-slate-500">카드를 찾을 수 없습니다.</p>
        <Link href="/cards" className="text-amber-500 hover:underline mt-4 inline-block">목록으로 돌아가기</Link>
      </div>
    );
  }

  const chartData: { name: string; KRW?: number; JPY_converted?: number }[] =
    chartType === 'KR'
      ? card.historyKR.length > 0
        ? card.historyKR.map((kr) => ({ name: kr.date, KRW: kr.price }))
        : [{ name: '데이터 없음', KRW: card.priceKR }]
      : card.historyJP.length > 0
        ? card.historyJP.map((jp) => ({ name: jp.date, JPY_converted: jp.price }))
        : [{ name: '데이터 없음', JPY_converted: card.priceJP }];

  const priceKey = chartType === 'KR' ? 'KRW' : 'JPY_converted';
  const chartMax = chartAxisMax(
    chartData.map((d) => (d[priceKey as keyof typeof d] as number | undefined) ?? 0),
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <button
        onClick={() => router.back()}
        className="inline-flex items-center text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white mb-6 transition-colors"
      >
        <ChevronLeft className="w-4 h-4 mr-1" /> 이전 화면으로 돌아가기
      </button>

      <div className="flex flex-col md:flex-row gap-8 lg:gap-12">
        {/* Card Image */}
        <div className="w-full md:w-1/3 shrink-0">
          <div className="aspect-[63/88] rounded-2xl p-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl relative">
            <CardImage
              imageUrl={card.imageUrl}
              altText={card.name}
              colorClass={card.imageColor}
              className="shadow-[0_0_30px_rgba(0,0,0,0.1)] dark:shadow-[0_0_30px_rgba(0,0,0,0.5)]"
            />
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 space-y-8">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <RarityBadge rarity={card.rarity} />
              <Link
                href={card.setId ? `/sets/${card.setId}` : '/sets'}
                className="text-amber-600 dark:text-amber-500 hover:underline text-sm font-medium"
              >
                {card.set}
              </Link>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 dark:text-white mb-2">{card.name}</h1>
            <p className="text-xl text-slate-500 dark:text-slate-400">{card.enName}</p>
            {card.number && <p className="text-sm text-slate-400 mt-1">No. {card.number}</p>}
          </div>

          {/* Price Comparison */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-slate-50 dark:from-slate-900 dark:to-slate-950 border border-blue-200 dark:border-blue-900/30 rounded-xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none text-6xl">🇰🇷</div>
              <div className="flex justify-between items-center mb-4 relative z-10">
                <RegionLabel region="KR" className="text-slate-700 dark:text-slate-300 font-medium" />
                {card.trendKR !== 0 && <TrendBadge value={card.trendKR} />}
              </div>
              <div className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-1 relative z-10">
                {card.priceKR > 0 ? formatKRW(card.priceKR) : '시세 미등록'}
              </div>
              <p className="text-slate-500 text-sm relative z-10">최근 거래 기준</p>
            </div>

            <div className="bg-gradient-to-br from-red-50 to-slate-50 dark:from-slate-900 dark:to-slate-950 border border-red-200 dark:border-red-900/30 rounded-xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none text-6xl">🇯🇵</div>
              <div className="flex justify-between items-center mb-4 relative z-10">
                <RegionLabel region="JP" className="text-slate-700 dark:text-slate-300 font-medium" />
                {card.trendJP !== 0 && <TrendBadge value={card.trendJP} />}
              </div>
              <div className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-1 relative z-10">
                {card.priceJP > 0 ? formatKRW(card.priceJP) : '시세 미등록'}
              </div>
              <p className="text-slate-500 text-sm relative z-10">최근 거래 기준</p>
            </div>
          </div>

          {/* Price Chart */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">시세 추이 (7일)</h3>
              <div className="flex bg-slate-100 dark:bg-slate-950 p-1 rounded-lg">
                <button
                  onClick={() => setChartType('KR')}
                  className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${chartType === 'KR' ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                >
                  🇰🇷 한국판
                </button>
                <button
                  onClick={() => setChartType('JP')}
                  className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${chartType === 'JP' ? 'bg-white dark:bg-slate-800 text-red-600 dark:text-red-400 shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                >
                  🇯🇵 일본판
                </button>
              </div>
            </div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" strokeOpacity={0.5} vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => formatChartAxisKrw(val, chartMax)} />
                  <Tooltip content={<CustomTooltip />} />
                  {chartType === 'KR' && (
                    <Line type="monotone" name="한국판" dataKey="KRW" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                  )}
                  {chartType === 'JP' && (
                    <Line type="monotone" name="일본판" dataKey="JPY_converted" stroke="#ef4444" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
