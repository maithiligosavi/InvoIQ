import { FileText, LayoutDashboard, UploadCloud, X, LogOut, User } from 'lucide-react';

export type View = 'dashboard' | 'invoices' | 'upload';

interface SidebarProps {
  active: View;
  onNavigate: (view: View) => void;
  mobileOpen: boolean;
  onClose: () => void;
  username?: string | null;
  onLogout?: () => void;
  onOpenAuth?: () => void;
}

const navItems: { id: View; label: string; icon: typeof FileText }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'upload', label: 'Upload Center', icon: UploadCloud },
];

export default function Sidebar({
  active,
  onNavigate,
  mobileOpen,
  onClose,
  username,
  onLogout,
  onOpenAuth,
}: SidebarProps) {
  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-40 h-full w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between h-16 px-5 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg shadow-sm"
              style={{ backgroundColor: '#E2B4BD', color: '#4A4A4A' }}
            >
              <FileText size={20} strokeWidth={2.4} />
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
                className={`group flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
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

        {/* User Status / Auth Section in Footer */}
        <div className="p-3 border-t border-slate-200 shrink-0">
          {username ? (
            <div
              className="flex items-center justify-between p-2.5 rounded-xl border border-[#E2B4BD]/40 shadow-sm"
              style={{ backgroundColor: '#FFF5F5' }}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 shadow-inner"
                  style={{ backgroundColor: '#F7D6D0', color: '#4A4A4A' }}
                >
                  {username.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold truncate" style={{ color: '#4A4A4A' }}>
                    {username}
                  </p>
                  <p className="text-[10px] text-emerald-600 font-medium">Authenticated</p>
                </div>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign out"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-[#F7D6D0]/50 transition-colors"
                  aria-label="Sign out"
                >
                  <LogOut size={16} />
                </button>
              )}
            </div>
          ) : (
            onOpenAuth && (
              <button
                onClick={onOpenAuth}
                className="w-full py-2.5 px-3 rounded-xl text-xs font-bold shadow-sm transition-all flex items-center justify-center gap-2 hover:brightness-95"
                style={{ backgroundColor: '#E2B4BD', color: '#4A4A4A' }}
              >
                <User size={15} />
                <span>Sign In to InvoIQ</span>
              </button>
            )
          )}
        </div>
      </aside>
    </>
  );
}
