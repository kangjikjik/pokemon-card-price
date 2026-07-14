"use client";

import { useMemo, useState, useEffect, useLayoutEffect, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Filter, ArrowUpDown, TrendingUp, Loader2, Sparkles } from "lucide-react";
import { type Card, formatKRW } from "@/lib/data";
import {
  compareCardsByRarity,
  getRarityLabel,
  normalizeRarity,
  RARITY_FILTER_GROUPS,
} from "@/lib/rarity";
import { matchesSearchQuery } from "@/lib/search";
import {
  saveCardsListState,
  readSavedCardsState,
  useCardsListBfcacheSync,
  useCardsListScrollRestore,
} from "@/lib/scroll-restore";
import { RarityBadge, CardImage, RegionLabel } from "@/components/ui";
import { ScrollFab } from "@/components/scroll-fab";

export default function CardsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    }>
      <CardsPageContent />
    </Suspense>
  );
}

function CardsPageContent() {
  const searchParams = useSearchParams();
  const searchQuery = (searchParams.get("q") || "").trim().toLowerCase();
  const [allCards, setAllCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeRarity, setActiveRarity] = useState("All");
  const [sortBy, setSortBy] = useState<"rarity" | "price" | "popular">("rarity");
  const [listKey, setListKey] = useState(0);
  const [filtersReady, setFiltersReady] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 40;

  useLayoutEffect(() => {
    const saved = readSavedCardsState();
    if (saved) {
      setActiveRarity(saved.rarity);
      setSortBy(saved.sort);
    }
    setFiltersReady(true);
  }, []);

  const bumpListKey = useCallback(() => setListKey(k => k + 1), []);
  useCardsListBfcacheSync(setActiveRarity, setSortBy, bumpListKey);

  useEffect(() => {
    if ("scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }
  }, []);

  useEffect(() => {
    fetch("/api/cards?limit=5000&sort=rarity_desc")
      .then(r => r.json())
      .then(json => setAllCards(json.data || []))
      .catch(() => setAllCards([]))
      .finally(() => setLoading(false));
  }, []);

  const rarityCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const card of allCards) {
      counts.set(card.rarity, (counts.get(card.rarity) || 0) + 1);
    }
    return counts;
  }, [allCards]);

  const filteredCards = useMemo(() => {
    const target = normalizeRarity(activeRarity);
    let cards =
      activeRarity === "All"
        ? [...allCards]
        : allCards.filter(c => normalizeRarity(c.rarity) === target);

    if (searchQuery) {
      cards = cards.filter(
        c =>
          matchesSearchQuery(c.name, searchQuery) ||
          matchesSearchQuery(c.enName, searchQuery) ||
          matchesSearchQuery(c.set, searchQuery) ||
          matchesSearchQuery(c.setCode, searchQuery),
      );
    }

    cards.sort((a, b) => {
      if (sortBy === "price") return b.priceKR - a.priceKR;
      if (sortBy === "popular") return b.trendKR - a.trendKR;
      return compareCardsByRarity(a, b);
    });

    return cards;
  }, [allCards, activeRarity, searchQuery, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filteredCards.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedCards = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredCards.slice(start, start + PAGE_SIZE);
  }, [filteredCards, currentPage]);

  useEffect(() => {
    setPage(1);
  }, [activeRarity, sortBy, searchQuery]);

  useCardsListScrollRestore(loading, filtersReady && !loading);

  const handleCardClick = () => {
    saveCardsListState(window.scrollY, { rarity: activeRarity, sort: sortBy });
  };

  const goToPage = (next: number) => {
    const clamped = Math.max(1, Math.min(totalPages, next));
    setPage(clamped);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const filterBtnClass = (active: boolean, hasCards: boolean) =>
    `px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
      active
        ? "bg-amber-500 text-white dark:text-slate-900 shadow-sm"
        : hasCards
          ? "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          : "bg-slate-50 text-slate-400 dark:bg-slate-900 dark:text-slate-600 cursor-default"
    }`;

  return (
    <>
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row gap-8">
      <aside className="w-full md:w-72 shrink-0">
        <div className="md:sticky md:top-20 md:max-h-[calc(100vh-6rem)] md:overflow-y-auto space-y-6 md:pr-2">
          <div>
            <h3 className="text-slate-900 dark:text-white font-bold mb-4 flex items-center">
              <Filter className="w-4 h-4 mr-2" /> 레어도 필터
            </h3>

            <button
              onClick={() => setActiveRarity("All")}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-semibold mb-4 transition-colors ${
                activeRarity === "All"
                  ? "bg-amber-500 text-white dark:text-slate-900"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              }`}
            >
              전체 ({allCards.length})
            </button>

            <div className="space-y-5">
              {RARITY_FILTER_GROUPS.map(group => (
                <div key={group.id}>
                  <div className="mb-2">
                    <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">{group.title}</h4>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.rarities.map(code => {
                      const count = rarityCounts.get(code) || 0;
                      const active = activeRarity === code;
                      return (
                        <button
                          key={code}
                          type="button"
                          onClick={() => setActiveRarity(code)}
                          title={getRarityLabel(code)}
                          className={filterBtnClass(active, count > 0 || loading)}
                        >
                          <span className="font-bold">{code}</span>
                          {!loading && (
                            <span className={`ml-1 ${active ? "opacity-90" : "opacity-60"}`}>
                              {count}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>

      <div className="flex-1">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              모든 카드 {!loading && `(${filteredCards.length})`}
            </h2>
            {searchQuery && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                검색: 「{searchParams.get("q")}」
              </p>
            )}
            {activeRarity !== "All" && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {activeRarity} · {getRarityLabel(activeRarity)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setSortBy("rarity")}
              className={`flex items-center px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === "rarity" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm" : "text-slate-500 hover:text-slate-700 dark:text-slate-400"}`}
            >
              <Sparkles className="w-4 h-4 mr-1" /> 등급순
            </button>
            <button
              onClick={() => setSortBy("price")}
              className={`flex items-center px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === "price" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm" : "text-slate-500 hover:text-slate-700 dark:text-slate-400"}`}
            >
              <ArrowUpDown className="w-4 h-4 mr-1" /> 가격순
            </button>
            <button
              onClick={() => setSortBy("popular")}
              className={`flex items-center px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === "popular" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm" : "text-slate-500 hover:text-slate-700 dark:text-slate-400"}`}
            >
              <TrendingUp className="w-4 h-4 mr-1" /> 인기순
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
          </div>
        ) : !filtersReady ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
          </div>
        ) : (
          <>
          <div
            key={`${activeRarity}-${sortBy}-${listKey}-${currentPage}`}
            className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6"
          >
            {pagedCards.map(card => (
              <Link
                href={`/cards/${card.id}`}
                key={card.id}
                onClick={handleCardClick}
                className="group flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden hover:border-amber-500/50 transition-colors shadow-sm hover:shadow-md"
              >
                <div className="aspect-[63/88] p-2 bg-slate-50 dark:bg-slate-950">
                  <div className="w-full h-full relative group-hover:-translate-y-2 group-hover:scale-105 transition-all duration-300">
                    <CardImage imageUrl={card.imageUrl} altText={card.name} colorClass={card.imageColor} />
                  </div>
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <RarityBadge rarity={card.rarity} />
                  </div>
                  <h4 className="text-slate-900 dark:text-white font-semibold truncate mb-3">{card.name}</h4>
                  <div className="mt-auto space-y-2">
                    <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950/50 p-1.5 rounded">
                      <RegionLabel region="KR" />
                      <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                        {card.priceKR > 0 ? formatKRW(card.priceKR) : "미등록"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-950/50 p-1.5 rounded">
                      <RegionLabel region="JP" />
                      <span className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                        {card.priceJP > 0 ? formatKRW(card.priceJP) : "미등록"}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
            {filteredCards.length === 0 && (
              <div className="col-span-full text-center py-16 text-slate-500">
                {searchQuery ? `「${searchParams.get("q")}」 검색 결과가 없습니다.` : "해당 레어도의 카드가 없습니다."}
              </div>
            )}
          </div>

          {filteredCards.length > 0 && (
            <div className="mt-8 flex flex-col gap-4">
              <p className="text-sm text-slate-500 dark:text-slate-400 text-center sm:text-left">
                {(currentPage - 1) * PAGE_SIZE + 1}
                –{Math.min(currentPage * PAGE_SIZE, filteredCards.length)}
                {" / "}
                {filteredCards.length}장 · {currentPage}/{totalPages}페이지
              </p>
              <div className="w-full flex flex-wrap items-center justify-center gap-2 sm:gap-2.5">
                <button
                  type="button"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="min-w-14 px-4 py-2 rounded-lg text-sm font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-200 dark:hover:bg-slate-700"
                >
                  이전
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(p => {
                    if (totalPages <= 13) return true;
                    if (p === 1 || p === totalPages) return true;
                    return Math.abs(p - currentPage) <= 4;
                  })
                  .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                    if (idx > 0 && typeof arr[idx - 1] === "number" && p - (arr[idx - 1] as number) > 1) {
                      acc.push("…");
                    }
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((p, idx) =>
                    p === "…" ? (
                      <span key={`e-${idx}`} className="px-2 text-slate-400 text-sm">…</span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        onClick={() => goToPage(p)}
                        className={`min-w-11 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                          p === currentPage
                            ? "bg-amber-500 text-white dark:text-slate-900"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700"
                        }`}
                      >
                        {p}
                      </button>
                    ),
                  )}
                <button
                  type="button"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="min-w-14 px-4 py-2 rounded-lg text-sm font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-200 dark:hover:bg-slate-700"
                >
                  다음
                </button>
              </div>
            </div>
          )}
          </>
        )}
      </div>
    </div>
    <ScrollFab />
    </>
  );
}
