'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import { Search, Loader2, Package, CreditCard } from 'lucide-react';
import { cn } from '@/lib/utils';

type SuggestCard = { id: string; name: string; rarity: string; set: string };
type SuggestSet = { id: string; name: string; code: string };

type SuggestItem =
  | { kind: 'set'; id: string; label: string; sub: string; href: string }
  | { kind: 'card'; id: string; label: string; sub: string; href: string }
  | { kind: 'search'; id: string; label: string; sub: string; href: string };

type Props = {
  className?: string;
  inputClassName?: string;
  placeholder?: string;
  autoFocus?: boolean;
  onClose?: () => void;
};

export function SearchBox({
  className,
  inputClassName,
  placeholder = '카드 이름 또는 세트명 검색...',
  autoFocus,
  onClose,
}: Props) {
  const router = useRouter();
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [cards, setCards] = useState<SuggestCard[]>([]);
  const [sets, setSets] = useState<SuggestSet[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [dropdownRect, setDropdownRect] = useState({ top: 0, left: 0, width: 0 });

  const close = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
    onClose?.();
  }, [onClose]);

  const updateRect = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setDropdownRect({
      top: rect.bottom + 8,
      left: rect.left,
      width: rect.width,
    });
  }, []);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim()) {
      setCards([]);
      setSets([]);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/search/suggest?q=${encodeURIComponent(q)}&limit=8`);
      const json = await res.json();
      setCards(json.cards || []);
      setSets(json.sets || []);
    } catch {
      setCards([]);
      setSets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const items: SuggestItem[] = useMemo(() => {
    const result: SuggestItem[] = [];
    for (const set of sets) {
      result.push({
        kind: 'set',
        id: `set-${set.id}`,
        label: set.name,
        sub: set.code,
        href: `/sets/${set.id}`,
      });
    }
    for (const card of cards) {
      result.push({
        kind: 'card',
        id: `card-${card.id}`,
        label: card.name,
        sub: `${card.set} · ${card.rarity}`,
        href: `/cards/${card.id}`,
      });
    }
    if (query.trim()) {
      result.push({
        kind: 'search',
        id: 'search-all',
        label: `「${query}」 전체 검색 결과 보기`,
        sub: '',
        href: `/cards?q=${encodeURIComponent(query.trim())}`,
      });
    }
    return result;
  }, [sets, cards, query]);

  const goToItem = useCallback((item: SuggestItem) => {
    close();
    router.push(item.href);
  }, [close, router]);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const t = setTimeout(() => fetchSuggestions(query), 200);
    return () => clearTimeout(t);
  }, [query, fetchSuggestions]);

  useEffect(() => {
    setActiveIndex(-1);
  }, [query, sets, cards]);

  const showDropdown = open && query.trim().length > 0;
  const hasResults = cards.length > 0 || sets.length > 0;

  useEffect(() => {
    if (!showDropdown) return;
    updateRect();
    const onScroll = () => updateRect();
    const onResize = () => updateRect();
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onResize);
    };
  }, [showDropdown, updateRect]);

  useEffect(() => {
    if (!showDropdown) return;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [showDropdown]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (wrapRef.current?.contains(target)) return;
      if (listRef.current?.contains(target)) return;
      close();
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [close]);

  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-index="${activeIndex}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
      return;
    }
    if (!showDropdown || items.length === 0) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const trimmed = query.trim();
        if (trimmed) router.push(`/cards?q=${encodeURIComponent(trimmed)}`);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => (i + 1) % items.length);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => (i <= 0 ? items.length - 1 : i - 1));
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && items[activeIndex]) {
        goToItem(items[activeIndex]);
      } else {
        const trimmed = query.trim();
        if (trimmed) router.push(`/cards?q=${encodeURIComponent(trimmed)}`);
      }
    }
  };

  const firstSetIdx = items.findIndex(i => i.kind === 'set');
  const firstCardIdx = items.findIndex(i => i.kind === 'card');

  const dropdown = showDropdown && mounted ? createPortal(
    <>
      <div
        className="fixed inset-0 z-[9998] bg-black/20 dark:bg-black/40"
        aria-hidden
        onMouseDown={e => {
          e.preventDefault();
          close();
        }}
      />
      <div
        ref={listRef}
        id="search-suggest-list"
        className="fixed z-[9999] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl max-h-[min(70vh,24rem)] overflow-y-auto overscroll-contain"
        style={{ top: dropdownRect.top, left: dropdownRect.left, width: dropdownRect.width }}
        role="listbox"
      >
        {!loading && !hasResults && (
          <p className="px-4 py-3 text-sm text-slate-500">검색 결과가 없습니다.</p>
        )}

        {items.map((item, idx) => {
          const active = idx === activeIndex;
          const header =
            idx === firstSetIdx ? (
              <p className="px-4 pt-3 pb-1 text-xs font-semibold text-slate-400 uppercase tracking-wide">확장팩</p>
            ) : idx === firstCardIdx ? (
              <p className="px-4 pt-3 pb-1 text-xs font-semibold text-slate-400 uppercase tracking-wide">카드</p>
            ) : null;

          const Icon = item.kind === 'set' ? Package : item.kind === 'card' ? CreditCard : null;
          const iconClass = item.kind === 'set' ? 'text-amber-500' : item.kind === 'card' ? 'text-blue-500' : '';

          return (
            <div key={item.id}>
              {header}
              <button
                type="button"
                data-index={idx}
                role="option"
                aria-selected={active}
                onMouseEnter={() => setActiveIndex(idx)}
                onClick={() => goToItem(item)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                  item.kind === 'search' && 'border-t border-slate-100 dark:border-slate-800 text-amber-600 dark:text-amber-400 font-medium',
                  active ? 'bg-amber-50 dark:bg-amber-950/40' : 'hover:bg-slate-50 dark:hover:bg-slate-800',
                )}
              >
                {Icon && <Icon className={cn('w-4 h-4 shrink-0', iconClass)} />}
                <div className={cn('min-w-0', item.kind === 'search' ? 'flex-1' : 'flex-1')}>
                  <p className={cn('text-sm', item.kind === 'search' ? '' : 'font-medium text-slate-900 dark:text-white')}>
                    {item.label}
                  </p>
                  {item.sub && <p className="text-xs text-slate-500">{item.sub}</p>}
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </>,
    document.body,
  ) : null;

  return (
    <div ref={wrapRef} className={cn('relative w-full', className)}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          ref={inputRef}
          type="search"
          value={query}
          autoFocus={autoFocus}
          onChange={e => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          role="combobox"
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls="search-suggest-list"
          className={cn(
            'w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder:text-slate-400 rounded-full py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent',
            inputClassName,
          )}
        />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 animate-spin" />
        )}
      </div>
      {dropdown}
    </div>
  );
}
