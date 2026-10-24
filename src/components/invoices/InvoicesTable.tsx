import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { deleteInvoice, fetchInvoices } from '@/services/api';
import { formatDate, formatINR } from '@/utils/format';
import type { Invoice, InvoiceStatus } from '@/types';

const statusStyles: Record<InvoiceStatus, string> = {
  Processed: 'bg-emerald-50 text-emerald-700',
  Pending: 'bg-amber-50 text-amber-700',
  Failed: 'bg-red-50 text-red-600',
};

const statusDot: Record<InvoiceStatus, string> = {
  Processed: 'bg-emerald-500',
  Pending: 'bg-amber-500',
  Failed: 'bg-red-500',
};

const PAGE_SIZE = 8;

interface InvoicesTableProps {
  search: string;
  invoices?: Invoice[];
  onInvoicesChange?: React.Dispatch<React.SetStateAction<Invoice[]>>;
  onDeleteInvoice?: (id: string) => Promise<void>;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export default function InvoicesTable({
  search,
  invoices: externalInvoices,
  onInvoicesChange,
  onDeleteInvoice,
  loading: externalLoading,
  error: externalError,
  onRetry: externalRetry,
}: InvoicesTableProps) {
  const [internalInvoices, setInternalInvoices] = useState<Invoice[]>([]);
  const [internalLoading, setInternalLoading] = useState(externalInvoices === undefined);
  const [internalError, setInternalError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadInvoices = async () => {
    setInternalLoading(true);
    setInternalError(null);
    try {
      const data = await fetchInvoices();
      setInternalInvoices(data);
    } catch (err: any) {
      console.error('Failed to fetch invoices in InvoicesTable:', err);
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
    loadInvoices();
  }, [externalInvoices]);

  const invoices = externalInvoices !== undefined ? externalInvoices : internalInvoices;
  const setInvoices = onInvoicesChange || setInternalInvoices;
  const isLoading = externalLoading !== undefined ? externalLoading : internalLoading;
  const errorMsg = externalError !== undefined ? externalError : internalError;
  const handleRetry = externalRetry || loadInvoices;

  const categories = useMemo(
    () => Array.from(new Set(invoices.map((i) => i.category))).sort(),
    [invoices]
  );

  const filtered = useMemo(() => {
    return invoices.filter((inv) => {
      const q = search.toLowerCase().trim();
      const matchesSearch =
        !q ||
        inv.vendor.toLowerCase().includes(q) ||
        inv.invoiceId.toLowerCase().includes(q);
      const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
      const matchesCategory = categoryFilter === 'all' || inv.category === categoryFilter;
      return matchesSearch && matchesStatus && matchesCategory;
    });
  }, [invoices, search, statusFilter, categoryFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageData = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id);
      setDeleteError(null);

      if (onDeleteInvoice) {
        await onDeleteInvoice(id);
      } else {
        await deleteInvoice(id);
        setInvoices((prev) => prev.filter((i) => i.id !== id && i.invoiceId !== id));
      }

      if (selected?.id === id || selected?.invoiceId === id) {
        setSelected(null);
      }
    } catch (err: any) {
      console.error('Failed to delete invoice:', err);
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to delete invoice from server.';
      setDeleteError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  if (isLoading && invoices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-72 bg-white rounded-xl border border-slate-200 shadow-soft text-slate-400">
        <Loader2 size={36} className="animate-spin text-brand-600 mb-3" />
        <p className="text-sm font-medium text-slate-700">Loading invoices from backend...</p>
        <p className="text-xs text-slate-400 mt-1">Connecting to FastAPI on port 8000</p>
      </div>
    );
  }

  if (errorMsg && invoices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-white rounded-xl border border-slate-200 shadow-soft text-center">
        <AlertCircle size={36} className="text-amber-500 mb-3" />
        <p className="text-base font-semibold text-slate-800">Unable to load invoices</p>
        <p className="text-xs text-slate-500 max-w-md mt-1 mb-4">{errorMsg}</p>
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

  return (
    <div className="space-y-4">
      {deleteError && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle size={18} className="text-red-500 shrink-0" />
            <span>{deleteError}</span>
          </div>
          <button
            onClick={() => setDeleteError(null)}
            className="text-red-400 hover:text-red-600 p-1"
            aria-label="Dismiss error"
          >
            <X size={16} />
          </button>
        </div>
      )}

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

      <div className="bg-white rounded-xl border border-slate-200 shadow-soft p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 sm:hidden">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              readOnly
              placeholder="Use header search..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-slate-100 border border-transparent outline-none placeholder:text-slate-400"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as InvoiceStatus | 'all');
              setPage(1);
            }}
            className="px-3 py-2 text-sm rounded-lg bg-slate-100 border border-transparent focus:bg-white focus:border-brand-300 outline-none cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="Processed">Processed</option>
            <option value="Pending">Pending</option>
            <option value="Failed">Failed</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-sm rounded-lg bg-slate-100 border border-transparent focus:bg-white focus:border-brand-300 outline-none cursor-pointer"
          >
            <option value="all">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <div className="sm:ml-auto flex items-center text-xs text-slate-500">
            <span>Total Live Invoices: <strong className="text-slate-800">{invoices.length}</strong></span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-soft overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                <th className="text-left font-semibold px-5 py-3">Vendor</th>
                <th className="text-left font-semibold px-5 py-3">Invoice ID</th>
                <th className="text-left font-semibold px-5 py-3">Date</th>
                <th className="text-right font-semibold px-5 py-3">Amount</th>
                <th className="text-center font-semibold px-5 py-3">Status</th>
                <th className="text-right font-semibold px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pageData.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 text-sm">
                    {invoices.length === 0
                      ? 'No invoices found in database. Upload a PDF in the Upload Center to get started!'
                      : 'No invoices match your filters.'}
                  </td>
                </tr>
              ) : (
                pageData.map((inv) => {
                  const isDeleting = deletingId === inv.id;
                  return (
                    <tr
                      key={inv.id}
                      className="border-t border-slate-100 hover:bg-slate-50/60 transition-colors"
                    >
                      <td className="px-5 py-3.5">
                        <div className="font-medium text-slate-800">{inv.vendor}</div>
                        <div className="text-[11px] text-slate-400">{inv.category}</div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600 font-mono text-xs">{inv.invoiceId}</td>
                      <td className="px-5 py-3.5 text-slate-600">{formatDate(inv.date)}</td>
                      <td className="px-5 py-3.5 text-right font-semibold text-slate-900">
                        {formatINR(inv.amount)}
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium ${statusStyles[inv.status]}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${statusDot[inv.status]}`} />
                          {inv.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setSelected(inv)}
                            className="p-1.5 rounded-md text-slate-400 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                            aria-label="View invoice"
                            title="View details"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            onClick={() => handleDelete(inv.id)}
                            disabled={isDeleting}
                            className="p-1.5 rounded-md text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors disabled:opacity-50"
                            aria-label="Delete invoice"
                            title="Delete invoice permanently"
                          >
                            {isDeleting ? (
                              <Loader2 size={16} className="animate-spin text-red-500" />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-5 py-3 border-t border-slate-100">
          <p className="text-xs text-slate-400">
            Showing {pageData.length} of {filtered.length} invoices
          </p>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-md text-slate-500 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="text-xs font-medium text-slate-600 px-2">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-md text-slate-500 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-100 transition-colors"
              aria-label="Next page"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>

      {selected && (
        <InvoiceModal
          invoice={selected}
          isDeleting={deletingId === selected.id}
          onClose={() => setSelected(null)}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}

function InvoiceModal({
  invoice,
  isDeleting,
  onClose,
  onDelete,
}: {
  invoice: Invoice;
  isDeleting?: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-xl shadow-card max-w-lg w-full max-h-[90vh] overflow-y-auto animate-scale-in">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div>
            <h3 className="text-base font-bold text-slate-900">Invoice Details</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{invoice.invoiceId}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <DetailField label="Vendor" value={invoice.vendor} />
            <DetailField label="Category" value={invoice.category} />
            <DetailField label="Date" value={formatDate(invoice.date)} />
            <DetailField label="Currency" value={invoice.currency} />
            <DetailField label="GST / Tax" value={formatINR(invoice.gst)} />
            <DetailField label="Status" value={invoice.status} />
          </div>

          <div className="flex items-center justify-between rounded-lg bg-brand-50 px-4 py-3">
            <span className="text-sm font-medium text-brand-700">Total Amount</span>
            <span className="text-xl font-bold text-brand-700">{formatINR(invoice.amount)}</span>
          </div>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Line Items
            </p>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-500">
                    <th className="text-left font-medium px-3 py-2">Description</th>
                    <th className="text-right font-medium px-3 py-2">Qty</th>
                    <th className="text-right font-medium px-3 py-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.lineItems.map((item, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">{item.description}</td>
                      <td className="px-3 py-2 text-right text-slate-600">{item.quantity}</td>
                      <td className="px-3 py-2 text-right font-medium text-slate-800">
                        {formatINR(item.total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => onDelete(invoice.id)}
              disabled={isDeleting}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
            >
              {isDeleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
              Delete
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-slate-800 mt-0.5">{value}</p>
    </div>
  );
}
