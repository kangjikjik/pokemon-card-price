'use client';

import { useEffect, useState } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export const ScrollFab = () => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 200);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const scrollTo = (top: number) => {
    window.scrollTo({ top, behavior: 'smooth' });
  };

  return (
    <div
      className={cn(
        'fixed bottom-6 right-6 z-50 flex flex-col gap-2 transition-all duration-300',
        visible ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-4 pointer-events-none',
      )}
      aria-hidden={!visible}
    >
      <button
        type="button"
        onClick={() => scrollTo(0)}
        className="w-11 h-11 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg flex items-center justify-center text-slate-700 dark:text-slate-200 hover:bg-amber-50 dark:hover:bg-slate-700 hover:border-amber-400 transition-colors"
        aria-label="맨 위로"
      >
        <ArrowUp className="w-5 h-5" />
      </button>
      <button
        type="button"
        onClick={() => scrollTo(document.documentElement.scrollHeight)}
        className="w-11 h-11 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg flex items-center justify-center text-slate-700 dark:text-slate-200 hover:bg-amber-50 dark:hover:bg-slate-700 hover:border-amber-400 transition-colors"
        aria-label="맨 아래로"
      >
        <ArrowDown className="w-5 h-5" />
      </button>
    </div>
  );
};
