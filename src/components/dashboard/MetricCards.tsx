import {
  Building2,
  Receipt,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import { formatINR } from '@/utils/format';
import type { Metrics } from '@/types';

interface MetricCardsProps {
  metrics: Metrics;
}

const cards: { key: keyof Metrics; label: string; icon: LucideIcon; color: string; bg: string }[] = [
  { key: 'totalSpent', label: 'Total Spent', icon: Wallet, color: 'text-brand-600', bg: 'bg-brand-50' },
  { key: 'invoicesProcessed', label: 'Invoices Processed', icon: Receipt, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  { key: 'activeVendors', label: 'Active Vendors', icon: Building2, color: 'text-amber-600', bg: 'bg-amber-50' },
  { key: 'averageInvoiceValue', label: 'Avg Invoice Value', icon: TrendingUp, color: 'text-violet-600', bg: 'bg-violet-50' },
];

export default function MetricCards({ metrics }: MetricCardsProps) {
  const safeMetrics = metrics || {
    totalSpent: 0,
    invoicesProcessed: 0,
    activeVendors: 0,
    averageInvoiceValue: 0,
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        const value = safeMetrics[card.key] ?? 0;
        const display = typeof value === 'number' && value > 999
          ? formatINR(value)
          : formatINR(value as number);
        const isCount = card.key === 'invoicesProcessed' || card.key === 'activeVendors';
        return (
          <div
            key={card.key}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft hover:shadow-card transition-shadow animate-fade-in"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">{card.label}</p>
                <p className="text-2xl font-bold text-slate-900 mt-1.5">
                  {isCount ? value.toLocaleString('en-IN') : display}
                </p>
              </div>
              <div className={`flex items-center justify-center w-11 h-11 rounded-lg ${card.bg}`}>
                <Icon size={20} className={card.color} />
              </div>
            </div>
            <div className="flex items-center gap-1 mt-3">


            </div>
          </div>
        );
      })}
    </div>
  );
}
