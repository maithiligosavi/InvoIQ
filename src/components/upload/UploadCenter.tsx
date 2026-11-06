import { useCallback, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  Save,
  UploadCloud,
  X,
} from 'lucide-react';
import { parseInvoice, saveInvoice } from '@/services/api';
import { formatINR } from '@/utils/format';
import type { ExtractedInvoice, Invoice } from '@/types';

// ─── Types ───────────────────────────────────────────────────────────────────

type UploadStage = 'idle' | 'uploading' | 'extracting' | 'review' | 'saving' | 'saved' | 'error';

interface FileEntry {
  file: File;
  stage: UploadStage;
  progress: number;
  extracted?: ExtractedInvoice;
  errorMessage?: string;
}

const stageLabel: Record<UploadStage, string> = {
  idle: 'Waiting',
  uploading: 'Uploading…',
  extracting: 'Extracting Data…',
  review: 'Awaiting Review',
  saving: 'Saving…',
  saved: 'Saved',
  error: 'Failed',
};

interface UploadCenterProps {
  onInvoiceUploaded?: (invoice: Invoice) => void;
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function UploadCenter({ onInvoiceUploaded }: UploadCenterProps = {}) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const updateEntry = useCallback((file: File, patch: Partial<FileEntry>) => {
    setFiles((prev) => prev.map((f) => (f.file === file ? { ...f, ...patch } : f)));
  }, []);

  const processFile = useCallback(
    async (file: File) => {
      const entry: FileEntry = { file, stage: 'uploading', progress: 0 };
      setFiles((prev) => [entry, ...prev]);
      setActiveFile(file);

      // Fake progress ticks
      updateEntry(file, { progress: 40, stage: 'uploading' });
      await new Promise((r) => setTimeout(r, 500));
      updateEntry(file, { progress: 75, stage: 'extracting' });

      try {
        const extracted = await parseInvoice(file);
        updateEntry(file, { progress: 100, stage: 'review', extracted });
      } catch (err: any) {
        const raw =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          'Failed to upload invoice.';
        const errorMessage =
          typeof raw === 'string'
            ? raw
            : Array.isArray(raw)
            ? raw.map((b: any) => b.msg || b.message || JSON.stringify(b)).join(', ')
            : 'Failed to process file';
        updateEntry(file, { stage: 'error', progress: 100, errorMessage });
      }
    },
    [updateEntry]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      Array.from(e.dataTransfer.files).forEach(processFile);
    },
    [processFile]
  );

  const handleSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      Array.from(e.target.files || []).forEach(processFile);
      e.target.value = '';
    },
    [processFile]
  );

  const removeFile = (file: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== file));
    if (activeFile === file) {
      setActiveFile(null);
    }
  };

  /** Called by the review panel when the user clicks "Save Invoice" */
  const handleSave = useCallback(
    async (file: File, edited: ExtractedInvoice) => {
      updateEntry(file, { stage: 'saving', extracted: edited });
      try {
        const invoice = await saveInvoice(edited);
        updateEntry(file, { stage: 'saved' });
        if (onInvoiceUploaded) onInvoiceUploaded(invoice);
      } catch (err: any) {
        const raw =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          'Failed to save invoice.';
        const errorMessage =
          typeof raw === 'string'
            ? raw
            : Array.isArray(raw)
            ? raw.map((b: any) => b.msg || b.message || JSON.stringify(b)).join(', ')
            : 'Failed to save invoice';
        updateEntry(file, { stage: 'error', errorMessage });
      }
    },
    [updateEntry, onInvoiceUploaded]
  );

  // Which entry to show in the right panel
  const previewEntry =
    // prefer the actively selected file
    files.find((f) => f.file === activeFile) ??
    // fallback: first file in review/saving/saved state
    files.find((f) => ['review', 'saving', 'saved'].includes(f.stage));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ── Left column: drop zone + file list ── */}
      <div className="space-y-4">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`relative cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-all ${
            isDragging
              ? 'border-brand-500 bg-brand-50 scale-[1.01]'
              : 'border-slate-300 bg-white hover:border-brand-400 hover:bg-slate-50'
          }`}
        >
          <input ref={inputRef} type="file" multiple accept=".pdf" onChange={handleSelect} className="hidden" />
          <div className="flex flex-col items-center">
            <div
              className={`flex items-center justify-center w-16 h-16 rounded-2xl mb-4 transition-colors ${
                isDragging ? 'bg-brand-600 text-white' : 'bg-brand-50 text-brand-600'
              }`}
            >
              <UploadCloud size={30} />
            </div>
            <p className="text-sm font-semibold text-slate-900">
              {isDragging ? 'Drop your PDFs here' : 'Drag & drop invoice PDFs'}
            </p>
            <p className="text-xs text-slate-400 mt-1">or click to browse — only .pdf files accepted</p>
          </div>
        </div>

        {/* File list */}
        <div className="space-y-2.5">
          {files.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">
              No uploads yet. Drop a file to see extraction in action.
            </div>
          )}
          {files.map((entry, i) => (
            <FileRow
              key={i}
              entry={entry}
              isActive={entry.file === activeFile}
              onClick={() => setActiveFile(entry.file)}
              onRemove={() => removeFile(entry.file)}
            />
          ))}
        </div>
      </div>

      {/* ── Right column: review / preview panel ── */}
      <div className="lg:sticky lg:top-20 self-start">
        {previewEntry &&
        (previewEntry.stage === 'review' || previewEntry.stage === 'saving') ? (
          <ReviewPanel
            entry={previewEntry}
            onSave={(edited) => handleSave(previewEntry.file, edited)}
          />
        ) : (
          <StaticPreview entry={previewEntry} />
        )}
      </div>
    </div>
  );
}

