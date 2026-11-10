import { useCallback, useEffect, useState } from 'react';
import Sidebar, { type View } from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import Dashboard from '@/components/dashboard/Dashboard';
import InvoicesTable from '@/components/invoices/InvoicesTable';
import UploadCenter from '@/components/upload/UploadCenter';
import AuthModal from '@/components/auth/AuthModal';
import {
  deleteInvoice,
  fetchInvoices,
  getStoredToken,
  getStoredUsername,
  clearAuthSession,
} from '@/services/api';
import type { Invoice } from '@/types';

const viewTitles: Record<View, string> = {
  dashboard: 'Dashboard Overview',
  invoices: 'Invoices',
  upload: 'Upload Center',
};

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Authentication state
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [username, setUsername] = useState<string | null>(() => getStoredUsername());
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(() => !getStoredToken());

  const loadInvoices = useCallback(async () => {
    const activeToken = getStoredToken();
    if (!activeToken) {
      setLoading(false);
      setAuthModalOpen(true);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await fetchInvoices();
      setInvoices(data);
    } catch (err: any) {
      console.error('Failed to load initial invoices from backend:', err);
      if (err?.response?.status === 401) {
        setAuthModalOpen(true);
      } else {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            'Failed to connect to FastAPI backend at http://localhost:8000. Please ensure the backend is running.'
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      loadInvoices();
    } else {
      setAuthModalOpen(true);
    }
  }, [token, loadInvoices]);

  // Handle automatic 401 logout & storage sync
  useEffect(() => {
    const handleUnauthorized = () => {
      setToken(null);
      setUsername(null);
      setInvoices([]);
      setAuthModalOpen(true);
    };

    const handleAuthChanged = () => {
      setToken(getStoredToken());
      setUsername(getStoredUsername());
    };

    window.addEventListener('invoiq:unauthorized', handleUnauthorized);
    window.addEventListener('invoiq:auth_changed', handleAuthChanged);

    return () => {
      window.removeEventListener('invoiq:unauthorized', handleUnauthorized);
      window.removeEventListener('invoiq:auth_changed', handleAuthChanged);
    };
  }, []);

  const handleAuthSuccess = ({ username: loggedUser, token: newToken }: { username: string; token: string }) => {
    setToken(newToken);
    setUsername(loggedUser);
    setAuthModalOpen(false);
    loadInvoices();
  };

  const handleLogout = () => {
    clearAuthSession();
    setToken(null);
    setUsername(null);
    setInvoices([]);
    setAuthModalOpen(true);
  };

  const handleInvoiceUploaded = (newInvoice: Invoice) => {
    setInvoices((prev) => {
      // Prevent duplicates if already present
      const filtered = prev.filter(
        (inv) => inv.id !== newInvoice.id && inv.invoiceId !== newInvoice.invoiceId
      );
      return [newInvoice, ...filtered];
    });
  };

  const handleDeleteInvoice = async (invoiceId: string) => {
    await deleteInvoice(invoiceId);
    setInvoices((prev) =>
      prev.filter((inv) => inv.id !== invoiceId && inv.invoiceId !== invoiceId)
    );
  };

  const handleNavigate = (next: View) => {
    setView(next);
    setSearch('');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Sidebar
        active={view}
        onNavigate={handleNavigate}
        mobileOpen={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        username={username}
        onLogout={handleLogout}
        onOpenAuth={() => setAuthModalOpen(true)}
      />

      <div className="lg:pl-64">
        <Header
          title={viewTitles[view]}
          onMenuClick={() => setMobileNavOpen(true)}
          search={search}
          onSearch={setSearch}
          showSearch={view !== 'upload'}
          username={username}
          onLogout={handleLogout}
          onOpenAuth={() => setAuthModalOpen(true)}
        />

        <main className="p-4 sm:p-6 max-w-7xl mx-auto">
          <div key={view} className="animate-fade-in">
            {view === 'dashboard' && (
              <Dashboard
                invoices={invoices}
                loading={loading}
                error={error}
                onRetry={loadInvoices}
                search={search}
              />
            )}
            {view === 'invoices' && (
              <InvoicesTable
                search={search}
                invoices={invoices}
                onInvoicesChange={setInvoices}
                onDeleteInvoice={handleDeleteInvoice}
                loading={loading}
                error={error}
                onRetry={loadInvoices}
              />
            )}
            {view === 'upload' && (
              <UploadCenter onInvoiceUploaded={handleInvoiceUploaded} />
            )}
          </div>
        </main>
      </div>

      {/* Modern InvoIQ Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={token ? () => setAuthModalOpen(false) : undefined}
        onSuccess={handleAuthSuccess}
      />
    </div>
  );
}
