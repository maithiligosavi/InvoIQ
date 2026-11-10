import axios from 'axios';
import type { Analytics, ExtractedInvoice, Invoice } from '@/types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach Authorization: Bearer <token> to every axios request
api.interceptors.request.use(
  (config) => {
    const token = getStoredToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercept 401 Unauthorized responses to clear token and trigger auth modal
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthSession();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('invoiq:unauthorized'));
      }
    }
    return Promise.reject(error);
  }
);

// Seamlessly attach Authorization: Bearer <token> to native window.fetch requests as well
if (typeof window !== 'undefined' && window.fetch) {
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const token = getStoredToken();
    if (token) {
      init = init ? { ...init } : {};
      const headers = new Headers(init.headers || {});
      if (!headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      init.headers = headers;
    }
    return originalFetch(input, init);
  };
}

// -------------------------------------------------------------
// Auth Helpers & Storage
// -------------------------------------------------------------

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token') || localStorage.getItem('access_token');
}

export function getStoredUsername(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('username');
}

export function saveAuthSession(token: string, username?: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('token', token);
  localStorage.setItem('access_token', token);
  if (username) {
    localStorage.setItem('username', username);
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('invoiq:auth_changed', { detail: { token, username } }));
  }
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('invoiq:auth_changed', { detail: { token: null, username: null } }));
  }
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
  message?: string;
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/token', {
    username: username.trim(),
    password,
  });
  saveAuthSession(data.access_token, data.username);
  return data;
}

export async function registerUser(username: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/register', {
    username: username.trim(),
    password,
  });
  saveAuthSession(data.access_token, data.username);
  return data;
}

export async function fetchCurrentUser(): Promise<{ id: number; username: string }> {
  const { data } = await api.get<{ id: number; username: string }>('/me');
  return data;
}

// -------------------------------------------------------------
// Existing Protected Invoice APIs
// -------------------------------------------------------------

export async function fetchInvoices(): Promise<Invoice[]> {
  const { data } = await api.get<Invoice[]>('/invoices');
  return (data || []).map((inv: any) => ({
    ...inv,
    amount: Number(inv.amount ?? inv.totalAmount ?? 0),
    status: inv.status || 'Verified',
  }));
}

export async function fetchAnalytics(): Promise<Analytics> {
  const { data } = await api.get<Analytics>('/analytics');
  return data;
}

export async function deleteInvoice(invoiceId: string): Promise<{ message: string; id: string }> {
  const { data } = await api.delete<{ message: string; id: string }>(`/invoices/${encodeURIComponent(invoiceId)}`);
  return data;
}

/** Parse a PDF invoice and return extracted fields — does NOT save to DB. */
export async function parseInvoice(file: File): Promise<ExtractedInvoice> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<ExtractedInvoice>('/parse', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (event.total) {
        const progress = Math.round((event.loaded / event.total) * 100);
        apiProgressTracker.setProgress(progress);
      }
    },
  });

  const vendor = data.vendorName || 'Unknown Vendor';
  const invoiceNumber = data.invoiceNumber || '';
  const invoiceDate = data.date || new Date().toISOString().split('T')[0];
  const totalAmount = Number(data.totalAmount ?? 0);
  // Preserve decimal precision — do NOT round GST or line-item amounts to integers.
  // Math.round() was the original source of decimal-blocking: a totalAmount like
  // 499.50 would produce a rounded GST of 90 (instead of 89.91), causing a
  // balance mismatch in the backend validator and preventing the invoice from saving.
  const gst = data.gst != null
    ? parseFloat(Number(data.gst).toFixed(2))
    : parseFloat((totalAmount * 0.18).toFixed(2));
  const currency = data.currency || 'INR';
  const baseAmount = parseFloat((totalAmount - gst).toFixed(2));
  const lineItems = (data.lineItems && data.lineItems.length > 0)
    ? data.lineItems
    : [
        { description: `${vendor} Service`, quantity: 1, unitPrice: baseAmount, total: baseAmount },
        { description: 'GST 18%', quantity: 1, unitPrice: gst, total: gst },
      ];

  return { vendorName: vendor, invoiceNumber, date: invoiceDate, totalAmount, currency, gst, lineItems };
}

/** Persist a (possibly user-edited) ExtractedInvoice to the database and return the saved Invoice. */
export async function saveInvoice(extracted: ExtractedInvoice): Promise<Invoice> {
  const { data } = await api.post<Invoice & { id: string; vendor: string; invoiceId: string; amount: number; status: string; category: string }>('/invoices', {
    vendorName: extracted.vendorName,
    invoiceNumber: extracted.invoiceNumber,
    date: extracted.date,
    totalAmount: extracted.totalAmount,
    gst: extracted.gst,
    taxAmount: extracted.gst,
    currency: extracted.currency,
    lineItems: extracted.lineItems,
  });

  const id = (data as any).id ? String((data as any).id) : `INV-${Date.now()}`;
  const vendor = (data as any).vendor || extracted.vendorName;
  const invoiceId = (data as any).invoiceId || extracted.invoiceNumber;
  const amount = Number((data as any).amount ?? extracted.totalAmount);
  const status = (data as any).status || 'Verified';

  return {
    id,
    vendor,
    invoiceId,
    date: extracted.date,
    amount,
    status,
    category: (data as any).category || 'General',
    currency: extracted.currency,
    gst: extracted.gst,
    lineItems: extracted.lineItems,
  };
}

/** @deprecated Use parseInvoice + saveInvoice instead. Kept for compatibility. */
export async function uploadInvoice(file: File): Promise<{
  progress: number;
  extracted: ExtractedInvoice;
  invoice: Invoice;
}> {
  const extracted = await parseInvoice(file);
  const invoice = await saveInvoice(extracted);
  return { progress: 100, extracted, invoice };
}

export const apiProgressTracker = {
  current: 0,
  setProgress(value: number) {
    this.current = value;
  },
};

export default api;