// ─── File Row ─────────────────────────────────────────────────────────────────

function FileRow({
  entry,
  isActive,
  onClick,
  onRemove,
}: {
  entry: FileEntry;
  isActive: boolean;
  onClick: () => void;
  onRemove: () => void;
}) {
  const { file, stage, progress, errorMessage } = entry;
  const isInProgress = stage === 'uploading' || stage === 'extracting' || stage === 'saving';

  return (
    <div
      onClick={onClick}
      className={`rounded-lg border p-3.5 shadow-soft animate-scale-in transition-colors cursor-pointer ${
        stage === 'error'
          ? 'bg-red-50/40 border-red-200'
          : isActive
          ? 'bg-brand-50/40 border-brand-300'
          : 'bg-white border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`flex items-center justify-center w-9 h-9 rounded-lg shrink-0 ${
            stage === 'error' ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500'
          }`}
        >
          {stage === 'error' ? <AlertCircle size={18} /> : <FileText size={18} />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
          <p className="text-[11px] text-slate-400">
            {(file.size / 1024).toFixed(0)} KB ·{' '}
            <span
              className={
                stage === 'error'
                  ? 'text-red-600 font-semibold'
                  : stage === 'saved'
                  ? 'text-emerald-600 font-medium'
                  : stage === 'review'
                  ? 'text-amber-600 font-medium'
                  : ''
              }
            >
              {stageLabel[stage]}
            </span>
          </p>
        </div>
        <StageIcon stage={stage} />
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="text-slate-300 hover:text-slate-500 transition-colors"
          aria-label="Remove file"
        >
          <X size={16} />
        </button>
      </div>

      {isInProgress && (
        <div className="mt-2.5">
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {stage === 'error' && errorMessage && (
        <div className="mt-2.5 flex items-start gap-2 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
          <span className="font-semibold break-words leading-relaxed">{errorMessage}</span>
        </div>
      )}
    </div>
  );
}

function StageIcon({ stage }: { stage: UploadStage }) {
  if (stage === 'saved') return <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />;
  if (stage === 'error') return <AlertCircle size={18} className="text-red-500 shrink-0" />;
  if (stage === 'review') return <FileText size={18} className="text-amber-500 shrink-0" />;
  return <Loader2 size={16} className="text-brand-500 animate-spin shrink-0" />;
}

// ─── Editable Review Panel ────────────────────────────────────────────────────

function ReviewPanel({
  entry,
  onSave,
}: {
  entry: FileEntry;
  onSave: (edited: ExtractedInvoice) => void;
}) {
  const data = entry.extracted!;
  const isSaving = entry.stage === 'saving';

  // Local form state — initialised from extracted data
  const [form, setForm] = useState<ExtractedInvoice>(() => ({ ...data }));

  const set = <K extends keyof ExtractedInvoice>(key: K, value: ExtractedInvoice[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-xl border border-slate-200 shadow-card animate-scale-in overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-200 bg-slate-50">
        <FileText size={17} className="text-amber-500" />
        <h3 className="text-sm font-bold text-slate-900">Review Extracted Data</h3>
        <span className="ml-auto text-[10px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
          Needs Confirmation
        </span>
      </div>

      <div className="p-5 space-y-5">
        {/* Core fields grid */}
        <div className="grid grid-cols-2 gap-3">
          <EditableField
            label="Vendor Name"
            value={form.vendorName}
            onChange={(v) => set('vendorName', v)}
            required
            colSpan
          />
          <EditableField
            label="Invoice Number"
            value={form.invoiceNumber}
            onChange={(v) => set('invoiceNumber', v)}
            required
          />
          <EditableField
            label="Invoice Date"
            value={form.date}
            onChange={(v) => set('date', v)}
            type="date"
          />
          <EditableField
            label="Currency"
            value={form.currency}
            onChange={(v) => set('currency', v)}
            maxLength={3}
          />
          <EditableField
            label="GST / Tax"
            value={String(form.gst ?? 0)}
            onChange={(v) => set('gst', Number(v) || 0)}
            type="number"
            min="0"
          />
          <EditableField
            label="Total Amount"
            value={String(form.totalAmount ?? 0)}
            onChange={(v) => set('totalAmount', Number(v) || 0)}
            type="number"
            min="0"
            highlight
            required
          />
        </div>

        {/* Line items */}
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Line Items
          </p>
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500">
                  <th className="text-left font-medium px-3 py-2">Description</th>
                  <th className="text-right font-medium px-3 py-2 w-28">Total</th>
                </tr>
              </thead>
              <tbody>
                {form.lineItems.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-3 py-2 text-slate-400 text-center">
                      No line items extracted
                    </td>
                  </tr>
                ) : (
                  form.lineItems.map((item, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-3 py-1.5">
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => {
                            const updated = form.lineItems.map((li, idx) =>
                              idx === i ? { ...li, description: e.target.value } : li
                            );
                            set('lineItems', updated);
                          }}
                          className="w-full text-slate-700 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-brand-400 focus:outline-none py-0.5 transition-colors"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-right">
                        <input
                          type="number"
                          min="0"
                          value={item.total}
                          onChange={(e) => {
                            const updated = form.lineItems.map((li, idx) =>
                              idx === i ? { ...li, total: Number(e.target.value) || 0 } : li
                            );
                            set('lineItems', updated);
                          }}
                          className="w-24 text-right font-medium text-slate-800 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-brand-400 focus:outline-none py-0.5 transition-colors"
                        />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Save button */}
        <button
          type="submit"
          disabled={isSaving}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors shadow-sm"
        >
          {isSaving ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Saving Invoice…
            </>
          ) : (
            <>
              <Save size={15} />
              Save Invoice
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// ─── Editable Field ───────────────────────────────────────────────────────────

function EditableField({
  label,
  value,
  onChange,
  type = 'text',
  highlight,
  required,
  colSpan,
  min,
  maxLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  highlight?: boolean;
  required?: boolean;
  colSpan?: boolean;
  min?: string;
  maxLength?: number;
}) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? 'bg-brand-50' : 'bg-slate-50'} ${colSpan ? 'col-span-2' : ''}`}>
      <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        min={min}
        maxLength={maxLength}
        className={`w-full text-sm font-semibold bg-transparent border-b pb-0.5 focus:outline-none transition-colors ${
          highlight
            ? 'text-brand-700 border-brand-200 hover:border-brand-400 focus:border-brand-600'
            : 'text-slate-800 border-slate-200 hover:border-slate-400 focus:border-brand-500'
        }`}
      />
    </div>
  );
}

