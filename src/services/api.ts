import axios from 'axios';
import type { Analytics, ExtractedInvoice, Invoice } from '@/types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export async function fetchInvoices(): Promise<Invoice[]> {
  const { data } = await api.get<Invoice[]>('/invoices');
  return data;
}

export async function fetchAnalytics(): Promise<Analytics> {
  const { data } = await api.get<Analytics>('/analytics');
  return data;
}

export async function deleteInvoice(invoiceId: string): Promise<{ message: string; id: string }> {
  const { data } = await api.delete<{ message: string; id: string }>(`/invoices/${encodeURIComponent(invoiceId)}`);
  return data;
}

export async function uploadInvoice(file: File): Promise<{
  progress: number;
  extracted: ExtractedInvoice;
  invoice: Invoice;
}> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (event.total) {
        const progress = Math.round((event.loaded / event.total) * 100);
        apiProgressTracker.setProgress(progress);
      }
    },
  });

  // Unpack data from response (handles { data: {...} } or root fields)
  const raw = (data && data.data) ? data.data : data;

  const vendor = raw.vendor || raw.vendorName || raw.vendor_name || 'Unknown Vendor';
  const invoiceNumber = raw.invoiceId || raw.invoiceNumber || raw.invoice_number || 'INV-001';
  const invoiceDate = raw.date || raw.invoice_date || new Date().toISOString().split('T')[0];
  const totalAmount = Number(raw.amount ?? raw.totalAmount ?? raw.total_amount ?? 0);
  const gst = Number(raw.gst ?? Math.round(totalAmount * 0.18));
  const currency = raw.currency || 'INR';
  const status = (raw.status === 'Pending' || raw.status === 'Failed') ? raw.status : 'Processed';
  const id = raw.id ? String(raw.id) : `INV-${Date.now()}`;

  const lineItems = (raw.lineItems && raw.lineItems.length > 0)
    ? raw.lineItems
    : [
        {
          description: `${vendor} Service`,
          quantity: 1,
          unitPrice: Math.round(totalAmount * 0.82),
          total: Math.round(totalAmount * 0.82),
        },
        {
          description: 'GST 18%',
          quantity: 1,
          unitPrice: gst,
          total: gst,
        },
      ];

  const extracted: ExtractedInvoice = {
    vendorName: vendor,
    invoiceNumber,
    date: invoiceDate,
    totalAmount,
    currency,
    gst,
    lineItems,
  };

  const invoice: Invoice = {
    id,
    vendor,
    invoiceId: invoiceNumber,
    date: invoiceDate,
    amount: totalAmount,
    status,
    category: raw.category || 'General',
    currency,
    gst,
    lineItems,
  };

  return { progress: 100, extracted, invoice };
}

export const apiProgressTracker = {
  current: 0,
  setProgress(value: number) {
    this.current = value;
  },
};

export default api;
