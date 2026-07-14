'use client';

import { useLayoutEffect } from 'react';
import { usePathname } from 'next/navigation';
import { clearScrollPosition, readScrollPosition } from '@/lib/scroll-restore';

function restoreScrollTo(pathname: string): (() => void) | undefined {
  const y = readScrollPosition(pathname);
  if (y == null) return;

  const scroll = () => window.scrollTo(0, y);
  scroll();

  const raf = requestAnimationFrame(() => {
    scroll();
    requestAnimationFrame(scroll);
  });
  const timers = [50, 150].map((ms) => setTimeout(scroll, ms));
  const finalTimer = setTimeout(() => {
    scroll();
    clearScrollPosition(pathname);
  }, 300);

  return () => {
    cancelAnimationFrame(raf);
    timers.forEach(clearTimeout);
    clearTimeout(finalTimer);
  };
}

/** 뒤로가기 시 이전 스크롤 위치 복원 */
export function ScrollRestore() {
  const pathname = usePathname();

  useLayoutEffect(() => {
    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }
  }, []);

  useLayoutEffect(() => {
    let cleanup = restoreScrollTo(pathname);

    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return;
      cleanup?.();
      cleanup = restoreScrollTo(pathname);
    };

    window.addEventListener('pageshow', onPageShow);
    return () => {
      cleanup?.();
      window.removeEventListener('pageshow', onPageShow);
    };
  }, [pathname]);

  return null;
}
