import { Menu, Search } from 'lucide-react';

interface HeaderProps {
  title: string;
  onMenuClick: () => void;
  search: string;
  onSearch: (value: string) => void;
  showSearch?: boolean;
}

export default function Header({ title, onMenuClick, search, onSearch, showSearch = true }: HeaderProps) {
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
        <div className="hidden md:flex relative w-64 lg:w-80">
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
    </header>
  );
}
