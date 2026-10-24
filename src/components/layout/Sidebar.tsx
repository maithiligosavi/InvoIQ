import { FileText, LayoutDashboard, UploadCloud, X } from 'lucide-react';

export type View = 'dashboard' | 'invoices' | 'upload';

interface SidebarProps {
  active: View;
  onNavigate: (view: View) => void;
  mobileOpen: boolean;
  onClose: () => void;
}

const navItems: { id: View; label: string; icon: typeof FileText }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'upload', label: 'Upload Center', icon: UploadCloud },
];

export default function Sidebar({ active, onNavigate, mobileOpen, onClose }: SidebarProps) {
  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-40 h-full w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
      >
        <div className="flex items-center justify-between h-16 px-5 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-brand-600 text-white">
              <FileText size={20} strokeWidth={2.2} />
            </div>
            <div>
              <h1 className="text-[15px] font-bold text-slate-900 leading-none">InvoIQ</h1>
              <p className="text-[10px] text-slate-400 mt-0.5">Invoice Intelligence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-slate-400 hover:text-slate-600"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 px-3 py-5 space-y-1">
          <p className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Menu
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onNavigate(item.id);
                  onClose();
                }}
                className={`group flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
              >
                <Icon
                  size={19}
                  strokeWidth={isActive ? 2.4 : 2}
                  className={isActive ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600'}
                />
                {item.label}
                {isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-600" />
                )}
              </button>
            );
          })}
        </nav>


      </aside>
    </>
  );
}
