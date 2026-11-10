import { Menu, Search, User, LogOut, LogIn } from 'lucide-react';

interface HeaderProps {
  title: string;
  onMenuClick: () => void;
  search: string;
  onSearch: (value: string) => void;
  showSearch?: boolean;
  username?: string | null;
  onLogout?: () => void;
  onOpenAuth?: () => void;
}

export default function Header({
  title,
  onMenuClick,
  search,
  onSearch,
  showSearch = true,
  username,
  onLogout,
  onOpenAuth,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 h-16 px-4 sm:px-6 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <button
        onClick={onMenuClick}
        className="lg:hidden text-slate-500 hover:text-slate-700"
        aria-label="Open menu"
      >
        <Menu size={22} />
      </button>

      <div className="flex-1 min-w-0">
        <h2 className="text-base sm:text-lg font-bold text-slate-900 truncate">{title}</h2>
      </div>

      {showSearch && (
        <div className="hidden md:flex relative w-64 lg:w-72">
          <Search
            size={17}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search invoices, vendors..."
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-100 border border-transparent focus:bg-white focus:border-brand-300 focus:ring-2 focus:ring-brand-100 outline-none transition-all placeholder:text-slate-400"
          />
        </div>
      )}

      {/* User Auth controls */}
      <div className="flex items-center gap-2 pl-2">
        {username ? (
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200/80 rounded-full py-1 px-2.5">
            <div className="w-7 h-7 rounded-full bg-[#E2B4BD] text-[#4A4A4A] flex items-center justify-center font-bold text-xs shadow-inner">
              {username.charAt(0).toUpperCase()}
            </div>
            <span className="text-xs font-semibold text-slate-700 hidden sm:inline max-w-[120px] truncate">
              {username}
            </span>
            {onLogout && (
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-1 rounded-full text-slate-400 hover:text-rose-600 hover:bg-slate-100 transition-colors ml-0.5"
                aria-label="Sign out"
              >
                <LogOut size={15} />
              </button>
            )}
          </div>
        ) : (
          onOpenAuth && (
            <button
              onClick={onOpenAuth}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm hover:brightness-95"
              style={{ backgroundColor: '#E2B4BD', color: '#4A4A4A' }}
            >
              <LogIn size={14} />
              <span>Sign In</span>
            </button>
          )
        )}
      </div>
    </header>
  );
}
