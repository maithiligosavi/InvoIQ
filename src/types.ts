export type InvoiceStatus = 'Processed' | 'Pending' | 'Failed';

export interface LineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
}

export interface Invoice {
  id: string;
  vendor: string;
  invoiceId: string;
  date: string;
  amount: number;
  status: InvoiceStatus;
  category: string;
  currency: string;
  gst: number;
  lineItems: LineItem[];
}

export interface Metrics {
  totalSpent: number;
  invoicesProcessed: number;
  activeVendors: number;
  averageInvoiceValue: number;
}

export interface MonthlySpend {
  month: string;
  spend: number;
}

export interface VendorSpend {
  vendor: string;
  spend: number;
}

export interface Analytics {
  metrics: Metrics;
  monthlySpend: MonthlySpend[];
  vendorSpend: VendorSpend[];
}

export interface ExtractedInvoice {
  vendorName: string;
  invoiceNumber: string;
  date: string;
  totalAmount: number;
  currency: string;
  gst: number;
  lineItems: LineItem[];
}
