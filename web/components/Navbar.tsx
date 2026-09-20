'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, Search, Sun, Moon, X } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { SearchBox } from './search-box';
import { PokeballIcon } from './pokeball-icon';

const NAV_ITEMS = [
  { to: '/', label: '홈' },
  { to: '/cards', label: '모든 카드' },
  { to: '/sets', label: '세트 시세' },
  { to: '/community', label: '커뮤니티' },
] as const;

const NavLink = ({ to, children, onClick }: { to: string; children: React.ReactNode; onClick?: () => void }) => {
  const pathname = usePathname();
  const isActive = pathname === to || (to !== '/' && pathname.startsWith(to));
  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    onClick?.();
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    const target = new URL(to, window.location.origin);
    if (
      target.pathname === window.location.pathname &&
      target.search === window.location.search &&
      target.hash === window.location.hash
    ) {
      window.location.reload();
    } else {
      window.location.assign(target.href);
    }
  };

  return (
    <a
      href={to}
      onClick={handleClick}
      className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
        isActive
          ? 'bg-amber-500 text-white dark:text-slate-900 shadow-[0_0_15px_rgba(245,158,11,0.3)]'
          : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
      }`}
    >
      {children}
    </a>
  );
};

export function Navbar() {
  const { theme, toggle } = useTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0B132B]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 h-16 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <Link href="/" className="flex items-center gap-2 group shrink-0 justify-self-start">
          <PokeballIcon size="lg" className="group-hover:rotate-180 transition-transform duration-500" />
          <span className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight hidden sm:inline">
            Poké<span className="text-amber-500">Price</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-2 justify-self-center">
          {NAV_ITEMS.map(item => (
            <NavLink key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2 justify-self-end">
          {searchOpen ? (
            <div className="flex items-center gap-2 w-48 sm:w-64 md:w-72">
              <SearchBox
                className="flex-1 min-w-0"
                autoFocus
                onClose={() => setSearchOpen(false)}
              />
              <button
                type="button"
                onClick={() => setSearchOpen(false)}
                className="p-2 text-slate-500 hover:text-slate-900 dark:hover:text-white shrink-0"
                aria-label="검색 닫기"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
              aria-label="검색"
            >
              <Search className="w-5 h-5" />
            </button>
          )}
          <button
            type="button"
            onClick={() => setMenuOpen(v => !v)}
            className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors md:hidden"
            aria-label="메뉴"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <button
            onClick={toggle}
            className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors bg-slate-100 dark:bg-slate-800 rounded-full shrink-0"
            title="테마 전환"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-indigo-500" />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav className="md:hidden border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0B132B]/95 px-4 py-3 flex flex-col gap-1">
          {NAV_ITEMS.map(item => (
            <NavLink key={item.to} to={item.to} onClick={() => setMenuOpen(false)}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}
