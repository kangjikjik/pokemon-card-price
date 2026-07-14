export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-12 mt-auto transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 opacity-50">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-red-500 to-red-600 border border-slate-200 dark:border-slate-900 flex items-center justify-center relative overflow-hidden grayscale">
            <div className="absolute top-1/2 left-0 w-full h-[1px] bg-slate-200 dark:bg-slate-900 -translate-y-1/2" />
            <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-slate-900 dark:bg-white rounded-full border border-slate-200 dark:border-slate-900 -translate-x-1/2 -translate-y-1/2 z-10" />
            <div className="w-full h-1/2 bg-slate-900 dark:bg-white absolute bottom-0" />
          </div>
          <span className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">PokéPrice</span>
        </div>
        <div className="text-slate-500 text-sm text-center md:text-right">
          <p>Pokémon and its trademarks are ©Nintendo, Creatures, and GAMEFREAK.</p>
          <p className="mt-1">시세 정보는 참고용이며 실제 거래가와 다를 수 있습니다.</p>
        </div>
      </div>
    </footer>
  );
}
