import { KadoriMark } from './kadori-mark';

export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-12 mt-auto transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 opacity-70">
          <KadoriMark size="sm" />
          <span className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">카도리</span>
        </div>
        <div className="text-slate-500 text-sm text-center md:text-right">
          <p>카도리는 Nintendo·The Pokémon Company와 제휴·승인 관계가 없는 비공식 정보 서비스입니다.</p>
          <p>Pokémon and its trademarks are ©Nintendo, Creatures, and GAMEFREAK.</p>
          <p className="mt-1">시세 정보는 참고용이며 실제 거래가와 다를 수 있습니다.</p>
        </div>
      </div>
    </footer>
  );
}
