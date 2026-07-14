import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home } from './components/Home';
import { CardList } from './components/CardList';
import { CardDetail } from './components/CardDetail';
import { SetList } from './components/SetList';
import { SetDetail } from './components/SetDetail';
import { Search, Sun, Moon } from 'lucide-react';

const NavLink = ({ to, children }: { to: string, children: React.ReactNode }) => {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  
  return (
    <Link 
      to={to} 
      className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
        isActive 
          ? 'bg-amber-500 text-white dark:text-slate-900 shadow-[0_0_15px_rgba(245,158,11,0.3)]' 
          : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
      }`}
    >
      {children}
    </Link>
  );
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  const [isDarkMode, setIsDarkMode] = useState(true); // Default to dark mode

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0B132B] text-slate-900 dark:text-slate-200 font-sans selection:bg-amber-500 selection:text-slate-900 flex flex-col transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0B132B]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-colors duration-300">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-red-500 to-red-600 border-2 border-white dark:border-slate-900 flex items-center justify-center relative overflow-hidden shadow-[0_0_10px_rgba(239,68,68,0.5)] group-hover:rotate-180 transition-transform duration-500">
              <div className="absolute top-1/2 left-0 w-full h-[2px] bg-white dark:bg-slate-900 -translate-y-1/2"></div>
              <div className="absolute top-1/2 left-1/2 w-3 h-3 bg-slate-900 dark:bg-white rounded-full border-[2px] border-white dark:border-slate-900 -translate-x-1/2 -translate-y-1/2 z-10"></div>
              <div className="w-full h-1/2 bg-slate-900 dark:bg-white absolute bottom-0"></div>
            </div>
            <span className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Poké<span className="text-amber-500">Price</span>
            </span>
          </Link>
          
          <nav className="hidden md:flex items-center gap-2">
            <NavLink to="/">홈</NavLink>
            <NavLink to="/cards">모든 카드</NavLink>
            <NavLink to="/sets">확장팩 시세</NavLink>
          </nav>

          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors">
              <Search className="w-5 h-5" />
            </button>
            <button 
              onClick={() => setIsDarkMode(!isDarkMode)} 
              className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors bg-slate-100 dark:bg-slate-800 rounded-full"
              title="블랙/화이트 테마 전환"
            >
              {isDarkMode ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-indigo-500" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-12 mt-auto transition-colors duration-300">
        <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 opacity-50">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-red-500 to-red-600 border border-slate-200 dark:border-slate-900 flex items-center justify-center relative overflow-hidden grayscale">
              <div className="absolute top-1/2 left-0 w-full h-[1px] bg-slate-200 dark:bg-slate-900 -translate-y-1/2"></div>
              <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-slate-900 dark:bg-white rounded-full border border-slate-200 dark:border-slate-900 -translate-x-1/2 -translate-y-1/2 z-10"></div>
              <div className="w-full h-1/2 bg-slate-900 dark:bg-white absolute bottom-0"></div>
            </div>
            <span className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
              PokéPrice
            </span>
          </div>
          <div className="text-slate-500 text-sm text-center md:text-right">
            <p>Pokémon and its trademarks are ©Nintendo, Creatures, and GAMEFREAK.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/cards" element={<CardList />} />
          <Route path="/cards/:id" element={<CardDetail />} />
          <Route path="/sets" element={<SetList />} />
          <Route path="/sets/:id" element={<SetDetail />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
