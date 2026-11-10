import type { Analytics, Invoice, ExtractedInvoice } from '@/types';

const vendors = [
  'Reliance Jio',
  'AWS India',
  'Swiggy IT',
  'Zoho',
  'Tata Croma',
  'Flipkart B2B',
  'Infosys BPM',
  'TCS iON',
];

const categories = [
  'Telecom',
  'Cloud Services',
  'Food & Beverage',
  'Software',
  'Electronics',
  'Logistics',
  'Consulting',
  'IT Infrastructure',
];

const statuses: Invoice['status'][] = ['Processed', 'Pending', 'Failed'];

function seedRandom(seed: number): () => number {
  let value = seed;
  return () => {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

export const invoices: Invoice[] = (() => {
  const rand = seedRandom(42);
  const list: Invoice[] = [];
  for (let i = 0; i < 72; i++) {
    const vendor = vendors[Math.floor(rand() * vendors.length)];
    const category = categories[Math.floor(rand() * categories.length)];
    const status = statuses[Math.floor(rand() * 3)];
    const amount = Math.floor(rand() * 480000) + 5000;
    const gst = Math.round(amount * 0.18);
    const day = Math.floor(rand() * 27) + 1;
    const month = Math.floor(rand() * 12);
    const year = 2025;

    list.push({
      id: `INV-${String(i + 1).padStart(4, '0')}`,
      vendor,
      invoiceId: `INV-${String(1000 + i)}`,
      date: new Date(year, month, day).toISOString(),
      amount,
      status,
      category,
      currency: 'INR',
      gst,
      lineItems: [
        { description: `${category} Service Charge`, quantity: 1, unitPrice: Math.round(amount * 0.7), total: Math.round(amount * 0.7) },
        { description: 'GST 18%', quantity: 1, unitPrice: gst, total: gst },
        { description: 'Processing Fee', quantity: 1, unitPrice: Math.round(amount * 0.12), total: Math.round(amount * 0.12) },
      ],
    });
  }
  return list;
})();

export const analytics: Analytics = (() => {
  const processed = invoices.filter((i) => i.status === 'Processed');
  const totalSpent = processed.reduce((sum, i) => sum + i.amount, 0);
  const activeVendors = new Set(processed.map((i) => i.vendor)).size;

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const rand = seedRandom(7);
  const monthlySpend = monthNames.map((month) => ({
    month,
    spend: Math.floor(rand() * 600000) + 120000,
  }));

  const vendorSpend = vendors.map((vendor) => ({
    vendor,
    spend: processed
      .filter((i) => i.vendor === vendor)
      .reduce((sum, i) => sum + i.amount, 0),
  }))
    .filter((v) => v.spend > 0)
    .sort((a, b) => b.spend - a.spend)
    .slice(0, 5);

  return {
    metrics: {
      totalSpent,
      invoicesProcessed: invoices.length,
      activeVendors,
      averageInvoiceValue: Math.round(totalSpent / (processed.length || 1)),
    },
    monthlySpend,
    vendorSpend,
  };
})();

export const mockExtractedInvoice: ExtractedInvoice = {
  vendorName: 'Tata Croma Enterprise',
  invoiceNumber: 'CROMA-2025-0891',
  date: '2025-10-15',
  totalAmount: 125000,
  currency: 'INR',
  gst: 22500,
  lineItems: [
    { description: 'Dell XPS 13 Laptop (Qty: 5)', quantity: 5, unitPrice: 95000, total: 475000 },
    { description: 'Logitech MX Master 3S', quantity: 5, unitPrice: 8500, total: 42500 },
    { description: 'USB-C Docking Station', quantity: 10, unitPrice: 12000, total: 120000 },
  ],
};
