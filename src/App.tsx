import { useCallback, useEffect, useState } from 'react';
import Sidebar, { type View } from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import Dashboard from '@/components/dashboard/Dashboard';
import InvoicesTable from '@/components/invoices/InvoicesTable';
import UploadCenter from '@/components/upload/UploadCenter';
import { deleteInvoice, fetchInvoices } from '@/services/api';
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInvoices();
      setInvoices(data);
    } catch (err: any) {
      console.error('Failed to load initial invoices from backend:', err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to connect to FastAPI backend at http://localhost:8000. Please ensure the backend is running.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

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
      />

      <div className="lg:pl-64">
        <Header
          title={viewTitles[view]}
          onMenuClick={() => setMobileNavOpen(true)}
          search={search}
          onSearch={setSearch}
          showSearch={view !== 'upload'}
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
    </div>
  );
}
