'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { type Card } from '@/lib/data';
import { RarityBadge, TrendBadge, CardImage } from '@/components/ui';
import {
  PriceVariantProvider,
  PriceVariantTabs,
  ListPriceDisplay,
  ListPriceBlock,
  buildCardPriceMatrix,
} from '@/components/price-variant-ui';

function HighlightCard({ card }: { card: Card }) {
  const matrix = buildCardPriceMatrix(card);

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row gap-8 items-center relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-colors">
      <div className="w-full md:w-1/3 aspect-[63/88] max-w-[280px] shrink-0 transform group-hover:scale-105 transition-transform duration-500">
        <CardImage
          imageUrl={card.imageUrl}
          altText={card.name}
          colorClass={card.imageColor}
          className="shadow-2xl shadow-orange-900/20"
        />
      </div>
      <div className="flex-1 space-y-6 z-10 w-full">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <RarityBadge rarity={card.rarity} />
            <span className="text-slate-500 dark:text-slate-400 text-sm">{card.set}</span>
          </div>
          <h3 className="text-4xl font-bold text-slate-900 dark:text-white mb-1">{card.name}</h3>
          <p className="text-slate-500 dark:text-slate-400">{card.enName}</p>
        </div>

        <PriceVariantTabs />

        <div className="bg-slate-50 dark:bg-slate-950/50 rounded-xl p-5 border border-slate-100 dark:border-slate-800/50">
          <div className="flex items-center justify-between gap-4">
            <ListPriceDisplay matrix={matrix} size="lg" showTrend />
          </div>
        </div>

        <Link
          href={`/cards/${card.id}`}
          className="inline-flex items-center justify-center bg-slate-900 text-white dark:bg-white dark:text-slate-950 px-6 py-3 rounded-lg font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors w-full sm:w-auto shadow-sm"
        >
          상세 분석 보기 <ChevronRight className="w-4 h-4 ml-2" />
        </Link>
      </div>
    </div>
  );
}

function GridCard({ card }: { card: Card }) {
  const matrix = buildCardPriceMatrix(card);

  return (
    <Link
      href={`/cards/${card.id}`}
      className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/50 transition-colors shadow-sm hover:shadow-md"
    >
      <div className="aspect-[63/88] p-4 bg-slate-50 dark:bg-slate-950">
        <div className="w-full h-full relative group-hover:-translate-y-2 group-hover:scale-105 transition-all duration-300">
          <CardImage imageUrl={card.imageUrl} altText={card.name} colorClass={card.imageColor} />
        </div>
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex justify-between items-start mb-2">
          <RarityBadge rarity={card.rarity} />
        </div>
        <h4 className="text-slate-900 dark:text-white font-semibold truncate mb-3">{card.name}</h4>
        <div className="mt-auto">
          <ListPriceBlock matrix={matrix} />
        </div>
      </div>
    </Link>
  );
}

export function HomeHotCardSection({ highlightCard }: { highlightCard: Card }) {
  return (
    <PriceVariantProvider>
      <HighlightCard card={highlightCard} />
    </PriceVariantProvider>
  );
}

export function HomeCardGrid({ cards }: { cards: Card[] }) {
  return (
    <PriceVariantProvider>
      <div className="mb-4">
        <PriceVariantTabs size="sm" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        {cards.map(card => (
          <GridCard key={card.id} card={card} />
        ))}
      </div>
    </PriceVariantProvider>
  );
}
