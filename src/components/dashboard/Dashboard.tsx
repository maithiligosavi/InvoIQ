import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { fetchInvoices, fetchAnalytics } from '@/services/api';
import type { Analytics, Invoice } from '@/types';
import MetricCards from './MetricCards';
import Charts from './Charts';

interface DashboardProps {
  invoices?: Invoice[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  search?: string;
}

export default function Dashboard({
  invoices: externalInvoices,
  loading: externalLoading,
  error: externalError,
  onRetry: externalRetry,
  search = '',
}: DashboardProps = {}) {
  const [internalInvoices, setInternalInvoices] = useState<Invoice[]>([]);
  const [internalLoading, setInternalLoading] = useState(externalInvoices === undefined);
  const [internalError, setInternalError] = useState<string | null>(null);
  const [apiAnalytics, setApiAnalytics] = useState<Analytics | null>(null);

  // If external invoices are not provided, fetch live invoices directly
  const loadDashboardData = async () => {
    setInternalLoading(true);
    setInternalError(null);
    try {
      const [fetchedInvoices, fetchedAnalytics] = await Promise.allSettled([
        fetchInvoices(),
        fetchAnalytics(),
      ]);

      if (fetchedInvoices.status === 'fulfilled') {
        setInternalInvoices(fetchedInvoices.value);
      } else {
        throw fetchedInvoices.reason;
      }

      if (fetchedAnalytics.status === 'fulfilled') {
        setApiAnalytics(fetchedAnalytics.value);
      }
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setInternalError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to load invoices from backend server.'
      );
    } finally {
      setInternalLoading(false);
    }
  };

  useEffect(() => {
    if (externalInvoices !== undefined) {
      return;
    }
    loadDashboardData();
  }, [externalInvoices]);

  const invoices = externalInvoices !== undefined ? externalInvoices : internalInvoices;
  const isLoading = externalLoading !== undefined ? externalLoading : internalLoading;
  const errorMsg = externalError !== undefined ? externalError : internalError;
  const handleRetry = externalRetry || loadDashboardData;

  // Filter invoices by search query
  const filteredInvoices = useMemo(() => {
    if (!search.trim()) return invoices;
    const q = search.toLowerCase();
    return invoices.filter(
      (inv) =>
        inv.invoiceId?.toLowerCase().includes(q) ||
        inv.vendor?.toLowerCase().includes(q) ||
        inv.status?.toLowerCase().includes(q) ||
        inv.date?.toLowerCase().includes(q)
    );
  }, [invoices, search]);

  // Compute live analytics whenever filteredInvoices changes
  const liveData: Analytics = useMemo(() => {
    const processed = filteredInvoices.filter((i) => i.status === 'Processed');
    const totalSpent = processed.reduce((sum, i) => sum + (Number(i.amount) || 0), 0);
    const activeVendors = new Set(filteredInvoices.map((i) => i.vendor).filter(Boolean)).size;
    const averageInvoiceValue = processed.length > 0 ? Math.round(totalSpent / processed.length) : 0;

    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlyMap: Record<string, number> = {};
    monthNames.forEach((m) => {
      monthlyMap[m] = 0;
    });

    processed.forEach((inv) => {
      const d = new Date(inv.date);
      if (!isNaN(d.getTime())) {
        const m = monthNames[d.getMonth()];
        monthlyMap[m] = (monthlyMap[m] || 0) + (Number(inv.amount) || 0);
      }
    });

    const monthlySpend = monthNames.map((month) => ({
      month,
      spend: monthlyMap[month] || 0,
    }));

    const vendorMap: Record<string, number> = {};
    processed.forEach((inv) => {
      const v = inv.vendor || 'Unknown';
      vendorMap[v] = (vendorMap[v] || 0) + (Number(inv.amount) || 0);
    });

    const vendorSpend = Object.entries(vendorMap)
      .map(([vendor, spend]) => ({ vendor, spend }))
      .sort((a, b) => b.spend - a.spend)
      .slice(0, 5);

    return {
      metrics: {
        totalSpent,
        invoicesProcessed: filteredInvoices.length,
        activeVendors,
        averageInvoiceValue,
      },
      monthlySpend,
      vendorSpend,
    };
  }, [filteredInvoices]);

  if (isLoading && filteredInvoices.length === 0 && !search) {
    return (
      <div className="flex flex-col items-center justify-center h-72 bg-white rounded-xl border border-slate-200 shadow-soft text-slate-400">
        <Loader2 size={36} className="animate-spin text-brand-600 mb-3" />
        <p className="text-sm font-medium text-slate-700">Loading live invoice data...</p>
        <p className="text-xs text-slate-400 mt-1">Fetching from FastAPI backend at localhost:8000</p>
      </div>
    );
  }

  if (errorMsg && filteredInvoices.length === 0 && !search) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-xl border border-slate-200 shadow-soft text-center">
        <AlertCircle size={36} className="text-amber-500 mb-3" />
        <p className="text-base font-semibold text-slate-800">Unable to load invoices from backend</p>
        <p className="text-xs text-slate-500 max-w-md mt-1 mb-4">
          {errorMsg}
        </p>
        <button
          onClick={handleRetry}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors shadow-sm"
        >
          <RefreshCw size={15} />
          Retry Connection
        </button>
      </div>
    );
  }

  const data = liveData || apiAnalytics;

  return (
    <div className="space-y-4">
      {errorMsg && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-amber-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={handleRetry}
            className="font-medium underline hover:text-amber-900"
          >
            Retry
          </button>
        </div>
      )}
      <MetricCards metrics={data.metrics} />
      <Charts analytics={data} />
    </div>
  );
}