// ─── Static Preview (empty / saved state) ────────────────────────────────────

function StaticPreview({ entry }: { entry?: FileEntry }) {
  if (!entry?.extracted) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-soft h-full flex flex-col items-center justify-center min-h-[300px]">
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 mb-3">
          <FileText size={26} />
        </div>
        <p className="text-sm font-medium text-slate-600">Extracted Data Preview</p>
        <p className="text-xs text-slate-400 mt-1 max-w-[220px]">
          Upload a PDF and extracted invoice fields will appear here for review.
        </p>
      </div>
    );
  }

  const data = entry.extracted;
  const isSaved = entry.stage === 'saved';

  const formattedDate = (() => {
    try {
      const d = new Date(data.date);
      return !isNaN(d.getTime()) ? d.toLocaleDateString('en-IN') : data.date || 'N/A';
    } catch {
      return data.date || 'N/A';
    }
  })();

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-card animate-scale-in overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-200 bg-slate-50">
        <CheckCircle2 size={17} className="text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-900">Invoice Saved</h3>
        <span className="ml-auto text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
          {isSaved ? 'Committed to DB' : 'Preview'}
        </span>
      </div>

      <div className="p-5 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <StaticField label="Vendor Name" value={data.vendorName || 'Unknown Vendor'} colSpan />
          <StaticField label="Invoice #" value={data.invoiceNumber || 'N/A'} />
          <StaticField label="Date" value={formattedDate} />
          <StaticField label="Currency" value={data.currency || 'INR'} />
          <StaticField label="GST / Tax" value={formatINR(data.gst || 0)} />
          <StaticField label="Total Amount" value={formatINR(data.totalAmount || 0)} highlight />
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
                  <th className="text-right font-medium px-3 py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.lineItems.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-3 py-2 text-slate-400 text-center">
                      No line items extracted
                    </td>
                  </tr>
                ) : (
                  data.lineItems.map((item, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-3 py-2 text-slate-700">{item.description}</td>
                      <td className="px-3 py-2 text-right font-medium text-slate-800">
                        {formatINR(item.total)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StaticField({
  label,
  value,
  highlight,
  colSpan,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  colSpan?: boolean;
}) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? 'bg-brand-50' : 'bg-slate-50'} ${colSpan ? 'col-span-2' : ''}`}>
      <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{label}</p>
      <p className={`text-sm font-semibold mt-0.5 ${highlight ? 'text-brand-700' : 'text-slate-800'}`}>
        {value}
      </p>
    </div>
  );
}
