import { useCallback, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  UploadCloud,
  X,
} from 'lucide-react';
import { uploadInvoice } from '@/services/api';
import { formatINR } from '@/utils/format';
import type { ExtractedInvoice, Invoice } from '@/types';

type Stage = 'idle' | 'uploading' | 'extracting' | 'complete' | 'error';

interface FileEntry {
  file: File;
  stage: Stage;
  progress: number;
  extracted?: ExtractedInvoice;
  errorMessage?: string;
}

const stageLabel: Record<Stage, string> = {
  idle: 'Waiting',
  uploading: 'Uploading...',
  extracting: 'Extracting Data...',
  complete: 'Complete',
  error: 'Failed',
};

interface UploadCenterProps {
  onInvoiceUploaded?: (invoice: Invoice) => void;
}

export default function UploadCenter({ onInvoiceUploaded }: UploadCenterProps = {}) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(async (file: File) => {
    const entry: FileEntry = { file, stage: 'uploading', progress: 0 };
    setFiles((prev) => [entry, ...prev]);

    setFiles((prev) =>
      prev.map((f) => (f.file === file ? { ...f, progress: 45, stage: 'uploading' } : f))
    );

    await new Promise((r) => setTimeout(r, 600));

    setFiles((prev) =>
      prev.map((f) => (f.file === file ? { ...f, progress: 75, stage: 'extracting' } : f))
    );

    try {
      const { extracted, invoice } = await uploadInvoice(file);
      setFiles((prev) =>
        prev.map((f) =>
          f.file === file
            ? { ...f, progress: 100, stage: 'complete', extracted: extracted }
            : f
        )
      );
      if (invoice && onInvoiceUploaded) {
        onInvoiceUploaded(invoice);
      }
    } catch (err: any) {
      const backendError =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Failed to upload invoice.';

      const errorMessage =
        typeof backendError === 'string'
          ? backendError
          : Array.isArray(backendError)
          ? backendError.map((b: any) => b.msg || b.message || JSON.stringify(b)).join(', ')
          : 'Failed to process file';

      setFiles((prev) =>
        prev.map((f) =>
          f.file === file
            ? { ...f, stage: 'error', progress: 100, errorMessage }
            : f
        )
      );
    }
  }, [onInvoiceUploaded]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = Array.from(e.dataTransfer.files);
      dropped.forEach(processFile);
    },
    [processFile]
  );

  const handleSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(e.target.files || []);
      selected.forEach(processFile);
      e.target.value = '';
    },
    [processFile]
  );

  const removeFile = (file: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== file));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="space-y-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`relative cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-all ${
            isDragging
              ? 'border-brand-500 bg-brand-50 scale-[1.01]'
              : 'border-slate-300 bg-white hover:border-brand-400 hover:bg-slate-50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            onChange={handleSelect}
            className="hidden"
          />
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
            <p className="text-xs text-slate-400 mt-1">
              or click to browse — only .pdf files accepted
            </p>
          </div>
        </div>

        <div className="space-y-2.5">
          {files.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">
              No uploads yet. Drop a file to see extraction in action.
            </div>
          )}
          {files.map((entry, i) => (
            <FileRow key={i} entry={entry} onRemove={() => removeFile(entry.file)} />
          ))}
        </div>
      </div>

      <div className="lg:sticky lg:top-20 self-start">
        <ExtractedPreview entry={files.find((f) => f.stage === 'complete' && f.extracted)} />
      </div>
    </div>
  );
}

function FileRow({ entry, onRemove }: { entry: FileEntry; onRemove: () => void }) {
  const { file, stage, progress, errorMessage } = entry;
  return (
    <div
      className={`rounded-lg border p-3.5 shadow-soft animate-scale-in transition-colors ${
        stage === 'error'
          ? 'bg-red-50/40 border-red-200'
          : 'bg-white border-slate-200'
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
                  : stage === 'complete'
                  ? 'text-emerald-600 font-medium'
                  : ''
              }
            >
              {stageLabel[stage]}
            </span>
          </p>
        </div>
        <StageIcon stage={stage} />
        <button
          onClick={onRemove}
          className="text-slate-300 hover:text-slate-500 transition-colors"
          aria-label="Remove file"
        >
          <X size={16} />
        </button>
      </div>

      {(stage === 'uploading' || stage === 'extracting') && (
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

function StageIcon({ stage }: { stage: Stage }) {
  if (stage === 'complete')
    return <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />;
  if (stage === 'error')
    return <AlertCircle size={18} className="text-red-500 shrink-0" />;
  return <Loader2 size={16} className="text-brand-500 animate-spin shrink-0" />;
}

function ExtractedPreview({ entry }: { entry?: FileEntry }) {
  if (!entry?.extracted) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-soft h-full flex flex-col items-center justify-center min-h-[300px]">
        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 mb-3">
          <FileText size={26} />
        </div>
        <p className="text-sm font-medium text-slate-600">Extracted Data Preview</p>
        <p className="text-xs text-slate-400 mt-1 max-w-[220px]">
          Upload a PDF and extracted invoice fields will appear here automatically.
        </p>
      </div>
    );
  }

  const data = entry.extracted;
  const formattedDate = (() => {
    try {
      const d = new Date(data.date);
      return !isNaN(d.getTime()) ? d.toLocaleDateString('en-IN') : data.date || 'N/A';
    } catch {
      return data.date || 'N/A';
    }
  })();

  const lineItems = data.lineItems || [];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-card animate-scale-in overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-200 bg-slate-50">
        <CheckCircle2 size={17} className="text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-900">Extracted Data Preview</h3>
        <span className="ml-auto text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
          Auto-verified
        </span>
      </div>

      <div className="p-5 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Vendor Name" value={data.vendorName || 'Unknown Vendor'} />
          <Field label="Invoice #" value={data.invoiceNumber || 'N/A'} />
          <Field label="Date" value={formattedDate} />
          <Field label="Currency" value={data.currency || 'INR'} />
          <Field label="GST / Tax" value={formatINR(data.gst || 0)} />
          <Field label="Total Amount" value={formatINR(data.totalAmount || 0)} highlight />
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
                {lineItems.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-3 py-2 text-slate-400 text-center">
                      No line items extracted
                    </td>
                  </tr>
                ) : (
                  lineItems.map((item, i) => (
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

function Field({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? 'bg-brand-50' : 'bg-slate-50'}`}>
      <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">{label}</p>
      <p
        className={`text-sm font-semibold mt-0.5 ${
          highlight ? 'text-brand-700' : 'text-slate-800'
        }`}
      >
        {value}
      </p>
    </div>
  );
}
