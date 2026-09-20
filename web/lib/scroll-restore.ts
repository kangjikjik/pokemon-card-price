"use client";

import { useEffect, useLayoutEffect, useRef } from "react";

const SCROLL_KEY = "cards-scroll-y";
const FILTER_KEY = "cards-filters";
const SETS_SCROLL_KEY = "sets-scroll-y";
const SET_DETAIL_PREFIX = "scroll-restore:";

type CardsSort = "rarity" | "price" | "popular";

type SavedCardsState = {
  rarity: string;
  sort: CardsSort;
  scrollY: number | null;
};

function parseSort(sort: string | undefined): CardsSort {
  return sort === "price" || sort === "popular" ? sort : "rarity";
}

/** sessionStorage에 저장된 카드 목록 상태 읽기 (삭제하지 않음) */
export function readSavedCardsState(): SavedCardsState | null {
  if (typeof window === "undefined") return null;
  try {
    const rawFilters = sessionStorage.getItem(FILTER_KEY);
    const rawScroll = sessionStorage.getItem(SCROLL_KEY);
    if (!rawFilters && !rawScroll) return null;

    const parsed = rawFilters
      ? (JSON.parse(rawFilters) as { rarity?: string; sort?: string })
      : {};
    return {
      rarity: parsed.rarity || "All",
      sort: parseSort(parsed.sort),
      scrollY: rawScroll ? parseInt(rawScroll, 10) : null,
    };
  } catch {
    return null;
  }
}

export function getInitialCardsRarity(): string {
  return readSavedCardsState()?.rarity ?? "All";
}

export function getInitialCardsSort(): CardsSort {
  return readSavedCardsState()?.sort ?? "rarity";
}

function clearSavedCardsState() {
  sessionStorage.removeItem(FILTER_KEY);
  sessionStorage.removeItem(SCROLL_KEY);
}

export function saveSetsListState(
  scrollY: number,
  tabId: string,
  initial: string | null = null,
  year: string | null = null,
) {
  sessionStorage.setItem(SETS_SCROLL_KEY, String(scrollY));
  sessionStorage.setItem(`${SETS_SCROLL_KEY}-tab`, tabId);
  sessionStorage.setItem(`${SETS_SCROLL_KEY}-initial`, initial ?? "");
  sessionStorage.setItem(`${SETS_SCROLL_KEY}-year`, year ?? "");
}

export function useSetsListRestore(
  ready = true,
  restoreState?: (state: { tab: string | null; initial: string | null; year: string | null }) => void,
) {
  useEffect(() => {
    if (!ready) return;
    if ("scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }
    const savedTab = sessionStorage.getItem(`${SETS_SCROLL_KEY}-tab`);
    const savedInitial = sessionStorage.getItem(`${SETS_SCROLL_KEY}-initial`);
    const savedYear = sessionStorage.getItem(`${SETS_SCROLL_KEY}-year`);
    if (restoreState) {
      restoreState({
        tab: savedTab,
        initial: savedInitial || null,
        year: savedYear || null,
      });
    }

    const savedScroll = sessionStorage.getItem(SETS_SCROLL_KEY);
    if (!savedScroll) return;

    const y = parseInt(savedScroll, 10);
    const restore = () => window.scrollTo(0, y);

    requestAnimationFrame(() => {
      requestAnimationFrame(restore);
    });
    const t = window.setTimeout(() => {
      restore();
      sessionStorage.removeItem(SETS_SCROLL_KEY);
      sessionStorage.removeItem(`${SETS_SCROLL_KEY}-tab`);
      sessionStorage.removeItem(`${SETS_SCROLL_KEY}-initial`);
      sessionStorage.removeItem(`${SETS_SCROLL_KEY}-year`);
    }, 150);

    return () => window.clearTimeout(t);
  }, [ready, restoreState]);
}

export function saveCardsListState(scrollY: number, filters: { rarity: string; sort: string }) {
  sessionStorage.setItem(SCROLL_KEY, String(scrollY));
  sessionStorage.setItem(FILTER_KEY, JSON.stringify(filters));
}

/** bfcache 복원 시 필터·스크롤 재동기화 */
export function useCardsListBfcacheSync(
  setActiveRarity: (v: string) => void,
  setSortBy: (v: CardsSort) => void,
  bumpListKey: () => void,
) {
  useEffect(() => {
    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return;
      const saved = readSavedCardsState();
      if (!saved) return;
      setActiveRarity(saved.rarity);
      setSortBy(saved.sort);
      bumpListKey();
      if (saved.scrollY !== null) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => window.scrollTo(0, saved.scrollY!));
        });
      }
    };
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, [setActiveRarity, setSortBy, bumpListKey]);
}

/** 데이터 로드 후 스크롤 복원 — 필터는 초기 state에서 동기 적용 */
export function useCardsListScrollRestore(loading: boolean, listReady: boolean) {
  const restoredRef = useRef(false);

  useLayoutEffect(() => {
    if (loading || !listReady || restoredRef.current) return;
    const saved = readSavedCardsState();
    if (!saved) {
      restoredRef.current = true;
      return;
    }
    if (saved.scrollY === null) {
      clearSavedCardsState();
      restoredRef.current = true;
      return;
    }

    const y = saved.scrollY;
    const restore = () => window.scrollTo(0, y);

    requestAnimationFrame(() => {
      requestAnimationFrame(restore);
    });
    const t = window.setTimeout(() => {
      restore();
      clearSavedCardsState();
      restoredRef.current = true;
    }, 100);

    return () => window.clearTimeout(t);
  }, [loading, listReady]);
}

/** 확장팩 상세 — 카드 클릭 직전 스크롤 저장 */
export function scrollRestoreKey(pathname: string): string {
  return `${SET_DETAIL_PREFIX}${pathname}`;
}

export function saveScrollPosition(pathname?: string): void {
  if (typeof window === "undefined") return;
  const path = pathname ?? window.location.pathname;
  sessionStorage.setItem(scrollRestoreKey(path), String(window.scrollY));
}

export function readScrollPosition(pathname: string): number | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(scrollRestoreKey(pathname));
  if (raw == null) return null;
  const y = parseInt(raw, 10);
  return Number.isFinite(y) ? y : null;
}

export function clearScrollPosition(pathname: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(scrollRestoreKey(pathname));
}
